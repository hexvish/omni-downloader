import os
import sys
import json
import re
import yt_dlp
from yt_dlp.utils import sanitize_filename

def extract_media_info(url):
    """
    Extracts metadata, formats, and playlist details using yt-dlp across multiple platforms.
    Returns JSON string for Kotlin consumption.
    """
    is_playlist_url = ('list=' in url or '/playlist' in url)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
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
                    vid_id = entry.get('id') or entry.get('url') or ''
                    clean_track_url = f"https://www.youtube.com/watch?v={vid_id}" if (vid_id and not str(vid_id).startswith('http')) else (entry.get('url') or entry.get('webpage_url') or url)

                    tracklist.append({
                        'index': idx,
                        'title': entry.get('title') or f"Item {idx}",
                        'url': clean_track_url,
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

def _clean_single_url(url):
    """Strips playlist parameters so single-item downloads never trigger playlist parsing."""
    if not url.startswith('http'):
        return f"https://www.youtube.com/watch?v={url}"
    cleaned = re.sub(r'[?&]list=[^&]+', '', url)
    cleaned = re.sub(r'[?&]index=[^&]+', '', cleaned)
    if '?' not in cleaned and '&' in cleaned:
        cleaned = cleaned.replace('&', '?', 1)
    return cleaned

def run_download(url, download_type, is_playlist, output_dir, progress_listener, selected_indices_raw=None):
    os.makedirs(output_dir, exist_ok=True)

    # Safely parse selected indices
    selected_indices = None
    if selected_indices_raw:
        try:
            if isinstance(selected_indices_raw, str):
                selected_indices = json.loads(selected_indices_raw)
            else:
                selected_indices = list(selected_indices_raw)
        except Exception:
            selected_indices = None

    if is_playlist:
        return _download_playlist(url, download_type, output_dir, progress_listener, selected_indices)
    else:
        return _download_single(url, download_type, output_dir, progress_listener)

def _download_single(url, download_type, output_dir, progress_listener):
    clean_url = _clean_single_url(url)

    if download_type == 'audio':
        return _download_single_audio(clean_url, output_dir, progress_listener)
    else:
        return _download_single_video(clean_url, output_dir, progress_listener)

def _download_single_audio(clean_url, output_dir, progress_listener):
    outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')

    def hook(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed else ""
            pct = min(99.0, round((downloaded / total) * 100, 1)) if total > 0 else 50.0
            if progress_listener:
                try:
                    progress_listener.onProgress(float(pct), speed_str, "Downloading audio...")
                except Exception:
                    pass

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'progress_hooks': [hook],
        'restrictfilenames': False,
        'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            if not info:
                raise Exception("Audio stream is unavailable or protected.")

            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                for f in os.listdir(output_dir):
                    if f.startswith(os.path.basename(base)):
                        filename = os.path.join(output_dir, f)
                        break

            if progress_listener:
                try:
                    progress_listener.onProgress(100.0, "", "Complete")
                    progress_listener.onCompleted(filename)
                except Exception:
                    pass
            return filename
    except Exception as e:
        if progress_listener:
            try:
                progress_listener.onError(str(e))
            except Exception:
                pass
        raise e

def _download_single_video(clean_url, output_dir, progress_listener):
    """
    Downloads video with full audio:
    - If platform offers single pre-combined video+audio stream (TikTok, IG, Twitter, Reddit), downloads directly.
    - If platform separates streams (YouTube 720p/1080p), downloads MP4 video and M4A audio, then merges via Android MediaMuxer.
    """
    # 1. Probe available formats
    probe_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 15,
        'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    }

    with yt_dlp.YoutubeDL(probe_opts) as ydl_probe:
        info = ydl_probe.extract_info(clean_url, download=False)
        if not info:
            raise Exception("Video information could not be retrieved.")

    formats = info.get('formats') or []
    has_combined = any(f.get('vcodec') != 'none' and f.get('acodec') != 'none' for f in formats)

    # If stream already has both video and audio combined (non-YouTube platforms or format 18)
    if has_combined and ('youtube.com' not in clean_url and 'youtu.be' not in clean_url):
        outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')
        def hook(d):
            if d.get('status') == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed else ""
                pct = min(99.0, round((downloaded / total) * 100, 1)) if total > 0 else 50.0
                if progress_listener:
                    try:
                        progress_listener.onProgress(float(pct), speed_str, "Downloading video...")
                    except Exception:
                        pass

        ydl_opts = {
            'format': 'best[acodec!=none][vcodec!=none]/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'progress_hooks': [hook],
            'restrictfilenames': False,
            'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            dl_info = ydl.extract_info(clean_url, download=True)
            filename = ydl.prepare_filename(dl_info)
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                for f in os.listdir(output_dir):
                    if f.startswith(os.path.basename(base)):
                        filename = os.path.join(output_dir, f)
                        break
            if progress_listener:
                try:
                    progress_listener.onProgress(100.0, "", "Complete")
                    progress_listener.onCompleted(filename)
                except Exception:
                    pass
            return filename

    # YouTube (or separate stream platforms): Download H.264 MP4 video and AAC M4A audio, then mux via MediaMuxer
    vid_id = info.get('id', 'temp')
    title = sanitize_filename(info.get('title') or f"video_{vid_id}")
    final_filename = os.path.join(output_dir, f"{title}.mp4")
    temp_vid = os.path.join(output_dir, f"_temp_vid_{vid_id}.mp4")
    temp_aud = os.path.join(output_dir, f"_temp_aud_{vid_id}.m4a")

    # Clean previous temp files if any
    for t in (temp_vid, temp_aud):
        if os.path.exists(t):
            try: os.remove(t)
            except Exception: pass

    def hook_vid(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed else ""
            pct = min(80.0, round((downloaded / total) * 80.0, 1)) if total > 0 else 40.0
            if progress_listener:
                try:
                    progress_listener.onProgress(float(pct), speed_str, "Downloading video track...")
                except Exception:
                    pass

    def hook_aud(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed else ""
            pct = 80.0 + (min(18.0, round((downloaded / total) * 18.0, 1)) if total > 0 else 10.0)
            if progress_listener:
                try:
                    progress_listener.onProgress(float(pct), speed_str, "Downloading audio track...")
                except Exception:
                    pass

    vid_opts = {
        'format': 'bestvideo[ext=mp4][vcodec^=avc1]/bestvideo[ext=mp4]/bestvideo',
        'outtmpl': temp_vid,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'progress_hooks': [hook_vid],
        'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    }

    aud_opts = {
        'format': 'bestaudio[ext=m4a][acodec^=mp4a]/bestaudio[ext=m4a]/bestaudio',
        'outtmpl': temp_aud,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'progress_hooks': [hook_aud],
        'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    }

    try:
        # Download video stream
        with yt_dlp.YoutubeDL(vid_opts) as ydl_v:
            ydl_v.extract_info(clean_url, download=True)

        # Download audio stream
        with yt_dlp.YoutubeDL(aud_opts) as ydl_a:
            ydl_a.extract_info(clean_url, download=True)

        # Mux via Android native MediaMuxer
        if progress_listener:
            try:
                progress_listener.onProgress(99.0, "", "Muxing video & audio into MP4...")
            except Exception:
                pass

        from com.hexvish.omnidownloader.util import MediaMuxerHelper
        mux_ok = MediaMuxerHelper.mux(temp_vid, temp_aud, final_filename)

        # Clean temp files
        for t in (temp_vid, temp_aud):
            if os.path.exists(t):
                try: os.remove(t)
                except Exception: pass

        if mux_ok and os.path.exists(final_filename):
            if progress_listener:
                try:
                    progress_listener.onProgress(100.0, "", "Complete")
                    progress_listener.onCompleted(final_filename)
                except Exception:
                    pass
            return final_filename
        else:
            raise Exception("Unable to mux video and audio on device.")
    except Exception as e:
        # Clean temp files on error
        for t in (temp_vid, temp_aud):
            if os.path.exists(t):
                try: os.remove(t)
                except Exception: pass
        if progress_listener:
            try:
                progress_listener.onError(str(e))
            except Exception:
                pass
        raise e

def _download_playlist(url, download_type, output_dir, progress_listener, selected_indices=None):
    ydl_opts_meta = {
        'quiet': True,
        'extract_flat': True,
        'ignoreerrors': True,
        'socket_timeout': 20,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            raw = ydl.extract_info(url, download=False)
            entries = [e for e in raw.get('entries', []) if e]

        selected_set = set(int(x) for x in selected_indices) if selected_indices else None
        tracks_to_dl = []
        for idx, entry in enumerate(entries, 1):
            if selected_set is None or idx in selected_set:
                tracks_to_dl.append((idx, entry))

        total_tracks = len(tracks_to_dl)
        if total_tracks == 0:
            raise Exception("No items selected for download.")

        downloaded_files = []
        for i, (track_idx, entry) in enumerate(tracks_to_dl):
            vid_id = entry.get('id') or entry.get('url') or ''
            if vid_id and not str(vid_id).startswith('http'):
                track_url = f"https://www.youtube.com/watch?v={vid_id}"
            else:
                track_url = entry.get('webpage_url') or entry.get('url')

            if not track_url:
                continue

            track_title = entry.get('title') or f"Item {track_idx}"
            pct = ((i) / total_tracks) * 100.0
            if progress_listener:
                try:
                    progress_listener.onProgress(float(pct), "", f"Downloading ({i+1}/{total_tracks}): {track_title[:24]}")
                except Exception:
                    pass

            # Download each item 1-by-1 with individual error tolerance
            try:
                out_file = _download_single(track_url, download_type, output_dir, None)
                if out_file and os.path.exists(out_file):
                    downloaded_files.append(out_file)
                    if progress_listener:
                        try:
                            progress_listener.onTrackFinished(out_file)
                        except Exception:
                            pass
            except Exception:
                # Skip unavailable / private / geo-blocked item and continue remaining playlist
                if progress_listener:
                    try:
                        progress_listener.onProgress(float(pct), "", f"Skipped unavailable #{track_idx}: {track_title[:18]}")
                    except Exception:
                        pass
                continue

        if not downloaded_files:
            raise Exception("All selected playlist items were unavailable or protected.")

        if progress_listener:
            try:
                progress_listener.onProgress(100.0, "", f"Saved {len(downloaded_files)} items to library!")
                progress_listener.onCompleted(downloaded_files[0])
            except Exception:
                pass

        return downloaded_files[0]
    except Exception as e:
        if progress_listener:
            try:
                progress_listener.onError(str(e))
            except Exception:
                pass
        raise e
