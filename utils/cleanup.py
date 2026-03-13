import os
import time
import threading
from config import DOWNLOAD_FOLDER, CLEANUP_INTERVAL, FILE_EXPIRY_AGE

def cleanup_loop():
    """
    Background thread to periodically clean up expired files in the downloads folder.
    """
    print(f">>> Background cleanup thread started. Interval: {CLEANUP_INTERVAL}s")
    while True:
        try:
            now = time.time()
            if os.path.exists(DOWNLOAD_FOLDER):
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if f == '.gitkeep':
                        continue
                        
                    file_path = os.path.join(DOWNLOAD_FOLDER, f)
                    if os.path.isfile(file_path):
                        creation_time = os.path.getctime(file_path)
                        if (now - creation_time) > FILE_EXPIRY_AGE:
                            os.remove(file_path)
                            print(f">>> Cleaned up expired file: {f}")
        except Exception as e:
            print(f">>> Cleanup error: {e}")
            
        time.sleep(CLEANUP_INTERVAL)

def start_cleanup_worker():
    """
    Starts the cleanup loop in a background daemon thread.
    """
    worker = threading.Thread(target=cleanup_loop, daemon=True)
    worker.start()
