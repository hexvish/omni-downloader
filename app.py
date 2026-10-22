import os
import sys
import shutil
import subprocess
import time
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

# Module imports
from config import DOWNLOAD_FOLDER
from downloader.updater import check_for_updates
from downloader.engine import init_engine, get_engine_status
from downloader.extractor import (
    extract_media_info, 
    download_media, 
    start_download_task, 
    get_task_status,
    cancel_task
)
from downloader.formatter import format_extraction_results
from utils.validators import validate_url, sanitize_input
from utils.cleanup import start_cleanup_worker

app = Flask(__name__)

# Ensure download directory exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_formats', methods=['POST'])
def fetch_formats():
    url = sanitize_input(request.form.get('url'))
    mode = request.form.get('mode', 'auto')
    
    is_valid, error_msg = validate_url(url)
    if not is_valid:
        return jsonify({'status': 'error', 'message': error_msg}), 400

    print(f">>> Fetching formats for: {url} (mode: {mode})")
    try:
        force_playlist = True if mode == 'playlist' else (False if mode == 'single' else None)
        raw_info = extract_media_info(url, is_playlist=force_playlist)
        formatted_data = format_extraction_results(raw_info, url=url)
        return jsonify(formatted_data)
    except Exception as e:
        print(f">>> Fetch error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/start_download', methods=['POST'])
def handle_start_download():
    url = sanitize_input(request.form.get('url'))
    download_type = request.form.get('type', 'audio')
    codec = request.form.get('codec', 'mp3')
    bitrate = request.form.get('bitrate', '320')
    resolution = request.form.get('resolution', '1080p')
    is_playlist = request.form.get('is_playlist', 'false').lower() in ('true', '1')
    try:
        total_items = int(request.form.get('total_items', 1))
    except Exception:
        total_items = 1

    if not url:
        return jsonify({'status': 'error', 'message': 'Missing URL parameter'}), 400

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
        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        print(f">>> Start download error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/task_status/<task_id>', methods=['GET'])
def handle_task_status(task_id):
    status = get_task_status(task_id)
    if not status:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    return jsonify(status)

@app.route('/cancel_download/<task_id>', methods=['POST'])
def handle_cancel_download(task_id):
    success = cancel_task(task_id)
    return jsonify({'success': success, 'task_id': task_id})

@app.route('/api/engine/status', methods=['GET'])
def handle_engine_status():
    return jsonify(get_engine_status())

@app.route('/open_downloads_folder', methods=['POST'])
def handle_open_downloads_folder():
    try:
        if os.name == 'nt':
            os.startfile(DOWNLOAD_FOLDER)
        elif sys.platform == 'darwin':
            subprocess.run(['open', DOWNLOAD_FOLDER])
        else:
            subprocess.run(['xdg-open', DOWNLOAD_FOLDER])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_file', methods=['POST'])
def handle_save_file():
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'}), 400
    src_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(src_path):
        return jsonify({'success': False, 'error': 'File not found on disk'}), 404

    user_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
    mode = request.form.get('mode', 'dialog')
    
    chosen_path = None
    if mode == 'dialog':
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            chosen_path = filedialog.asksaveasfilename(
                initialdir=user_downloads,
                initialfile=filename,
                title="Save Downloaded File"
            )
            root.destroy()
        except Exception as e:
            print(f">>> File dialog fallback: {e}")

        # If user cancelled dialog
        if chosen_path == "":
            return jsonify({'success': False, 'cancelled': True})

    # If dialog selected a path, copy to chosen_path
    if chosen_path:
        dest_path = chosen_path
    else:
        # Fallback: copy directly to user's Downloads folder
        dest_path = os.path.join(user_downloads, filename)
        base, ext = os.path.splitext(filename)
        c = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(user_downloads, f"{base} ({c}){ext}")
            c += 1

    try:
        shutil.copy2(src_path, dest_path)
        return jsonify({'success': True, 'saved_to': dest_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/open_file', methods=['POST'])
def handle_open_file():
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'}), 400
    src_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(src_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    try:
        if os.name == 'nt':
            os.startfile(src_path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', src_path])
        else:
            subprocess.run(['xdg-open', src_path])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reveal_file', methods=['POST'])
def handle_reveal_file():
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'}), 400
    src_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(src_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    try:
        if os.name == 'nt':
            norm_path = os.path.normpath(src_path)
            subprocess.Popen(f'explorer /select,"{norm_path}"', shell=True)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', src_path])
        else:
            subprocess.Popen(['xdg-open', os.path.dirname(src_path)])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    url = sanitize_input(request.form.get('url'))
    format_id = request.form.get('format_id')
    download_type = request.form.get('type', 'audio')
    codec = request.form.get('codec', 'mp3')
    bitrate = request.form.get('bitrate', '320')
    resolution = request.form.get('resolution') or format_id
    is_playlist = request.form.get('is_playlist', 'false').lower() in ('true', '1')
    try:
        total_items = int(request.form.get('total_items', 1))
    except Exception:
        total_items = 1

    if not url:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

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
        while True:
            status = get_task_status(task_id)
            if not status or status.get('status') == 'error':
                err = status.get('error', 'Download failed') if status else 'Lost task'
                return jsonify({'status': 'error', 'message': err}), 500
            if status.get('status') == 'completed':
                return jsonify({
                    'success': True,
                    'filename': status['filename'],
                    'download_url': status['download_url']
                })
            time.sleep(0.5)
    except Exception as e:
        print(f">>> Download error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get-file/<path:filename>')
def get_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    # Startup sequence
    init_engine()
    check_for_updates()
    start_cleanup_worker()
    
    # Run the server
    app.run(host='0.0.0.0', port=5000, debug=True)

