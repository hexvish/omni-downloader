import os
import re
import secrets
import shutil
import subprocess
import zipfile
import threading
import time
import yt_dlp
from config import YDL_COMMON_OPTS, DOWNLOAD_FOLDER, FFMPEG_PATH

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

def cleanup_playlist_directory(playlist_dir, fallback_ext='mp4'):
    """
    Cleans up playlist directory before zipping:
    1. Removes any 0-byte files (e.g. failed .temp files).
    2. Removes .temp, .part, .ytdl files.
    3. If any split stream pairs (.fXXX.mp4 + .fXXX.webm) remain unmerged,
       merges them using FFmpeg into a proper video file.
    4. Removes any leftover unmerged format fragments (.f\d+.*).
    """
    for root, dirs, files in os.walk(playlist_dir):
        for f in files:
            p = os.path.join(root, f)
            if not os.path.exists(p):
                continue
            if os.path.getsize(p) == 0 or f.endswith('.temp') or f.endswith('.part') or '.temp.' in f or f.endswith('.ytdl'):
                try:
                    os.remove(p)
                except Exception:
                    pass

    fragments = {}
    for root, dirs, files in os.walk(playlist_dir):
        for f in files:
            m = re.match(r'^(.*?)\.f\d+\.(mp4|webm|m4a|mkv)$', f)
            if m:
                base = m.group(1)
                fragments.setdefault(base, []).append(os.path.join(root, f))

    if fragments and FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        for base, parts in fragments.items():
            target_out = os.path.join(playlist_dir, f"{base}.{fallback_ext}")
            if not os.path.exists(target_out) and len(parts) >= 2:
                cmd = [FFMPEG_PATH, '-y']
                for part in parts:
                    cmd.extend(['-i', part])
                cmd.extend(['-c:v', 'copy', '-c:a', 'aac', target_out])
                try:
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
                except Exception:
                    pass

            if os.path.exists(target_out) and os.path.getsize(target_out) > 0:
                for part in parts:
                    try:
                        os.remove(part)
                    except Exception:
                        pass

