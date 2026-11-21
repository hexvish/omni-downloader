"""
Transfer-Safe Cleanup and Disk Headroom Monitor for Omni Downloader Server.
Ensures active downloads, conversions, and client streams are NEVER deleted prematurely.
"""

import os
import time
import shutil
import threading
from typing import Tuple, Set, Dict

# Configurable retention periods
COMPLETED_FILE_EXPIRY_SECONDS = int(os.environ.get("OMNI_FILE_EXPIRY", 7200)) # 2 hours default
ABANDONED_TEMP_EXPIRY_SECONDS = int(os.environ.get("OMNI_TEMP_EXPIRY", 7200)) # 2 hours default
CLEANUP_CHECK_INTERVAL = int(os.environ.get("OMNI_CLEANUP_INTERVAL", 900))    # 15 minutes default
MINIMUM_FREE_DISK_BYTES = 10 * 1024 * 1024 * 1024                             # 10 GB minimum reserve

# Thread-safe in-flight transfer registry
_active_transfers: Dict[str, int] = {}
_transfers_lock = threading.Lock()

class TransferGuard:
    """Context manager to mark a file as actively transferring to a client."""
    def __init__(self, filepath_or_name: str):
        self.filename = os.path.basename(filepath_or_name)

    def __enter__(self):
        with _transfers_lock:
            _active_transfers[self.filename] = _active_transfers.get(self.filename, 0) + 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with _transfers_lock:
            if self.filename in _active_transfers:
                _active_transfers[self.filename] -= 1
                if _active_transfers[self.filename] <= 0:
                    del _active_transfers[self.filename]

def is_file_transferring(filepath_or_name: str) -> bool:
    """Returns True if the file is currently being read/streamed by a client."""
    base = os.path.basename(filepath_or_name)
    with _transfers_lock:
        return _active_transfers.get(base, 0) > 0

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
    except Exception:
        return True, "" # If disk usage check fails, do not block

def run_cleanup_pass(download_dir: str, get_active_task_identifiers_func) -> int:
    """
    Executes a single cleanup pass over download_dir.
    Returns the number of purged items.
    """
    if not os.path.exists(download_dir):
        return 0

    now = time.time()
    purged_count = 0
    active_identifiers: Set[str] = set()

    try:
        active_identifiers = set(get_active_task_identifiers_func())
    except Exception as e:
        print(f">>> [SAFE CLEANUP] Warning retrieving active task identifiers: {e}")

    for fname in os.listdir(download_dir):
        if fname in ('.gitkeep', '.gitignore'):
            continue

        fpath = os.path.join(download_dir, fname)

        # 1. Protect files currently being streamed to a client
        if is_file_transferring(fname):
            continue

        # 2. Protect files associated with any active task
        # Check exact filename match
        if fname in active_identifiers:
            continue

        # Check if an active identifier (e.g. random_id or playlist folder) is inside fname
        is_active = False
        for ident in active_identifiers:
            if ident and ident in fname:
                is_active = True
                break
        if is_active:
            continue

        try:
            # Use modification timestamp (mtime) for cross-platform age calculation
            stat = os.stat(fpath)
            last_activity = stat.st_mtime
            age = now - last_activity

            # Check for partial/temporary files (.part, .ytdl, .temp, or leading __)
            is_partial = fname.startswith("__") or any(fname.endswith(ext) for ext in ('.part', '.ytdl', '.temp'))

            if is_partial:
                if age > ABANDONED_TEMP_EXPIRY_SECONDS:
                    if os.path.isfile(fpath) or os.path.islink(fpath):
                        os.remove(fpath)
                        purged_count += 1
                        print(f">>> [SAFE CLEANUP] Removed abandoned partial file: {fname}")
                continue

            # Completed files or playlist directories
            if age > COMPLETED_FILE_EXPIRY_SECONDS:
                if os.path.isfile(fpath) or os.path.islink(fpath):
                    os.remove(fpath)
                    purged_count += 1
                    print(f">>> [SAFE CLEANUP] Purged expired download: {fname}")
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath, ignore_errors=True)
                    purged_count += 1
                    print(f">>> [SAFE CLEANUP] Purged expired directory: {fname}")

        except Exception as item_err:
            # Skip if locked or inaccessible
            pass

    return purged_count

def safe_cleanup_worker(download_dir: str, get_active_task_identifiers_func):
    """
    Periodically checks download directory and safely cleans expired files.
    Daemon worker running in the background.
    """
    print(f">>> [SAFE CLEANUP] Worker active for {download_dir}. Retention: {COMPLETED_FILE_EXPIRY_SECONDS}s")
    while True:
        try:
            run_cleanup_pass(download_dir, get_active_task_identifiers_func)
        except Exception as loop_err:
            print(f">>> [SAFE CLEANUP] Error in cleanup loop: {loop_err}")

        time.sleep(CLEANUP_CHECK_INTERVAL)

def start_safe_cleanup(download_dir: str, get_active_task_identifiers_func):
    """Starts the safe cleanup daemon thread."""
    worker = threading.Thread(
        target=safe_cleanup_worker,
        args=(download_dir, get_active_task_identifiers_func),
        daemon=True
    )
    worker.start()
