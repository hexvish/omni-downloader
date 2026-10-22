import os
import secrets
import shutil
import zipfile
import threading
import time
import yt_dlp
from config import YDL_COMMON_OPTS, DOWNLOAD_FOLDER

# Thread-safe in-memory task tracker
tasks_lock = threading.Lock()
tasks = {}

def extract_media_info(url, is_playlist=None):
    """
    Extract metadata from a URL using yt-dlp.
    Supports single videos, YouTube Music, and playlists.
    """
    is_playlist_url = ('list=' in url or '/playlist' in url)
    if is_playlist is None:
        is_playlist = is_playlist_url

    if is_playlist:
        ydl_opts = {
            **YDL_COMMON_OPTS,
            'extract_flat': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info.get('_type') == 'playlist' or ('entries' in info and len(info.get('entries', [])) > 0):
                    return info
            except Exception as e:
                print(f">>> Playlist extraction fallback to single: {e}")

    # Fallback or single media extraction
    single_opts = {
        **YDL_COMMON_OPTS,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(single_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and not info.get('formats'):
                entries = [e for e in info['entries'] if e]
                if entries:
                    info = entries[0]
            return info
        except Exception as e:
            raise Exception(f"yt-dlp extraction failed: {str(e)}")

def find_file_by_id(folder, random_id):
    """Finds downloaded file in folder containing random_id suffix"""
    base_pattern = f"__{random_id}."
    for f in os.listdir(folder):
        if base_pattern in f and not f.endswith('.temp') and not f.endswith('.part'):
            return f
    return None

def _run_single_download(task_id, url, download_type, codec, bitrate, resolution):
    random_id = secrets.token_hex(4)
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)s__{random_id}.%(ext)s')

    def progress_hook(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed else ""
            pct = min(98.0, round((downloaded / total) * 100, 1)) if total > 0 else 50.0
            with tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['progress'] = pct
                    tasks[task_id]['speed'] = speed_str
                    tasks[task_id]['status'] = 'downloading'
        elif d.get('status') == 'finished':
            with tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['progress'] = 99.0
                    tasks[task_id]['status'] = 'converting'

    ydl_opts = {
        **YDL_COMMON_OPTS,
        'outtmpl': outtmpl,
        'noplaylist': True,
        'progress_hooks': [progress_hook],
    }

    if download_type == 'audio':
        chosen_codec = (codec or 'mp3').lower()
        chosen_quality = bitrate if (bitrate and bitrate != 'Lossless') else '320'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': chosen_codec,
            'preferredquality': chosen_quality,
        }, {
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }]
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': postprocessors,
        })
    else:
        try:
            height = int(str(resolution).replace('p', ''))
            fmt_str = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
        except Exception:
            fmt_str = 'bestvideo+bestaudio/best'

        ydl_opts.update({
            'format': fmt_str,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }]
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info:
                info = info['entries'][0]

        matched_file = find_file_by_id(DOWNLOAD_FOLDER, random_id)
        if not matched_file:
            raise FileNotFoundError("Could not locate the downloaded file on disk.")

        with tasks_lock:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['progress'] = 100.0
            tasks[task_id]['filename'] = matched_file
            tasks[task_id]['download_url'] = f'/get-file/{matched_file}'
    except Exception as e:
        print(f">>> Single download error for task {task_id}: {e}")
        with tasks_lock:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = str(e)

