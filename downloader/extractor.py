import os
import secrets
import yt_dlp
from config import YDL_COMMON_OPTS, DOWNLOAD_FOLDER

def extract_media_info(url):
    """
    Extract metadata from a URL using yt-dlp.
    """
    ydl_opts = {**YDL_COMMON_OPTS}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # Handle playlists/entries
            if 'entries' in info and not info.get('formats'):
                entries = [e for e in info['entries'] if e]
                if entries:
                    info = entries[0]
            
            return info
        except Exception as e:
            raise Exception(f"yt-dlp extraction failed: {str(e)}")

def download_media(url, format_id, download_type):
    """
    Download media based on selected format and type.
    """
    random_id = secrets.token_hex(4)
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)u__{random_id}.%(ext)s')
    
    ydl_opts = {
        **YDL_COMMON_OPTS,
        'outtmpl': outtmpl,
    }

    if download_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        try:
            height = int(format_id.replace('p', ''))
            fmt_str = f'bestvideo[height<={height}]+bestaudio/best'
        except:
            fmt_str = 'best'
            
        ydl_opts.update({
            'format': fmt_str,
            'noplaylist': True,
            'merge_output_format': 'mp4',
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        if 'entries' in info:
            info = info['entries'][0]

        if download_type == 'audio':
            expected_filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
        else:
            expected_filename = ydl.prepare_filename(info)
            # Handle possible extension changes during merge
            if not os.path.exists(expected_filename):
                base = expected_filename.rsplit('.', 1)[0]
                for ext in ['mp4', 'mkv', 'webm']:
                    if os.path.exists(f"{base}.{ext}"):
                        expected_filename = f"{base}.{ext}"
                        break

        # Final check/Emergency locator
        if not os.path.exists(expected_filename):
            base_pattern = f"__{random_id}."
            for f in os.listdir(DOWNLOAD_FOLDER):
                if base_pattern in f:
                    expected_filename = os.path.join(DOWNLOAD_FOLDER, f)
                    break

        if not os.path.exists(expected_filename):
            raise FileNotFoundError("Could not locate the downloaded file on disk.")

        return os.path.basename(expected_filename)
