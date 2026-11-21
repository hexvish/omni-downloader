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
env_max_size = os.environ.get('SERVER_MAX_FILE_SIZE')
MAX_FILE_SIZE = int(env_max_size) if env_max_size else None  # Unlimited on desktop; capped only if SERVER_MAX_FILE_SIZE is set
SERVER_MAX_FILE_SIZE = MAX_FILE_SIZE
MAX_PLAYLIST_ITEMS = int(os.environ.get('SERVER_MAX_PLAYLIST_ITEMS', 50))

AUTO_UPDATE = True
APP_VERSION = "1.0.3"
GITHUB_REPO = "hexvish/omni-downloader"

# Cookie file storage location
if getattr(sys, 'frozen', False):
    app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    COOKIE_DIR = os.path.join(app_data, 'OmniDownloader')
else:
    COOKIE_DIR = os.path.dirname(os.path.abspath(__file__))

COOKIE_FILE = os.path.join(COOKIE_DIR, 'cookies.txt')

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

def update_cookie_opts(cookie_path=None):
    """
    Dynamically configures yt-dlp cookie options and player client.
    When authenticated cookies are provided, yt-dlp can use the standard web client
    to unlock high definition (1080p, 1440p, 4K, 8K) streams.
    """
    global YDL_COMMON_OPTS
    
    target_cookie = cookie_path
    if not target_cookie:
        candidates = [
            COOKIE_FILE,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt'),
            os.path.join(os.path.dirname(sys.executable), 'cookies.txt'),
            os.path.join(BIN_DIR, 'cookies.txt')
        ]
        for c in candidates:
            if os.path.exists(c) and os.path.getsize(c) > 0:
                target_cookie = c
                break

    if target_cookie and os.path.exists(target_cookie) and os.path.getsize(target_cookie) > 0:
        YDL_COMMON_OPTS['cookiefile'] = target_cookie
        # With authenticated cookies, enable full client suite (tv_samsung, web_embedded, web)
        # to unlock high definition (1080p, 1440p, 4K, 8K) streams
        YDL_COMMON_OPTS['extractor_args'] = {
            'youtube': {
                'player_client': ['default', 'tv_samsung', 'web_embedded']
            }
        }
        return target_cookie
    else:
        YDL_COMMON_OPTS.pop('cookiefile', None)
        # Without cookies, android/ios clients bypass botguard restrictions (up to available stream formats)
        YDL_COMMON_OPTS['extractor_args'] = {
            'youtube': {
                'player_client': ['android', 'ios', 'web']
            }
        }
        return None

# Initialize cookie settings
update_cookie_opts()

if FFMPEG_PATH:
    YDL_COMMON_OPTS['ffmpeg_location'] = FFMPEG_PATH

# Cleanup Settings
CLEANUP_INTERVAL = 3600  # 1 hour
FILE_EXPIRY_AGE = 3600    # 1 hour

