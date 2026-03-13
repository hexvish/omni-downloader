import os

# Application Settings
DOWNLOAD_FOLDER = os.path.abspath('downloads')
SOCKET_TIMEOUT = 15
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB example limit (not strictly enforced by ytdlp here)
AUTO_UPDATE = True

# yt-dlp Options
YDL_COMMON_OPTS = {
    'restrictfilenames': True,
    'socket_timeout': SOCKET_TIMEOUT,
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Cleanup Settings
CLEANUP_INTERVAL = 3600  # 1 hour
FILE_EXPIRY_AGE = 3600    # 1 hour
