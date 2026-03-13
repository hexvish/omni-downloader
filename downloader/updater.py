import subprocess
import sys
from config import AUTO_UPDATE

def check_for_updates():
    if not AUTO_UPDATE:
        print(">>> yt-dlp auto-update is disabled.")
        return

    print(">>> yt-dlp update check started...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
        print(">>> yt-dlp is up to date.")
    except Exception as e:
        print(f">>> Failed to update yt-dlp: {e}")
