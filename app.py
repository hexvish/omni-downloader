import os
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

# Module imports
from config import DOWNLOAD_FOLDER
from downloader.updater import check_for_updates
from downloader.extractor import extract_media_info, download_media
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
    
    is_valid, error_msg = validate_url(url)
    if not is_valid:
        return jsonify({'status': 'error', 'message': error_msg}), 400

    print(f">>> Fetching formats for: {url}")
    try:
        raw_info = extract_media_info(url)
        formatted_data = format_extraction_results(raw_info)
        return jsonify(formatted_data)
    except Exception as e:
        print(f">>> Fetch error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    url = sanitize_input(request.form.get('url'))
    format_id = request.form.get('format_id')
    download_type = request.form.get('type')

    if not url or not format_id or not download_type:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

    try:
        filename = download_media(url, format_id, download_type)
        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': f'/get-file/{filename}'
        })
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
