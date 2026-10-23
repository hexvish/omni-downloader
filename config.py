import os
import sys
import shutil

# Application Settings
if getattr(sys, 'frozen', False):
    # Default to user's Downloads/OmniDownloader directory to avoid permission issues
    DOWNLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'Downloads', 'OmniDownloader')
else:
    DOWNLOAD_FOLDER = os.path.abspath('downloads')

SOCKET_TIMEOUT = 20
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
AUTO_UPDATE = True

# Discover bin directory
if getattr(sys, 'frozen', False):
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    candidate = os.path.join(base_dir, 'bin')
    if os.path.exists(candidate):
        BIN_DIR = candidate
    else:
        exe_bin = os.path.join(os.path.dirname(sys.executable), 'bin')
        BIN_DIR = exe_bin if os.path.exists(exe_bin) else candidate
else:
    BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')

# Discover FFmpeg path
bin_ffmpeg = os.path.join(BIN_DIR, 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
FFMPEG_PATH = None
if os.path.exists(bin_ffmpeg) and os.path.getsize(bin_ffmpeg) > 0:
    FFMPEG_PATH = bin_ffmpeg
elif shutil.which('ffmpeg'):
    FFMPEG_PATH = shutil.which('ffmpeg')
else:
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

