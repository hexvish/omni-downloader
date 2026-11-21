"""
Omni Downloader - Production Web Server Adapter
Optimized for Linux headless hosting on Oracle Cloud behind Caddy.
Features reverse-proxy awareness, SSRF protection, strict 1-job concurrency,
safe cleanup, transfer protection, rate limiting, and anonymous session monitoring.
"""

import os
import sys
import time
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

# Add parent directory to path to import core downloader modules
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Core imports
from config import APP_VERSION, DOWNLOAD_FOLDER, SERVER_MAX_FILE_SIZE, MAX_PLAYLIST_ITEMS
from downloader.engine import init_engine, get_engine_status
from downloader.extractor import (
    extract_media_info,
    start_download_task,
    get_task_status,
    cancel_task,
    get_active_task_identifiers,
    tasks,
    tasks_lock
)
from downloader.formatter import format_extraction_results
from utils.validators import sanitize_input

# Server adapter imports
from server.security import is_safe_url
from server.session_tracker import (
    get_or_create_session,
    record_session_download,
    SESSION_COOKIE_NAME
)
from server.rate_limiter import is_rate_limited
from server.cleanup_daemon import check_disk_headroom, start_safe_cleanup, TransferGuard

# Ensure download directory exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Allowed parameters whitelist
ALLOWED_TYPES = {"video", "audio"}
ALLOWED_CODECS = {"mp3", "m4a", "flac", "wav", "opus", "mp4", "mkv", "webm"}
ALLOWED_BITRATES = {"128", "192", "256", "320"}
ALLOWED_RESOLUTIONS = {"360p", "480p", "720p", "1080p", "1440p", "2160p", "best"}
JOB_TIMEOUT_SECONDS = int(os.environ.get("OMNI_JOB_TIMEOUT", 900)) # 15 minutes max per job

# Initialize Flask with paths pointing to shared UI
app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static")
)

# Reverse-proxy awareness for Caddy (X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Concurrency control: strict 1-active-download limiter
concurrency_lock = threading.Lock()
active_downloads = set()

# Initialize core engine at startup for Gunicorn
_engine_initialized = False
_engine_lock = threading.Lock()

def _ensure_engine_initialized():
    global _engine_initialized
    with _engine_lock:
        if not _engine_initialized:
            init_engine()
            _engine_initialized = True

_ensure_engine_initialized()

# Start background cleanup daemon
start_safe_cleanup(DOWNLOAD_FOLDER, get_active_task_identifiers)

def _watchdog_timeout_checker():
    """Monitors running tasks and terminates jobs exceeding maximum runtime."""
    while True:
        try:
            now = time.time()
            stale_task_ids = []
            with tasks_lock:
                for tid, tinfo in tasks.items():
                    if tinfo.get("status") in ("starting", "downloading", "processing"):
                        started = tinfo.get("created_at", now)
                        if (now - started) > JOB_TIMEOUT_SECONDS:
                            stale_task_ids.append(tid)

            for tid in stale_task_ids:
                print(f">>> [SERVER WATCHDOG] Task {tid} exceeded {JOB_TIMEOUT_SECONDS}s limit. Cancelling.")
                cancel_task(tid)
                with tasks_lock:
                    if tid in tasks:
                        tasks[tid]["status"] = "error"
                        tasks[tid]["error"] = f"Job execution exceeded time limit ({JOB_TIMEOUT_SECONDS // 60} mins)."
                with concurrency_lock:
                    active_downloads.discard(tid)

        except Exception as e:
            print(f">>> [SERVER WATCHDOG] Error in timeout loop: {e}")

        time.sleep(30)

watchdog_thread = threading.Thread(target=_watchdog_timeout_checker, daemon=True)
watchdog_thread.start()

@app.before_request
def assign_session():
    """Assigns an anonymous, opaque session cookie to every visitor."""
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    sid, is_new = get_or_create_session(request.cookies, client_ip)
    request.session_id = sid
    request.session_is_new = is_new