def _run_playlist_download(task_id, url, download_type, codec, bitrate, resolution):
    playlist_id = secrets.token_hex(4)
    playlist_dir = os.path.join(DOWNLOAD_FOLDER, f"playlist_{playlist_id}")
    os.makedirs(playlist_dir, exist_ok=True)

    track_stats = {'current_index': 1, 'total_items': 1}

    def progress_hook(d):
        if d.get('status') == 'downloading':
            info_dict = d.get('info_dict', {})
            idx = info_dict.get('playlist_index') or track_stats['current_index']
            total = info_dict.get('n_entries') or track_stats['total_items']
            track_stats['current_index'] = idx
            track_stats['total_items'] = total

            title = info_dict.get('title') or ''
            speed = d.get('speed') or 0
            speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed else ""

            track_total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            track_down = d.get('downloaded_bytes') or 0
            track_pct = (track_down / track_total) if track_total > 0 else 0

            overall_pct = round(((idx - 1 + track_pct) / max(total, 1)) * 95, 1)

            with tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['current_item'] = idx
                    tasks[task_id]['total_items'] = total
                    tasks[task_id]['current_title'] = title
                    tasks[task_id]['speed'] = speed_str
                    tasks[task_id]['progress'] = min(95.0, overall_pct)
                    tasks[task_id]['status'] = 'downloading'
        elif d.get('status') == 'finished':
            with tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['status'] = 'converting'

    outtmpl = os.path.join(playlist_dir, '%(playlist_index)02d - %(title)s.%(ext)s')

    ydl_opts = {
        **YDL_COMMON_OPTS,
        'outtmpl': outtmpl,
        'ignoreerrors': True,
        'progress_hooks': [progress_hook],
    }

    if download_type == 'audio':
        chosen_codec = (codec or 'mp3').lower()
        chosen_quality = bitrate if (bitrate and bitrate != 'Lossless') else '320'
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': chosen_codec,
                'preferredquality': chosen_quality,
            }, {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }]
        })
    else:
        try:
            height = int(str(resolution).replace('p', ''))
            fmt_str = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
        except Exception:
            fmt_str = 'bestvideo+bestaudio/best'

        ydl_opts.update({
            'format': fmt_str,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }]
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(url, download=True)
            playlist_title = playlist_info.get('title') if playlist_info else 'Playlist'

        with tasks_lock:
            tasks[task_id]['status'] = 'zipping'
            tasks[task_id]['progress'] = 98.0

        # Safe zip filename
        safe_title = "".join(c for c in (playlist_title or 'Playlist') if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_title = safe_title.replace(' ', '_') or 'Playlist'
        zip_filename = f"{safe_title}_{playlist_id}.zip"
        zip_path = os.path.join(DOWNLOAD_FOLDER, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(playlist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, playlist_dir)
                    zipf.write(file_path, arcname)

        shutil.rmtree(playlist_dir, ignore_errors=True)

        if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
            raise Exception("Failed to generate playlist ZIP archive.")

        with tasks_lock:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['progress'] = 100.0
            tasks[task_id]['filename'] = zip_filename
            tasks[task_id]['download_url'] = f'/get-file/{zip_filename}'
    except Exception as e:
        print(f">>> Playlist download error for task {task_id}: {e}")
        shutil.rmtree(playlist_dir, ignore_errors=True)
        with tasks_lock:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = str(e)

def start_download_task(url, download_type='audio', codec='mp3', bitrate='320', resolution='1080p', is_playlist=False):
    """
    Start an asynchronous download task in a background worker thread.
    Returns the unique task_id.
    """
    task_id = secrets.token_hex(8)
    with tasks_lock:
        tasks[task_id] = {
            'task_id': task_id,
            'status': 'starting',
            'progress': 0.0,
            'current_item': 1,
            'total_items': 1,
            'current_title': '',
            'speed': '',
            'filename': None,
            'download_url': None,
            'error': None,
            'created_at': time.time()
        }

    if is_playlist:
        worker = threading.Thread(
            target=_run_playlist_download,
            args=(task_id, url, download_type, codec, bitrate, resolution),
            daemon=True
        )
    else:
        worker = threading.Thread(
            target=_run_single_download,
            args=(task_id, url, download_type, codec, bitrate, resolution),
            daemon=True
        )

    worker.start()
    return task_id

def get_task_status(task_id):
    """Retrieve current task execution state"""
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return None
        return dict(task)

def download_media(url, format_id, download_type):
    """Synchronous download helper for backward compatibility"""
    codec = 'mp3'
    bitrate = '320'
    resolution = format_id if download_type == 'video' else None

    # Parse format_id if encoded like 'mp3-320'
    if '-' in format_id and download_type == 'audio':
        parts = format_id.split('-')
        codec = parts[0]
        bitrate = parts[1]

    task_id = start_download_task(
        url=url,
        download_type=download_type,
        codec=codec,
        bitrate=bitrate,
        resolution=resolution,
        is_playlist=False
    )

    while True:
        status = get_task_status(task_id)
        if not status:
            raise Exception("Task was aborted or lost.")
        if status['status'] == 'completed':
            return status['filename']
        if status['status'] == 'error':
            raise Exception(status.get('error', 'Download failed'))
        time.sleep(0.5)

