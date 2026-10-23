import os
import sys
import json
import shutil
import zipfile
import yt_dlp

def get_ffmpeg_path():
    """Detects if ffmpeg exists in PATH or app directories."""
    path = shutil.which('ffmpeg')
    if path:
        return path
    # Check common Android native library paths if bundled
    possible_paths = [
        '/data/data/com.hexvish.omnidownloader/lib/libffmpeg.so',
        '/data/data/com.hexvish.omnidownloader/files/ffmpeg'
    ]
    for p in possible_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return None

def extract_media_info(url):
    """
    Extracts metadata, formats, and playlist details using yt-dlp.
    Returns JSON string for Kotlin consumption.
    """
    is_playlist_url = ('list=' in url or '/playlist' in url)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'extract_flat': is_playlist_url,
        'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            raw_info = ydl.extract_info(url, download=False)
            if not raw_info:
                return json.dumps({'status': 'error', 'message': 'No media information found for this URL.'})

            is_playlist = (raw_info.get('_type') == 'playlist' or 'entries' in raw_info)
            if is_playlist and 'entries' in raw_info:
                entries = [e for e in raw_info['entries'] if e]
                tracklist = []
                for idx, entry in enumerate(entries, 1):
                    dur = entry.get('duration') or 0
                    mins, secs = divmod(int(dur), 60)
                    dur_str = f"{mins}:{secs:02d}" if dur else ""
                    tracklist.append({
                        'index': idx,
                        'title': entry.get('title') or f"Track {idx}",
                        'url': entry.get('url') or entry.get('webpage_url') or url,
                        'duration': dur,
                        'duration_str': dur_str,
                        'uploader': entry.get('uploader') or entry.get('channel') or ''
                    })

                thumb = raw_info.get('thumbnail') or (entries[0].get('thumbnail') if entries else '')
                return json.dumps({
                    'status': 'success',
                    'is_playlist': True,
                    'title': raw_info.get('title') or 'Playlist',
                    'uploader': raw_info.get('uploader') or 'Various Artists',
                    'thumbnail': thumb,
                    'total_tracks': len(tracklist),
                    'tracks': tracklist
                })
            else:
                duration = raw_info.get('duration') or 0
                mins, secs = divmod(int(duration), 60)
                dur_str = f"{mins}:{secs:02d}" if duration else ""

                return json.dumps({
                    'status': 'success',
                    'is_playlist': False,
                    'title': raw_info.get('title') or 'Unknown Title',
                    'uploader': raw_info.get('uploader') or raw_info.get('channel') or '',
                    'thumbnail': raw_info.get('thumbnail') or '',
                    'duration_str': dur_str,
                    'duration': duration,
                    'view_count': raw_info.get('view_count') or 0
                })
    except Exception as e:
        return json.dumps({
            'status': 'error',
            'message': str(e)
        })

def run_download(url, download_type, codec, bitrate, resolution, is_playlist, output_dir, progress_listener, selected_indices=None):
    """
    Downloads media and triggers Kotlin progress listener with percent, speed, and status.
    Handles single media and playlists (packaged into zip).
    """
    os.makedirs(output_dir, exist_ok=True)
    ffmpeg_exe = get_ffmpeg_path()

    def sanitize_title(title):
        return "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '.', '(', ')')).strip()

    if is_playlist:
        # Download playlist tracks and package into zip
        return _download_playlist(url, download_type, codec, bitrate, resolution, output_dir, progress_listener, ffmpeg_exe, selected_indices)
    else:
        return _download_single(url, download_type, codec, bitrate, resolution, output_dir, progress_listener, ffmpeg_exe)

