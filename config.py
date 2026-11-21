import os
import sys
import shutil

# Application Settings
env_download_dir = os.environ.get('DOWNLOAD_DIR')
if env_download_dir:
    DOWNLOAD_FOLDER = os.path.abspath(env_download_dir)
elif getattr(sys, 'frozen', False):
    # Default to user's Downloads/OmniDownloader directory to avoid permission issues
    DOWNLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'Downloads', 'OmniDownloader')
else:
    DOWNLOAD_FOLDER = os.path.abspath('downloads')

SOCKET_TIMEOUT = 20
MAX_FILE_SIZE = int(os.environ.get('SERVER_MAX_FILE_SIZE', 500 * 1024 * 1024))  # 500MB default
SERVER_MAX_FILE_SIZE = MAX_FILE_SIZE
MAX_PLAYLIST_ITEMS = int(os.environ.get('SERVER_MAX_PLAYLIST_ITEMS', 15))

AUTO_UPDATE = True
APP_VERSION = "1.0.3"
GITHUB_REPO = "hexvish/omni-downloader"

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
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'web']
        }
    }
}

# Optional cookie file support if cookies.txt is provided
cookie_candidates = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt'),
    os.path.join(BIN_DIR, 'cookies.txt')
]
for cp in cookie_candidates:
    if os.path.exists(cp) and os.path.getsize(cp) > 0:
        YDL_COMMON_OPTS['cookiefile'] = cp
        break

if FFMPEG_PATH:
    YDL_COMMON_OPTS['ffmpeg_location'] = FFMPEG_PATH

# Cleanup Settings
CLEANUP_INTERVAL = 3600  # 1 hour
FILE_EXPIRY_AGE = 3600    # 1 hour

