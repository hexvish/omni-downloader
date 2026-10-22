import os
import sys
import shutil
import subprocess
import threading
import urllib.request
import zipfile
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bin_dir():
    """Returns the path to the bin directory, ensuring it exists."""
    if getattr(sys, 'frozen', False):
        # When running as compiled executable
        base_dir = os.path.dirname(sys.executable)
        bin_dir = os.path.join(base_dir, 'bin')
        # If application folder is read-only (e.g. Program Files), fallback to LocalAppData
        try:
            os.makedirs(bin_dir, exist_ok=True)
            test_file = os.path.join(bin_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('1')
            os.remove(test_file)
            return bin_dir
        except Exception:
            local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            bin_dir = os.path.join(local_appdata, 'OmniDownloader', 'bin')
            os.makedirs(bin_dir, exist_ok=True)
            return bin_dir
    else:
        # Development / source code mode
        bin_dir = os.path.join(PROJECT_ROOT, 'bin')
        os.makedirs(bin_dir, exist_ok=True)
        return bin_dir

BIN_DIR = get_bin_dir()

# Global thread-safe engine status
engine_lock = threading.Lock()
engine_state = {
    'ffmpeg_ready': False,
    'ffmpeg_path': None,
    'ffmpeg_progress': 0,
    'ffmpeg_status': 'Checking...',
    'ytdlp_ready': True,
    'ytdlp_updating': False,
    'ytdlp_version': '',
    'ytdlp_path': None
}

def detect_ffmpeg():
    """Detects if ffmpeg is available locally or on system PATH."""
    bin_ffmpeg = os.path.join(BIN_DIR, 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    if os.path.exists(bin_ffmpeg) and os.path.getsize(bin_ffmpeg) > 0:
        return bin_ffmpeg

    # System PATH
    sys_ffmpeg = shutil.which('ffmpeg')
    if sys_ffmpeg:
        return sys_ffmpeg

    # imageio-ffmpeg fallback
    try:
        import imageio_ffmpeg
        img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if img_ffmpeg and os.path.exists(img_ffmpeg):
            # Copy to bin_dir for self-contained consistency
            try:
                shutil.copy2(img_ffmpeg, bin_ffmpeg)
                return bin_ffmpeg
            except Exception:
                return img_ffmpeg
    except Exception:
        pass

    return None

def detect_ytdlp():
    """Detects standalone yt-dlp binary or package."""
    bin_ytdlp = os.path.join(BIN_DIR, 'yt-dlp.exe' if os.name == 'nt' else 'yt-dlp')
    if os.path.exists(bin_ytdlp) and os.path.getsize(bin_ytdlp) > 0:
        return bin_ytdlp
    sys_ytdlp = shutil.which('yt-dlp')
    if sys_ytdlp:
        return sys_ytdlp
    return None

def init_engine():
    """Initializes and checks binaries on app startup."""
    ffmpeg_path = detect_ffmpeg()
    ytdlp_path = detect_ytdlp()

    # Get yt-dlp version
    version_str = ''
    try:
        import yt_dlp
        version_str = getattr(yt_dlp, '__version__', '')
    except Exception:
        pass

    with engine_lock:
        engine_state['ffmpeg_path'] = ffmpeg_path
        engine_state['ffmpeg_ready'] = bool(ffmpeg_path)
        engine_state['ffmpeg_status'] = 'Ready' if ffmpeg_path else 'Missing'
        engine_state['ffmpeg_progress'] = 100 if ffmpeg_path else 0
        engine_state['ytdlp_path'] = ytdlp_path
        engine_state['ytdlp_version'] = version_str

    # Trigger background updates and auto-installation
    if not ffmpeg_path:
        threading.Thread(target=_download_ffmpeg_worker, daemon=True).start()

    threading.Thread(target=_update_ytdlp_worker, daemon=True).start()

def _download_ffmpeg_worker():
    """Background worker to download FFmpeg if completely missing."""
    with engine_lock:
        engine_state['ffmpeg_status'] = 'Downloading audio/video engine...'
        engine_state['ffmpeg_progress'] = 5

    bin_ffmpeg = os.path.join(BIN_DIR, 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    zip_dest = os.path.join(BIN_DIR, 'ffmpeg_download.zip')

    # Try imageio_ffmpeg first if available
    try:
        import imageio_ffmpeg
        img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if img_ffmpeg and os.path.exists(img_ffmpeg):
            shutil.copy2(img_ffmpeg, bin_ffmpeg)
            with engine_lock:
                engine_state['ffmpeg_ready'] = True
                engine_state['ffmpeg_path'] = bin_ffmpeg
                engine_state['ffmpeg_progress'] = 100
                engine_state['ffmpeg_status'] = 'Ready'
            return
    except Exception:
        pass

    # Reliable static build download URL for Windows
    url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    try:
        def reporthook(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(95, int((block_num * block_size / total_size) * 90) + 5)
                with engine_lock:
                    engine_state['ffmpeg_progress'] = pct

        urllib.request.urlretrieve(url, zip_dest, reporthook=reporthook)

        with engine_lock:
            engine_state['ffmpeg_status'] = 'Extracting FFmpeg engine...'
            engine_state['ffmpeg_progress'] = 96

        with zipfile.ZipFile(zip_dest, 'r') as zf:
            for member in zf.namelist():
                if member.endswith('ffmpeg.exe'):
                    with zf.open(member) as source, open(bin_ffmpeg, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    break

        if os.path.exists(zip_dest):
            try:
                os.remove(zip_dest)
            except Exception:
                pass

        if os.path.exists(bin_ffmpeg):
            with engine_lock:
                engine_state['ffmpeg_ready'] = True
                engine_state['ffmpeg_path'] = bin_ffmpeg
                engine_state['ffmpeg_progress'] = 100
                engine_state['ffmpeg_status'] = 'Ready'
    except Exception as e:
        print(f">>> FFmpeg download error: {e}")
        with engine_lock:
            engine_state['ffmpeg_status'] = f"Download failed: {str(e)}"

def _update_ytdlp_worker():
    """Background worker to update yt-dlp on app launch."""
    with engine_lock:
        engine_state['ytdlp_updating'] = True

    bin_ytdlp = os.path.join(BIN_DIR, 'yt-dlp.exe')
    if os.path.exists(bin_ytdlp):
        try:
            print(">>> Running background yt-dlp binary self-update (yt-dlp -U)...")
            subprocess.run([bin_ytdlp, '-U'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
        except Exception as e:
            print(f">>> yt-dlp binary self-update error: {e}")
    else:
        # Download standalone yt-dlp binary for standalone builds if not present
        ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        try:
            print(">>> Downloading latest standalone yt-dlp.exe...")
            urllib.request.urlretrieve(ytdlp_url, bin_ytdlp)
        except Exception as e:
            print(f">>> yt-dlp download note: {e}")

    with engine_lock:
        engine_state['ytdlp_updating'] = False
        engine_state['ytdlp_path'] = detect_ytdlp()

def get_engine_status():
    """Returns a snapshot of the current engine state."""
    with engine_lock:
        return dict(engine_state)
