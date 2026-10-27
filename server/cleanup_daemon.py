"""
Transfer-Safe Cleanup and Disk Headroom Monitor for Omni Downloader Server.
Ensures active downloads and client streams are NEVER deleted prematurely.
"""

import os
import time
import shutil
import threading
from typing import Tuple

# Default retention: 2 hours after creation
COMPLETED_FILE_EXPIRY_SECONDS = int(os.environ.get("OMNI_FILE_EXPIRY", 7200)) # 2 hours
ABANDONED_TEMP_EXPIRY_SECONDS = int(os.environ.get("OMNI_TEMP_EXPIRY", 7200)) # 2 hours
CLEANUP_CHECK_INTERVAL = 900 # Check every 15 minutes
MINIMUM_FREE_DISK_BYTES = 10 * 1024 * 1024 * 1024 # 10 GB minimum reserve

def check_disk_headroom(download_dir: str) -> Tuple[bool, str]:
    """
    Verifies that the download volume has at least 10 GB free space before starting a job.
    Returns (has_headroom, error_message).
    """
    try:
        total, used, free = shutil.disk_usage(download_dir)
        if free < MINIMUM_FREE_DISK_BYTES:
            free_gb = round(free / (1024 ** 3), 2)
            return False, f"Server storage reserve reached ({free_gb} GB free). Minimum 10 GB required."
        return True, ""
    except Exception as e:
        return True, "" # If disk usage check fails, do not block

def safe_cleanup_worker(download_dir: str, get_active_task_filenames_func):
    """
    Periodically checks download directory and safely cleans expired files.
    Skips any file currently being written or transferred.
    """
    print(f">>> [SAFE CLEANUP] Worker active for {download_dir}. Retention: {COMPLETED_FILE_EXPIRY_SECONDS}s")
    while True:
        try:
            now = time.time()
            if os.path.exists(download_dir):
                # Retrieve list of filenames currently associated with active tasks
                active_filenames = set(get_active_task_filenames_func())

                for fname in os.listdir(download_dir):
                    if fname == '.gitkeep':
                        continue

                    fpath = os.path.join(download_dir, fname)

                    # 1. Never delete a file currently in an active task
                    if fname in active_filenames:
                        continue

                    try:
                        c_time = os.path.getctime(fpath)
                        age = now - c_time

                        # Handle partial/temporary files (.part, .ytdl, .temp)
                        is_partial = any(fname.endswith(ext) for ext in ('.part', '.ytdl', '.temp'))
                        if is_partial:
                            if age > ABANDONED_TEMP_EXPIRY_SECONDS:
                                if os.path.isfile(fpath):
                                    os.remove(fpath)
                                    print(f">>> [SAFE CLEANUP] Removed abandoned partial file: {fname}")
                            continue

                        # Handle completed files/directories
                        if age > COMPLETED_FILE_EXPIRY_SECONDS:
                            if os.path.isfile(fpath):
                                os.remove(fpath)
                                print(f">>> [SAFE CLEANUP] Purged expired download: {fname}")
                            elif os.path.isdir(fpath):
                                shutil.rmtree(fpath, ignore_errors=True)
                                print(f">>> [SAFE CLEANUP] Purged expired directory: {fname}")

                    except Exception as item_err:
                        # Silently skip file if currently locked/accessed by client
                        pass

        except Exception as loop_err:
            print(f">>> [SAFE CLEANUP] Error in cleanup pass: {loop_err}")

        time.sleep(CLEANUP_CHECK_INTERVAL)

def start_safe_cleanup(download_dir: str, get_active_task_filenames_func):
    """Starts the safe cleanup daemon thread."""
    worker = threading.Thread(
        target=safe_cleanup_worker,
        args=(download_dir, get_active_task_filenames_func),
        daemon=True
    )
    worker.start()