@app.after_request
def set_session_cookie(response):
    """Sets HTTP-only SameSite session cookie if new."""
    if getattr(request, "session_is_new", False):
        response.set_cookie(
            SESSION_COOKIE_NAME,
            request.session_id,
            max_age=30 * 86400,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure
        )
    return response

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/fetch_formats", methods=["POST"])
def fetch_formats():
    """Extracts media metadata after rate limiting and strict SSRF inspection."""
    # 1. Rate limiting (15/min)
    is_limited, retry_after = is_rate_limited(request.session_id, "fetch_formats", limit=15, window_seconds=60)
    if is_limited:
        resp = jsonify({
            "status": "error",
            "message": f"Too many format extraction requests. Please wait {retry_after} seconds before retrying."
        })
        resp.status_code = 429
        resp.headers["Retry-After"] = str(retry_after)
        return resp

    url = sanitize_input(request.form.get("url"))
    mode = request.form.get("mode", "auto")

    # 2. SSRF & URL Validation
    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
        return jsonify({"status": "error", "message": error_msg}), 400

    print(f">>> [SERVER] Fetching formats for: {url} (mode: {mode})")
    try:
        force_playlist = True if mode == "playlist" else (False if mode == "single" else None)
        raw_info = extract_media_info(url, is_playlist=force_playlist)
        formatted_data = format_extraction_results(raw_info, url=url)
        return jsonify(formatted_data)
    except Exception as e:
        print(f">>> [SERVER] Extraction error: {e}")
        return jsonify({"status": "error", "message": "Failed to extract media information from URL."}), 500

@app.route("/start_download", methods=["POST"])
def handle_start_download():
    """Starts download with rate limiting, parameter validation, and 1-job concurrency."""
    # 1. Rate limiting (5/min)
    is_limited, retry_after = is_rate_limited(request.session_id, "start_download", limit=5, window_seconds=60)
    if is_limited:
        resp = jsonify({
            "status": "error",
            "message": f"Too many download requests. Please wait {retry_after} seconds before starting another."
        })
        resp.status_code = 429
        resp.headers["Retry-After"] = str(retry_after)
        return resp

    url = sanitize_input(request.form.get("url"))
    download_type = request.form.get("type", "audio")
    if download_type not in ALLOWED_TYPES:
        download_type = "audio"

    codec = request.form.get("codec", "mp3").lower()
    if codec not in ALLOWED_CODECS:
        codec = "mp3" if download_type == "audio" else "mp4"

    bitrate = request.form.get("bitrate", "320")
    if bitrate not in ALLOWED_BITRATES:
        bitrate = "320"

    resolution = request.form.get("resolution", "1080p")
    if resolution not in ALLOWED_RESOLUTIONS:
        resolution = "1080p"

    is_playlist = request.form.get("is_playlist", "false").lower() in ("true", "1")

    try:
        total_items = int(request.form.get("total_items", 1))
    except Exception:
        total_items = 1

    # 2. SSRF Validation
    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
        return jsonify({"status": "error", "message": error_msg}), 400

    # 3. Server-side Playlist Size Enforcement
    if is_playlist and total_items > MAX_PLAYLIST_ITEMS:
        return jsonify({
            "status": "error",
            "message": f"Playlists are limited to a maximum of {MAX_PLAYLIST_ITEMS} items on this server."
        }), 400

    # 4. Storage Headroom Pre-flight Check
    has_headroom, disk_err = check_disk_headroom(DOWNLOAD_FOLDER)
    if not has_headroom:
        return jsonify({"status": "error", "message": disk_err}), 507

    # 5. Strict 1-Active-Download Concurrency Limit
    with concurrency_lock:
        # Prune finished tasks from active_downloads
        finished_ids = set()
        with tasks_lock:
            for active_id in active_downloads:
                if active_id in tasks and tasks[active_id].get("status") in ("completed", "error", "cancelled"):
                    finished_ids.add(active_id)
        active_downloads.difference_update(finished_ids)

        if len(active_downloads) >= 1:
            return jsonify({
                "status": "busy",
                "message": "The server is currently processing a download for another user. Please wait a moment and try again."
            }), 429

        placeholder_id = f"pending_{request.session_id[:8]}"
        active_downloads.add(placeholder_id)

    try:
        task_id = start_download_task(
            url=url,
            download_type=download_type,
            codec=codec,
            bitrate=bitrate,
            resolution=resolution,
            is_playlist=is_playlist,
            total_items=total_items,
            session_id=request.session_id,
            max_file_size=SERVER_MAX_FILE_SIZE,
            max_playlist_items=MAX_PLAYLIST_ITEMS
        )

        with concurrency_lock:
            active_downloads.discard(placeholder_id)
            active_downloads.add(task_id)

        record_session_download(request.session_id)
        return jsonify({"success": True, "task_id": task_id})

    except Exception as e:
        with concurrency_lock:
            active_downloads.discard(placeholder_id)
        print(f">>> [SERVER] Start download error: {e}")
        return jsonify({"status": "error", "message": "Failed to start download task."}), 500

