import os
import secrets
import threading
import time
import json
from flask import Flask, render_template, request, send_from_directory, jsonify
import yt_dlp

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def cleanup_files():
    """Periodically clean up the downloads folder."""
    while True:
        now = time.time()
        for f in os.listdir(DOWNLOAD_FOLDER):
            f_path = os.path.join(DOWNLOAD_FOLDER, f)
            if os.stat(f_path).st_mtime < now - 3600:
                try:
                    os.remove(f_path)
                except Exception as e:
                    print(f"Error deleting {f_path}: {e}")
        time.sleep(1800)

cleanup_thread = threading.Thread(target=cleanup_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_formats', methods=['POST'])
def fetch_formats():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            # Simple resolution list logic
            resolutions = {}
            for f in formats:
                height = f.get('height')
                # Filter for video-only or combined formats with resolution
                if height and f.get('vcodec') != 'none':
                    res_str = f"{height}p"
                    ext = f.get('ext', 'mp4')
                    filesize = f.get('filesize') or f.get('filesize_approx')
                    
                    if res_str not in resolutions or (filesize and (not resolutions[res_str].get('size') or filesize > resolutions[res_str]['size'])):
                        resolutions[res_str] = {
                            'resolution': res_str,
                            'ext': ext,
                            'size': filesize,
                            'height': height
                        }

            # Sort by height descending
            sorted_res = sorted(resolutions.values(), key=lambda x: x['height'], reverse=True)
            
            # Formats to return
            clean_formats = []
            for item in sorted_res:
                size_str = f"{round(item['size'] / (1024*1024), 1)} MB" if item['size'] else "N/A"
                clean_formats.append({
                    'id': item['resolution'],
                    'label': f"{item['resolution']} | {item['ext']} | {size_str}",
                    'type': 'video',
                    'height': item['height']
                })

            # Add Audio option
            clean_formats.append({
                'id': 'audio',
                'label': 'Audio Only | mp3 | Best Quality',
                'type': 'audio'
            })

            return jsonify({
                'success': True,
                'title': info.get('title', 'Media'),
                'formats': clean_formats
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_id = request.form.get('format_id')
    download_type = request.form.get('type') # 'video' or 'audio'

    if not url or not format_id or not download_type:
        return jsonify({'error': 'Missing parameters'}), 400

    random_id = secrets.token_hex(4)
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)s__{random_id}.%(ext)s')

    if download_type == 'audio':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'restrictfilenames': True,
        }
    else:
        # Resolve height from format_id (e.g., '1080p' -> 1080)
        try:
            height = int(format_id.replace('p', ''))
            fmt_str = f'bestvideo[height<={height}]+bestaudio/best'
        except:
            fmt_str = 'best'
            
        ydl_opts = {
            'format': fmt_str,
            'outtmpl': outtmpl,
            'noplaylist': True,
            'restrictfilenames': True,
            'merge_output_format': 'mp4',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # The actual final filename might be different from prepare_filename due to postprocessing
            if download_type == 'audio':
                # For audio-only conversion, yt-dlp usually replaces the extension with .mp3
                expected_filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            else:
                expected_filename = ydl.prepare_filename(info)
                # If merged, it might be .mp4 even if outtmpl was something else
                if not os.path.exists(expected_filename):
                    base = expected_filename.rsplit('.', 1)[0]
                    for ext in ['mp4', 'mkv', 'webm']:
                        if os.path.exists(f"{base}.{ext}"):
                            expected_filename = f"{base}.{ext}"
                            break

            if not os.path.exists(expected_filename):
                # Final emergency check of all files in downloads with the same random_id
                base_pattern = f"__{random_id}."
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if base_pattern in f:
                        expected_filename = os.path.join(DOWNLOAD_FOLDER, f)
                        break

            file_basename = os.path.basename(expected_filename)
            return jsonify({
                'success': True,
                'filename': file_basename,
                'download_url': f'/get-file/{file_basename}'
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-file/<filename>')
def get_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