def _run_single_download(task_id, url, download_type, codec, bitrate, resolution):
    random_id = secrets.token_hex(4)
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id]['random_id'] = random_id
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)s__{random_id}.%(ext)s')

    def progress_hook(d):
        with tasks_lock:
            if task_id in tasks and tasks[task_id].get('cancelled'):
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
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
                if task_id in tasks and tasks[task_id].get('cancelled'):
                    raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
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

        chosen_container = (codec or 'mp4').lower()
        if chosen_container not in ('mp4', 'mkv', 'webm'):
            chosen_container = 'mp4'
        ydl_opts.update({
            'format': fmt_str,
            'merge_output_format': chosen_container,
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

        with tasks_lock:
            if task_id in tasks and tasks[task_id].get('cancelled'):
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if f"__{random_id}." in f or f"__{random_id}" in f:
                        try:
                            os.remove(os.path.join(DOWNLOAD_FOLDER, f))
                        except Exception:
                            pass
                tasks[task_id]['status'] = 'cancelled'
                tasks[task_id]['error'] = 'Download cancelled by user.'
                return

        matched_file = find_file_by_id(DOWNLOAD_FOLDER, random_id)
        if not matched_file:
            raise FileNotFoundError("Could not locate the downloaded file on disk.")

        with tasks_lock:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['progress'] = 100.0
            tasks[task_id]['filename'] = matched_file
            tasks[task_id]['download_url'] = f'/get-file/{matched_file}'
    except (yt_dlp.utils.DownloadCancelled, Exception) as e:
        is_cancelled = False
        with tasks_lock:
            if task_id in tasks and tasks[task_id].get('cancelled'):
                is_cancelled = True
        if isinstance(e, yt_dlp.utils.DownloadCancelled) or is_cancelled:
            print(f">>> Task {task_id} cancelled by user. Cleaning up files...")
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f"__{random_id}." in f or f"__{random_id}" in f:
                    try:
                        os.remove(os.path.join(DOWNLOAD_FOLDER, f))
                    except Exception:
                        pass
            with tasks_lock:
                tasks[task_id]['status'] = 'cancelled'
                tasks[task_id]['error'] = 'Download cancelled by user.'
        else:
            print(f">>> Single download error for task {task_id}: {e}")
            with tasks_lock:
                tasks[task_id]['status'] = 'error'
                tasks[task_id]['error'] = str(e)

def _run_playlist_download(task_id, url, download_type, codec, bitrate, resolution, initial_total=1):
    playlist_id = secrets.token_hex(4)
    playlist_dir = os.path.join(DOWNLOAD_FOLDER, f"playlist_{playlist_id}")
    os.makedirs(playlist_dir, exist_ok=True)
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id]['playlist_dir'] = playlist_dir

    track_stats = {'current_index': 1, 'total_items': initial_total or 1, 'completed_items': 0}

    def progress_hook(d):
        with tasks_lock:
            if task_id in tasks and tasks[task_id].get('cancelled'):
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
        if d.get('status') == 'downloading':
            info_dict = d.get('info_dict', {})
            idx = info_dict.get('playlist_index') or track_stats['current_index']
            total = info_dict.get('n_entries') or track_stats['total_items']
            track_stats['current_index'] = idx
            track_stats['total_items'] = total
            track_stats['completed_items'] = max(track_stats['completed_items'], idx - 1)

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
                    tasks[task_id]['completed_items'] = track_stats['completed_items']
                    tasks[task_id]['current_title'] = title
                    tasks[task_id]['speed'] = speed_str
                    tasks[task_id]['progress'] = min(95.0, overall_pct)
                    tasks[task_id]['status'] = 'downloading'
        elif d.get('status') == 'finished':
            with tasks_lock:
                if task_id in tasks and tasks[task_id].get('cancelled'):
                    raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
                if task_id in tasks:
                    tasks[task_id]['status'] = 'converting'
                    tasks[task_id]['current_item'] = track_stats['current_index']
                    tasks[task_id]['total_items'] = track_stats['total_items']
                    tasks[task_id]['completed_items'] = track_stats['completed_items']

    def postprocessor_hook(d):
        with tasks_lock:
            if task_id in tasks and tasks[task_id].get('cancelled'):
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
        if d.get('status') == 'finished':
            idx = track_stats['current_index']
            with tasks_lock:
                if task_id in tasks:
                    track_stats['completed_items'] = max(track_stats['completed_items'], idx)
                    tasks[task_id]['completed_items'] = track_stats['completed_items']

    outtmpl = os.path.join(playlist_dir, '%(playlist_index)02d - %(title)s.%(ext)s')

    ydl_opts = {
        **YDL_COMMON_OPTS,
        'outtmpl': outtmpl,
        'ignoreerrors': True,
        'progress_hooks': [progress_hook],
        'postprocessor_hooks': [postprocessor_hook],
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

        chosen_container = (codec or 'mp4').lower()
        if chosen_container not in ('mp4', 'mkv', 'webm'):
            chosen_container = 'mp4'

        ydl_opts.update({
            'format': fmt_str,
            'merge_output_format': chosen_container,
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
            if task_id in tasks and tasks[task_id].get('cancelled'):
                shutil.rmtree(playlist_dir, ignore_errors=True)
                tasks[task_id]['status'] = 'cancelled'
                tasks[task_id]['error'] = 'Download cancelled by user.'
                return

        with tasks_lock:
            tasks[task_id]['status'] = 'zipping'
            tasks[task_id]['progress'] = 98.0
            tasks[task_id]['completed_items'] = track_stats['total_items']

        # Clean up directory and finalize any unmerged stream fragments before zipping
        cleanup_playlist_directory(playlist_dir, fallback_ext=chosen_container if download_type == 'video' else (codec or 'mp3'))

        # Safe zip filename
        safe_title = "".join(c for c in (playlist_title or 'Playlist') if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_title = safe_title.replace(' ', '_') or 'Playlist'
        zip_filename = f"{safe_title}_{playlist_id}.zip"
        zip_path = os.path.join(DOWNLOAD_FOLDER, zip_filename)
        with tasks_lock:
            if task_id in tasks:
                tasks[task_id]['zip_path'] = zip_path

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(playlist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Exclude 0-byte files, temp/part files, and any format fragments
                    if os.path.getsize(file_path) == 0:
                        continue
                    if file.endswith('.temp') or file.endswith('.part') or '.temp.' in file or file.endswith('.ytdl'):
                        continue
                    if re.search(r'\.f\d+\.(mp4|webm|m4a|mkv)$', file):
                        continue
                    arcname = os.path.relpath(file_path, playlist_dir)
                    zipf.write(file_path, arcname)

        shutil.rmtree(playlist_dir, ignore_errors=True)

        if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
            raise Exception("Failed to generate playlist ZIP archive.")

        with tasks_lock:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['progress'] = 100.0
            tasks[task_id]['completed_items'] = track_stats['total_items']
            tasks[task_id]['filename'] = zip_filename
            tasks[task_id]['download_url'] = f'/get-file/{zip_filename}'
    except (yt_dlp.utils.DownloadCancelled, Exception) as e:
        shutil.rmtree(playlist_dir, ignore_errors=True)
        if 'zip_path' in locals() and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass
        is_cancelled = False
        with tasks_lock:
            if task_id in tasks and tasks[task_id].get('cancelled'):
                is_cancelled = True
        if isinstance(e, yt_dlp.utils.DownloadCancelled) or is_cancelled:
            print(f">>> Playlist task {task_id} cancelled by user. Cleaned up.")
            with tasks_lock:
                tasks[task_id]['status'] = 'cancelled'
                tasks[task_id]['error'] = 'Download cancelled by user.'
        else:
            print(f">>> Playlist download error for task {task_id}: {e}")
            with tasks_lock:
                tasks[task_id]['status'] = 'error'
                tasks[task_id]['error'] = str(e)

def cancel_task(task_id):
    """
    Signals a task to cancel, marks status as 'cancelled',
    and removes any temporary/partial files created by it immediately.
    """
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id]['cancelled'] = True
            tasks[task_id]['status'] = 'cancelled'
            tasks[task_id]['error'] = 'Download cancelled by user.'

            # Immediate disk cleanup of partial/temporary files
            random_id = tasks[task_id].get('random_id')
            if random_id and os.path.exists(DOWNLOAD_FOLDER):
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if f"__{random_id}." in f or f"__{random_id}" in f:
                        try:
                            os.remove(os.path.join(DOWNLOAD_FOLDER, f))
                        except Exception:
                            pass

            playlist_dir = tasks[task_id].get('playlist_dir')
            if playlist_dir and os.path.exists(playlist_dir):
                shutil.rmtree(playlist_dir, ignore_errors=True)

            zip_path = tasks[task_id].get('zip_path')
            if zip_path and os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except Exception:
                    pass

            return True
    return False

def start_download_task(url, download_type='audio', codec='mp3', bitrate='320', resolution='1080p', is_playlist=False, total_items=1):
    """
    Start an asynchronous download task in a background worker thread.
    Returns the unique task_id.
    """
    task_id = secrets.token_hex(8)
    initial_total = int(total_items) if total_items else 1
    with tasks_lock:
        tasks[task_id] = {
            'task_id': task_id,
            'status': 'starting',
            'progress': 0.0,
            'current_item': 1,
            'total_items': initial_total,
            'completed_items': 0,
            'current_title': '',
            'speed': '',
            'is_playlist': is_playlist,
            'filename': None,
            'download_url': None,
            'error': None,
            'created_at': time.time()
        }

    if is_playlist:
        worker = threading.Thread(
            target=_run_playlist_download,
            args=(task_id, url, download_type, codec, bitrate, resolution, initial_total),
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

