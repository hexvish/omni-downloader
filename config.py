import os
import shutil

# Application Settings
DOWNLOAD_FOLDER = os.path.abspath('downloads')
SOCKET_TIMEOUT = 20
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
AUTO_UPDATE = True

# Discover FFmpeg path
FFMPEG_PATH = shutil.which('ffmpeg')
if not FFMPEG_PATH:
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_PATH = None

if FFMPEG_PATH:
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    current_path = os.environ.get('PATH', '')
    if ffmpeg_dir not in current_path:
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + current_path

# yt-dlp Options
YDL_COMMON_OPTS = {
    'restrictfilenames': True,
    'socket_timeout': SOCKET_TIMEOUT,
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

if FFMPEG_PATH:
    YDL_COMMON_OPTS['ffmpeg_location'] = FFMPEG_PATH

# Cleanup Settings
CLEANUP_INTERVAL = 3600  # 1 hour
FILE_EXPIRY_AGE = 3600    # 1 hour

