import os
import time
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

# Module imports
from config import DOWNLOAD_FOLDER
from downloader.updater import check_for_updates
from downloader.extractor import (
    extract_media_info, 
    download_media, 
    start_download_task, 
    get_task_status
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
    check_for_updates()
    start_cleanup_worker()
    
    # Run the server
    app.run(host='0.0.0.0', port=5000, debug=True)