@app.route("/task_status/<task_id>", methods=["GET"])
def handle_task_status(task_id):
    """Polls status and releases concurrency lock upon task completion/error."""
    status = get_task_status(task_id)
    if not status:
        return jsonify({"status": "error", "message": "Task not found"}), 404

    # Release concurrency slot once task is finished
    task_state = status.get("status")
    if task_state in ("completed", "error", "cancelled"):
        with concurrency_lock:
            active_downloads.discard(task_id)

    return jsonify(status)

@app.route("/cancel_download/<task_id>", methods=["POST"])
def handle_cancel_download(task_id):
    success = cancel_task(task_id)
    with concurrency_lock:
        active_downloads.discard(task_id)
    return jsonify({"success": success, "task_id": task_id})

@app.route("/api/engine/status", methods=["GET"])
def handle_engine_status():
    return jsonify(get_engine_status())

@app.route("/get-file/<path:filename>")
def get_file(filename):
    """Streams downloaded file to the browser client with transfer protection and session check."""
    # Sanitize filename against path traversal
    clean_name = os.path.basename(filename)
    task_id = request.args.get("task_id")

    # Verify task ownership if task_id provided or discoverable in active/recent tasks
    authorized = True
    with tasks_lock:
        if task_id and task_id in tasks:
            target_task = tasks[task_id]
            if target_task.get("session_id") and target_task.get("session_id") != request.session_id:
                authorized = False
        else:
            # Check if any task matches this filename
            for t in tasks.values():
                if t.get("filename") == clean_name:
                    if t.get("session_id") and t.get("session_id") != request.session_id:
                        authorized = False
                    break

    if not authorized:
        return jsonify({"status": "error", "message": "Unauthorized access to file."}), 403

    target_path = os.path.join(DOWNLOAD_FOLDER, clean_name)
    if not os.path.isfile(target_path):
        return jsonify({"status": "error", "message": "File not found or has expired."}), 404

    # Stream file protected by TransferGuard
    with TransferGuard(clean_name):
        response = send_from_directory(
            DOWNLOAD_FOLDER,
            clean_name,
            as_attachment=True,
            download_name=clean_name
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

@app.errorhandler(404)
def not_found_handler(e):
    return jsonify({"status": "error", "message": "Resource not found."}), 404

@app.errorhandler(500)
def internal_error_handler(e):
    return jsonify({"status": "error", "message": "An internal server error occurred."}), 500

# ---------------------------------------------------------------------------
# Note: Desktop-only routes (/open_downloads_folder, /api/save_file, 
# /api/reveal_file, /api/apply_update) are intentionally excluded from 
# the server adapter to prevent host GUI execution on a headless server.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
