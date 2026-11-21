"""
Sliding-Window Rate Limiter for Omni Downloader Server.
Applies configurable rate limits to expensive operations (extraction, download initiation).
"""

import time
import threading
from typing import Tuple, Dict, List

_rate_lock = threading.Lock()
_request_records: Dict[str, List[float]] = {}

# Default endpoint limits (requests per window)
LIMIT_FETCH_FORMATS = 15      # 15 format extractions per minute per session
LIMIT_START_DOWNLOAD = 5      # 5 download starts per minute per session
RATE_WINDOW_SECONDS = 60      # 1 minute sliding window

def is_rate_limited(key: str, action: str, limit: int = None, window_seconds: int = RATE_WINDOW_SECONDS) -> Tuple[bool, int]:
    """
    Checks if an action from an identifier (e.g. session_id or client IP) is rate-limited.
    Returns (is_limited, retry_after_seconds).
    """
    if limit is None:
        if action == "fetch_formats":
            limit = LIMIT_FETCH_FORMATS
        elif action == "start_download":
            limit = LIMIT_START_DOWNLOAD
        else:
            limit = 30

    now = time.time()
    lookup_key = f"{action}:{key}"

    with _rate_lock:
        timestamps = _request_records.get(lookup_key, [])
        
        # Prune expired timestamps
        cutoff = now - window_seconds
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= limit:
            oldest_relevant = valid_timestamps[0]
            retry_after = max(1, int(oldest_relevant + window_seconds - now))
            _request_records[lookup_key] = valid_timestamps
            return True, retry_after

        # Record this request
        valid_timestamps.append(now)
        _request_records[lookup_key] = valid_timestamps
        return False, 0

def clear_rate_limits():
    """Clears all stored rate limits (useful for testing)."""
    with _rate_lock:
        _request_records.clear()
