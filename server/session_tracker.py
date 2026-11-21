"""
Anonymous Session Tracker and Abuse Monitor for Omni Downloader Server.
Provides lightweight session tracking and anomaly flagging using SQLite with WAL mode.
Tracks active sessions in a rolling 7-day window and logs operational review notices.
"""

import os
import time
import json
import secrets
import sqlite3
import threading
from typing import Tuple, Dict, Any, Optional

SESSION_COOKIE_NAME = "omni_sid"
SESSION_DB_FILE = os.environ.get("OMNI_SESSION_DB", os.path.join(os.path.dirname(__file__), "sessions.db"))

# Thresholds per checklist Phase 1
REVIEW_THRESHOLD_SESSIONS_7D = int(os.environ.get("OMNI_REVIEW_THRESHOLD_7D", 5)) # Notice flag if > 5 sessions in 7 days
SESSION_RETENTION_SECONDS = 30 * 86400  # Expire sessions inactive > 30 days
ROLLING_7D_SECONDS = 7 * 86400          # 7 days window
ALERT_THROTTLE_SECONDS = 86400          # Log notice at most once every 24 hours

_db_lock = threading.RLock()
_initialized = False

def _init_db():
    """Initializes SQLite schema and handles migration from legacy sessions.json."""
    global _initialized
    with _db_lock:
        if _initialized:
            return
        os.makedirs(os.path.dirname(os.path.abspath(SESSION_DB_FILE)), exist_ok=True)
        with sqlite3.connect(SESSION_DB_FILE, timeout=15.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    sid TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    ips TEXT NOT NULL,
                    download_count INTEGER NOT NULL DEFAULT 0,
                    request_count INTEGER NOT NULL DEFAULT 1
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_last_seen ON sessions(last_seen);")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    val TEXT
                );
            """)
            conn.commit()

        # Migrate from legacy sessions.json if present
        legacy_json = os.path.join(os.path.dirname(SESSION_DB_FILE), "sessions.json")
        if os.path.exists(legacy_json):
            try:
                with open(legacy_json, "r", encoding="utf-8") as f:
                    legacy_data = json.load(f)
                with sqlite3.connect(SESSION_DB_FILE, timeout=15.0) as conn:
                    for sid, sinfo in legacy_data.items():
                        ips_str = json.dumps(sinfo.get("ips", []))
                        conn.execute("""
                            INSERT OR IGNORE INTO sessions (sid, created_at, last_seen, ips, download_count, request_count)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            sid,
                            sinfo.get("created_at", time.time()),
                            sinfo.get("last_seen", time.time()),
                            ips_str,
                            sinfo.get("download_count", 0),
                            sinfo.get("request_count", 1)
                        ))
                    conn.commit()
                # Rename legacy file to avoid repeated migration
                os.replace(legacy_json, legacy_json + ".migrated")
            except Exception as e:
                print(f">>> [SESSION TRACKER] Notice: Legacy JSON migration skipped: {e}")

        _initialized = True

def _get_connection():
    if not _initialized:
        _init_db()
    conn = sqlite3.connect(SESSION_DB_FILE, timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def get_or_create_session(cookies: dict, client_ip: str = "") -> Tuple[str, bool]:
    """
    Retrieves existing session or generates a new opaque session ID.
    Returns (session_id, is_new_session).
    """
    sid = cookies.get(SESSION_COOKIE_NAME) if cookies else None
    now = time.time()
    is_new = False

    with _db_lock:
        with _get_connection() as conn:
            row = None
            if sid:
                cur = conn.cursor()
                cur.execute("SELECT sid, ips, request_count FROM sessions WHERE sid = ?", (sid,))
                row = cur.fetchone()

            if row:
                existing_sid, ips_json, req_count = row
                try:
                    ips = json.loads(ips_json)
                except Exception:
                    ips = []
                if client_ip and client_ip not in ips:
                    ips.append(client_ip)

                conn.execute(
                    "UPDATE sessions SET last_seen = ?, request_count = ?, ips = ? WHERE sid = ?",
                    (now, req_count + 1, json.dumps(ips), existing_sid)
                )
                sid = existing_sid
            else:
                sid = secrets.token_hex(16)
                is_new = True
                ips = [client_ip] if client_ip else []
                conn.execute(
                    """INSERT INTO sessions (sid, created_at, last_seen, ips, download_count, request_count)
                       VALUES (?, ?, ?, ?, 0, 1)""",
                    (sid, now, now, json.dumps(ips))
                )

            # Evaluate rolling 7-day signals and cleanup expired sessions
            _check_abuse_signals(conn, now)
            _maybe_purge_expired(conn, now)
            conn.commit()

    return sid, is_new

def record_session_download(sid: str):
    """Increments the completed download counter for a session."""
    if not sid:
        return
    with _db_lock:
        with _get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET download_count = download_count + 1 WHERE sid = ?",
                (sid,)
            )
            conn.commit()

def get_active_session_count_7d() -> int:
    """Returns number of unique sessions seen within the rolling 7-day window."""
    now = time.time()
    cutoff = now - ROLLING_7D_SECONDS
    with _db_lock:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sessions WHERE last_seen >= ?", (cutoff,))
            row = cur.fetchone()
            return row[0] if row else 0

def get_session_info(sid: str) -> Optional[Dict[str, Any]]:
    """Returns stored session metrics for a given sid (useful for debugging/testing)."""
    with _db_lock:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT sid, created_at, last_seen, ips, download_count, request_count FROM sessions WHERE sid = ?",
                (sid,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "sid": row[0],
                "created_at": row[1],
                "last_seen": row[2],
                "ips": json.loads(row[3]) if row[3] else [],
                "download_count": row[4],
                "request_count": row[5]
            }

def _check_abuse_signals(conn: sqlite3.Connection, now: float):
    """
    Evaluates rolling 7-day session counts against the review threshold.
    Logs an internal notice if exceeded (at most once every 24 hours).
    Does NOT block or throttle users.
    """
    cutoff = now - ROLLING_7D_SECONDS
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sessions WHERE last_seen >= ?", (cutoff,))
    row = cur.fetchone()
    count_7d = row[0] if row else 0

    if count_7d > REVIEW_THRESHOLD_SESSIONS_7D:
        cur.execute("SELECT val FROM meta WHERE key = 'last_7d_notice_time'")
        meta_row = cur.fetchone()
        last_notice = float(meta_row[0]) if meta_row else 0.0

        if (now - last_notice) >= ALERT_THROTTLE_SECONDS:
            print(f">>> [OPERATIONAL NOTICE] {count_7d} distinct browser sessions active in the last 7 days (Review threshold: {REVIEW_THRESHOLD_SESSIONS_7D}).")
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, val) VALUES ('last_7d_notice_time', ?)",
                (str(now),)
            )

def _maybe_purge_expired(conn: sqlite3.Connection, now: float):
    """Purges sessions inactive for > 30 days if last purge was > 6 hours ago."""
    cur = conn.cursor()
    cur.execute("SELECT val FROM meta WHERE key = 'last_purge_time'")
    meta_row = cur.fetchone()
    last_purge = float(meta_row[0]) if meta_row else 0.0

    if (now - last_purge) >= 21600: # 6 hours
        cutoff = now - SESSION_RETENTION_SECONDS
        conn.execute("DELETE FROM sessions WHERE last_seen < ?", (cutoff,))
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, val) VALUES ('last_purge_time', ?)",
            (str(now),)
        )
