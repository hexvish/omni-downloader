"""
Anonymous Session Tracker and Abuse Monitor for Omni Downloader Server.
Provides lightweight session tracking and anomaly flagging without requiring user logins.
"""

import os
import time
import json
import secrets
import threading
from typing import Tuple, Dict, Any

SESSION_COOKIE_NAME = "omni_sid"
SESSION_DATA_FILE = os.environ.get("OMNI_SESSION_FILE", os.path.join(os.path.dirname(__file__), "sessions.json"))
SESSION_LOCK = threading.Lock()

# Thresholds per checklist Phase 1
REVIEW_THRESHOLD_SESSIONS_7D = 5       # Review flag if > 5 distinct sessions in 7 days
SESSION_RETENTION_SECONDS = 30 * 86400  # Expire sessions inactive > 30 days
ROLLING_7D_SECONDS = 7 * 86400          # 7 days window

def get_or_create_session(cookies: dict, client_ip: str) -> Tuple[str, bool]:
    """
    Retrieves existing session or generates a new opaque session ID.
    Returns (session_id, is_new_session).
    """
    sid = cookies.get(SESSION_COOKIE_NAME)
    now = time.time()

    with SESSION_LOCK:
        sessions = _load_sessions()

        is_new = False
        if not sid or sid not in sessions:
            sid = secrets.token_hex(16)
            is_new = True
            sessions[sid] = {
                "created_at": now,
                "last_seen": now,
                "ips": [client_ip] if client_ip else [],
                "download_count": 0,
                "request_count": 1
            }
        else:
            session_data = sessions[sid]
            session_data["last_seen"] = now
            session_data["request_count"] = session_data.get("request_count", 0) + 1
            if client_ip and client_ip not in session_data.get("ips", []):
                session_data["ips"].append(client_ip)

        _check_abuse_signals(sessions, now)
        _save_sessions(sessions)
        return sid, is_new

def record_session_download(sid: str):
    """Increments the completed download counter for a session."""
    with SESSION_LOCK:
        sessions = _load_sessions()
        if sid in sessions:
            sessions[sid]["download_count"] = sessions[sid].get("download_count", 0) + 1
            _save_sessions(sessions)

def _check_abuse_signals(sessions: Dict[str, Any], now: float):
    """
    Evaluates rolling 7-day session counts against the review threshold.
    Logs an internal notice if exceeded (does NOT block users).
    """
    active_in_7d = [
        s for s in sessions.values()
        if (now - s.get("created_at", 0)) <= ROLLING_7D_SECONDS
    ]
    if len(active_in_7d) > REVIEW_THRESHOLD_SESSIONS_7D:
        print(f">>> [OPERATIONAL NOTICE] {len(active_in_7d)} distinct browser sessions observed in the last 7 days (Review threshold: {REVIEW_THRESHOLD_SESSIONS_7D}).")

def _load_sessions() -> Dict[str, Any]:
    now = time.time()
    if os.path.exists(SESSION_DATA_FILE):
        try:
            with open(SESSION_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Purge expired sessions
                return {k: v for k, v in data.items() if (now - v.get("last_seen", 0)) < SESSION_RETENTION_SECONDS}
        except Exception:
            return {}
    return {}

def _save_sessions(sessions: Dict[str, Any]):
    try:
        temp_file = SESSION_DATA_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)
        os.replace(temp_file, SESSION_DATA_FILE)
    except Exception as e:
        print(f">>> Failed to write session data: {e}")
