"""
Omni Downloader - Production Web Server Adapter
Optimized for Linux headless hosting on Oracle Cloud behind Caddy.
Features SSRF protection, strict 1-job concurrency, safe cleanup, and session monitoring.
"""

import os
import sys
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response

# Add parent directory to path to import core downloader modules
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Core imports
from config import APP_VERSION
from downloader.engine import init_engine, get_engine_status
from downloader.extractor import (
    extract_media_info,
    start_download_task,
    get_task_status,
    cancel_task,
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
from server.cleanup_daemon import check_disk_headroom, start_safe_cleanup

# Server Configuration
SERVER_DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", os.path.join(ROOT_DIR, "downloads"))
SERVER_MAX_FILE_SIZE = int(os.environ.get("SERVER_MAX_FILE_SIZE", 500 * 1024 * 1024)) # 500 MB default
MAX_PLAYLIST_ITEMS = int(os.environ.get("SERVER_MAX_PLAYLIST_ITEMS", 15)) # 15 items max on cloud

os.makedirs(SERVER_DOWNLOAD_DIR, exist_ok=True)

# Initialize Flask with paths pointing to shared UI
app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static")
)

# Strict 1-active-download concurrency limiter
concurrency_lock = threading.Lock()
active_downloads = set()

def get_active_task_filenames():
    """Returns set of filenames actively being processed or transferred."""
    active_files = set()
    with tasks_lock:
        for t in tasks.values():
            if t.get("status") in ("pending", "downloading", "processing"):
                fname = t.get("filename")
                if fname:
                    active_files.add(fname)
    return active_files

# Start server-safe background cleanup
start_safe_cleanup(SERVER_DOWNLOAD_DIR, get_active_task_filenames)

@app.before_request
def assign_session():
    """Ensures each client has an anonymous session identifier."""
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    sid, is_new = get_or_create_session(request.cookies, client_ip)
    request.session_id = sid
    request.session_is_new = is_new

@app.after_request
def set_session_cookie(response):
    """Sets session cookie if new."""
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
    """Extracts media metadata after strict SSRF inspection."""
    url = sanitize_input(request.form.get("url"))
    mode = request.form.get("mode", "auto")

    # 1. SSRF & URL Validation
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
    """Starts download with 1-job concurrency and disk headroom enforcement."""
    url = sanitize_input(request.form.get("url"))
    download_type = request.form.get("type", "audio")
    codec = request.form.get("codec", "mp3")
    bitrate = request.form.get("bitrate", "320")
    resolution = request.form.get("resolution", "1080p")
    is_playlist = request.form.get("is_playlist", "false").lower() in ("true", "1")
    
    try:
        total_items = int(request.form.get("total_items", 1))
    except Exception:
        total_items = 1

    # 1. SSRF Validation
    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
        return jsonify({"status": "error", "message": error_msg}), 400

    # 2. Playlist Size Limit
    if is_playlist and total_items > MAX_PLAYLIST_ITEMS:
        return jsonify({
            "status": "error",
            "message": f"Playlists are limited to a maximum of {MAX_PLAYLIST_ITEMS} items on this server."
        }), 400

    # 3. Disk Space Pre-flight Check
    has_headroom, disk_err = check_disk_headroom(SERVER_DOWNLOAD_DIR)
    if not has_headroom:
        return jsonify({"status": "error", "message": disk_err}), 507

    # 4. Strict 1-Active-Download Concurrency Limit
    with concurrency_lock:
        if len(active_downloads) >= 1:
            return jsonify({
                "status": "busy",
                "message": "The server is currently processing a download for another user. Please wait a moment and try again."
            }), 429
        
        # Claim download slot
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
            total_items=total_items
        )

        with concurrency_lock:
            active_downloads.remove(placeholder_id)
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
    """Streams downloaded file to the browser client."""
    return send_from_directory(SERVER_DOWNLOAD_DIR, filename, as_attachment=True)

# ---------------------------------------------------------------------------
# Note: Desktop-only routes (/open_downloads_folder, /api/save_file, 
# /api/reveal_file, /api/apply_update) are intentionally excluded from 
# the server adapter to prevent host GUI execution on a headless server.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_engine()
    app.run(host="127.0.0.1", port=8000, debug=False)
