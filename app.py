import os
import secrets
import threading
import time
import subprocess
import sys
from flask import Flask, render_template, request, send_from_directory, jsonify
import yt_dlp
from yt_dlp.utils import ExtractorError, DownloadError

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def check_for_updates():
    """Check and update yt-dlp on startup."""
    print(">>> yt-dlp update check started...")
    try:
        # Using -U to ensure it's the latest version
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
        print(">>> yt-dlp is up to date.")
    except Exception as e:
        print(f">>> yt-dlp update failed: {e}")

def cleanup_files():
    """Periodically clean up the downloads folder."""
    while True:
        now = time.time()
        for f in os.listdir(DOWNLOAD_FOLDER):
            if f == '.gitkeep': continue
            f_path = os.path.join(DOWNLOAD_FOLDER, f)
            if os.stat(f_path).st_mtime < now - 3600:
                try:
                    os.remove(f_path)
                except Exception as e:
                    print(f"Error deleting {f_path}: {e}")
        time.sleep(1800)

# Run update check
check_for_updates()

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_formats', methods=['POST'])
def fetch_formats():
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'No URL provided'}), 400

    print(f">>> Extraction started for: {url}")
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'socket_timeout': 15,
        'extract_flat': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                print(f">>> Extraction failed: {str(e)}")
                return jsonify({'status': 'error', 'message': 'Unable to extract downloadable video or audio from this URL.'}), 500
            
            # Handle entries (playlists) by taking the first item
            if 'entries' in info and not info.get('formats'):
                entries = [e for e in info['entries'] if e]
                if entries:
                    info = entries[0]
            
            formats = info.get('formats', [])
            clean_formats = []
            resolutions = {}
            
            # Stable Preview: Favor high-res thumbnail
            preview_url = info.get('thumbnail')

            for f in formats:
                height = f.get('height')
                ext = (f.get('ext') or '').lower()
                vcodec = f.get('vcodec')
                filesize = f.get('filesize') or f.get('filesize_approx')
                
                # Filter for Video resolutions
                if height and vcodec != 'none':
                    res_str = f"{height}p"
                    if res_str not in resolutions or (filesize and (not resolutions[res_str].get('size') or filesize > resolutions[res_str]['size'])):
                        resolutions[res_str] = {
                            'resolution': res_str,
                            'ext': ext,
                            'size': filesize,
                            'height': height
                        }

            # Sort and add video formats
            sorted_res = sorted(resolutions.values(), key=lambda x: x['height'], reverse=True)
            for item in sorted_res:
                size_str = f"{round(item['size'] / (1024*1024), 1)} MB" if item['size'] else "N/A"
                clean_formats.append({
                    'id': item['resolution'],
                    'label': f"{item['resolution']} | {item['ext']} | {size_str}",
                    'type': 'video',
                    'height': item['height']
                })

            # Add Audio option if video/audio was found
            if sorted_res or any(f.get('acodec') != 'none' for f in formats):
                clean_formats.append({
                    'id': 'audio',
                    'label': 'Audio Only | mp3 | Best Quality',
                    'type': 'audio'
                })

            if not clean_formats:
                return jsonify({'status': 'error', 'message': 'No downloadable video or audio formats found for this URL.'}), 500

            print(f">>> Extraction successful: {info.get('title')}")
            return jsonify({
                'success': True,
                'title': info.get('title', 'Media Content'),
                'formats': clean_formats,
                'preview_url': preview_url
            })

    except Exception as e:
        print(f">>> Unexpected global fetch error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Server error: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_id = request.form.get('format_id')
    download_type = request.form.get('type')

    if not url or not format_id or not download_type:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

    print(f">>> Download started: {url} ({format_id})")
    
    random_id = secrets.token_hex(4)
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)u__{random_id}.%(ext)s')

    common_opts = {
        'outtmpl': outtmpl,
        'restrictfilenames': True,
        'socket_timeout': 15,
        'quiet': True,
        'no_warnings': True,
    }

    if download_type == 'audio':
        ydl_opts = {
            **common_opts,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        try:
            height = int(format_id.replace('p', ''))
            fmt_str = f'bestvideo[height<={height}]+bestaudio/best'
        except:
            fmt_str = 'best'
            
        ydl_opts = {
            **common_opts,
            'format': fmt_str,
            'noplaylist': True,
            'merge_output_format': 'mp4',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Check for entries in case it's a playlist item
            if 'entries' in info:
                info = info['entries'][0]

            if download_type == 'audio':
                expected_filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            else:
                expected_filename = ydl.prepare_filename(info)
                if not os.path.exists(expected_filename):
                    base = expected_filename.rsplit('.', 1)[0]
                    for ext in ['mp4', 'mkv', 'webm']:
                        if os.path.exists(f"{base}.{ext}"):
                            expected_filename = f"{base}.{ext}"
                            break

            # Emergency locator
            if not os.path.exists(expected_filename):
                base_pattern = f"__{random_id}."
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if base_pattern in f:
                        expected_filename = os.path.join(DOWNLOAD_FOLDER, f)
                        break

            if not os.path.exists(expected_filename):
                raise FileNotFoundError("Could not locate the downloaded file.")

            file_basename = os.path.basename(expected_filename)
            print(f">>> Download completed: {file_basename}")
            return jsonify({
                'success': True,
                'filename': file_basename,
                'download_url': f'/get-file/{file_basename}'
            })

    except Exception as e:
        print(f">>> Download crash: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Download failed: {str(e)}'}), 500

@app.route('/get-file/<filename>')
def get_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    print(">>> Server started on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