def _download_single(url, download_type, codec, bitrate, resolution, output_dir, progress_listener, ffmpeg_exe):
    outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')

    def hook(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed else ""
            pct = min(98.0, round((downloaded / total) * 100, 1)) if total > 0 else 50.0
            if progress_listener:
                progress_listener.onProgress(float(pct), speed_str, "Downloading stream...")
        elif d.get('status') == 'finished':
            if progress_listener:
                progress_listener.onProgress(99.0, "", "Finalizing file...")

    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [hook],
        'restrictfilenames': False,
        'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    }

    if ffmpeg_exe:
        ydl_opts['ffmpeg_location'] = ffmpeg_exe

    if download_type == 'audio':
        chosen_codec = (codec or 'mp3').lower()
        chosen_bitrate = bitrate if (bitrate and bitrate != 'Lossless') else '320'
        if ffmpeg_exe:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': chosen_codec,
                    'preferredquality': chosen_bitrate,
                }, {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }]
            })
        else:
            # Native fallback: download direct audio stream (m4a or best)
            ydl_opts.update({
                'format': 'bestaudio[ext=m4a]/bestaudio/best'
            })
    else:
        # Video download
        chosen_container = (codec or 'mp4').lower()
        if ffmpeg_exe:
            try:
                h = int(str(resolution).replace('p', ''))
                fmt_str = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'
            except Exception:
                fmt_str = 'bestvideo+bestaudio/best'
            ydl_opts.update({
                'format': fmt_str,
                'merge_output_format': chosen_container,
                'postprocessors': [{
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }]
            })
        else:
            # Without ffmpeg, select best direct mp4 stream (contains both video and audio)
            ydl_opts.update({
                'format': 'best[ext=mp4]/best'
            })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if download_type == 'audio' and ffmpeg_exe:
                base, _ = os.path.splitext(filename)
                filename = f"{base}.{(codec or 'mp3').lower()}"
            elif not os.path.exists(filename):
                # Search for matching file in output_dir
                base, _ = os.path.splitext(filename)
                for f in os.listdir(output_dir):
                    if f.startswith(os.path.basename(base)):
                        filename = os.path.join(output_dir, f)
                        break

            if progress_listener:
                progress_listener.onProgress(100.0, "", "Complete")
                progress_listener.onCompleted(filename)
            return filename
    except Exception as e:
        if progress_listener:
            progress_listener.onError(str(e))
        raise e

def _download_playlist(url, download_type, codec, bitrate, resolution, output_dir, progress_listener, ffmpeg_exe, selected_indices=None):
    temp_dir = os.path.join(output_dir, 'playlist_temp')
    os.makedirs(temp_dir, exist_ok=True)

    ydl_opts_meta = {
        'quiet': True,
        'extract_flat': True,
        'socket_timeout': 20,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            raw = ydl.extract_info(url, download=False)
            playlist_title = raw.get('title') or 'Playlist'
            entries = [e for e in raw.get('entries', []) if e]

        selected_set = set(int(x) for x in selected_indices) if selected_indices else None
        tracks_to_dl = []
        for idx, entry in enumerate(entries, 1):
            if selected_set is None or idx in selected_set:
                tracks_to_dl.append((idx, entry))

        total_tracks = len(tracks_to_dl)
        if total_tracks == 0:
            raise Exception("No tracks selected for download.")

        downloaded_files = []
        for i, (track_idx, entry) in enumerate(tracks_to_dl):
            track_url = entry.get('url') or entry.get('webpage_url')
            if not track_url:
                continue

            track_title = entry.get('title') or f"Track_{track_idx}"
            if progress_listener:
                base_pct = (i / total_tracks) * 90.0
                progress_listener.onProgress(float(base_pct), "", f"Downloading ({i+1}/{total_tracks}): {track_title[:28]}...")

            out_file = _download_single(track_url, download_type, codec, bitrate, resolution, temp_dir, None, ffmpeg_exe)
            if out_file and os.path.exists(out_file):
                downloaded_files.append(out_file)

        if progress_listener:
            progress_listener.onProgress(92.0, "", "Compressing playlist into ZIP...")

        clean_pl_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '-', '_', '.', '(', ')')).strip()
        zip_path = os.path.join(output_dir, f"{clean_pl_title}.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in downloaded_files:
                zipf.write(f, os.path.basename(f))

        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        if progress_listener:
            progress_listener.onProgress(100.0, "", "Complete")
            progress_listener.onCompleted(zip_path)

        return zip_path
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if progress_listener:
            progress_listener.onError(str(e))
        raise e
