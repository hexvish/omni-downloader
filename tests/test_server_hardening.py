"""
Automated Test Suite for Omni Downloader Server Hardening.
Tests SSRF validation, rate limiting, session tracking, cleanup safety,
and download size limit enforcement.
"""

import os
import sys
import time
import shutil
import tempfile
import unittest
import threading
import sqlite3

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import yt_dlp
from server.security import is_safe_url
from server.rate_limiter import is_rate_limited, clear_rate_limits
from server.cleanup_daemon import (
    TransferGuard,
    is_file_transferring,
    run_cleanup_pass
)
import server.session_tracker as session_tracker
from server.app import app


class TestSSRFSecurity(unittest.TestCase):
    """Verifies that SSRF attack vectors are blocked and legitimate URLs pass."""

    def test_safe_public_urls_allowed(self):
        safe_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://instagram.com/reel/Cx123",
            "https://twitter.com/user/status/12345",
            "http://example.com/video.mp4"
        ]
        for url in safe_urls:
            is_safe, msg = is_safe_url(url)
            self.assertTrue(is_safe, f"Expected safe URL to pass: {url}. Msg: {msg}")

    def test_localhost_and_loopback_blocked(self):
        blocked_urls = [
            "http://localhost/secret",
            "http://127.0.0.1:8000/admin",
            "http://127.0.0.1/",
            "http://127.1/",
            "http://[::1]/internal"
        ]
        for url in blocked_urls:
            is_safe, msg = is_safe_url(url)
            self.assertFalse(is_safe, f"Expected localhost to be blocked: {url}")

    def test_cloud_metadata_ip_blocked(self):
        # Critical for Oracle Cloud & AWS (169.254.169.254)
        metadata_urls = [
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.169.254/opc/v1/instance/",
            "https://169.254.169.254/"
        ]
        for url in metadata_urls:
            is_safe, msg = is_safe_url(url)
            self.assertFalse(is_safe, f"Expected metadata IP to be blocked: {url}")

    def test_private_rfc1918_ips_blocked(self):
        private_urls = [
            "http://10.0.0.1/status",
            "http://172.16.0.5/api",
            "http://192.168.1.1/router"
        ]
        for url in private_urls:
            is_safe, msg = is_safe_url(url)
            self.assertFalse(is_safe, f"Expected private IP to be blocked: {url}")

    def test_embedded_credentials_blocked(self):
        credential_urls = [
            "http://admin:secret@youtube.com/watch?v=123",
            "https://user:pass@example.com/video"
        ]
        for url in credential_urls:
            is_safe, msg = is_safe_url(url)
            self.assertFalse(is_safe, f"Expected credential URL to be blocked: {url}")

    def test_custom_ports_blocked(self):
        port_urls = [
            "http://example.com:8080/test",
            "http://youtube.com:22/",
            "https://example.com:8443/video"
        ]
        for url in port_urls:
            is_safe, msg = is_safe_url(url)
            self.assertFalse(is_safe, f"Expected custom port URL to be blocked: {url}")

    def test_bad_schemes_and_malformed_blocked(self):
        bad_urls = [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "gopher://example.com",
            "",
            "not a url"
        ]
        for url in bad_urls:
            is_safe, msg = is_safe_url(url)
            self.assertFalse(is_safe, f"Expected bad scheme/malformed to be blocked: {url}")


class TestRateLimiter(unittest.TestCase):
    """Verifies sliding-window rate limiting on critical endpoints."""

    def setUp(self):
        clear_rate_limits()

    def test_rate_limiter_allows_up_to_limit(self):
        key = "session_user_1"
        limit = 5

        # 5 requests should pass
        for i in range(limit):
            is_limited, retry_after = is_rate_limited(key, "fetch_formats", limit=limit, window_seconds=60)
            self.assertFalse(is_limited, f"Request {i+1} should not be limited")
            self.assertEqual(retry_after, 0)

        # 6th request must be limited
        is_limited, retry_after = is_rate_limited(key, "fetch_formats", limit=limit, window_seconds=60)
        self.assertTrue(is_limited, "6th request should be rate-limited")
        self.assertGreater(retry_after, 0)

    def test_rate_limiter_distinct_keys_independent(self):
        limit = 3
        key_a = "user_alpha"
        key_b = "user_beta"

        # Max out user_alpha
        for _ in range(limit):
            is_rate_limited(key_a, "start_download", limit=limit, window_seconds=60)

        is_limited_a, _ = is_rate_limited(key_a, "start_download", limit=limit, window_seconds=60)
        self.assertTrue(is_limited_a)

        # user_beta should still be allowed
        is_limited_b, retry_b = is_rate_limited(key_b, "start_download", limit=limit, window_seconds=60)
        self.assertFalse(is_limited_b)
        self.assertEqual(retry_b, 0)


class TestSessionTracker(unittest.TestCase):
    """Verifies anonymous session generation, 7-day rolling window, and SQLite concurrency."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_sessions.db")
        # Point session tracker to temporary DB
        session_tracker.SESSION_DB_FILE = self.db_path
        session_tracker._initialized = False

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_session_creation_and_persistence(self):
        # 1. New visit without cookies
        sid1, is_new = session_tracker.get_or_create_session({}, client_ip="203.0.113.1")
        self.assertTrue(is_new)
        self.assertTrue(len(sid1) >= 16)

        # 2. Subsequent visit with same cookie
        sid2, is_new2 = session_tracker.get_or_create_session({session_tracker.SESSION_COOKIE_NAME: sid1})
        self.assertFalse(is_new2)
        self.assertEqual(sid1, sid2)

        # Verify recorded metrics
        info = session_tracker.get_session_info(sid1)
        self.assertIsNotNone(info)
        self.assertEqual(info["request_count"], 2)
        self.assertEqual(info["ips"], ["203.0.113.1"])

    def test_download_counter_increment(self):
        sid, _ = session_tracker.get_or_create_session({})
        session_tracker.record_session_download(sid)
        session_tracker.record_session_download(sid)

        info = session_tracker.get_session_info(sid)
        self.assertEqual(info["download_count"], 2)

    def test_rolling_7d_window_calculation(self):
        now = time.time()
        conn = session_tracker._get_connection()
        with conn:
            # Session active 1 day ago (within 7d)
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, 0, 1)",
                ("s_1d", now - 86400, now - 86400, "[]")
            )
            # Session active 6 days ago (within 7d)
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, 0, 1)",
                ("s_6d", now - 6 * 86400, now - 6 * 86400, "[]")
            )
            # Session active 8 days ago (OUTSIDE 7d)
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, 0, 1)",
                ("s_8d", now - 8 * 86400, now - 8 * 86400, "[]")
            )

        active_count = session_tracker.get_active_session_count_7d()
        self.assertEqual(active_count, 2, "Expected exactly 2 sessions active within 7 days")

    def test_multithreaded_sqlite_concurrency(self):
        errors = []

        def worker_task(thread_id):
            try:
                for i in range(10):
                    sid, _ = session_tracker.get_or_create_session({}, client_ip=f"10.0.0.{thread_id}")
                    session_tracker.record_session_download(sid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent session operations failed: {errors}")


class TestCleanupDaemon(unittest.TestCase):
    """Verifies that cleanup protects active files, transfers, and unexpired files."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_transfer_guard_protects_file(self):
        target_file = os.path.join(self.test_dir, "streaming_video.mp4")
        with open(target_file, "w") as f:
            f.write("content")

        self.assertFalse(is_file_transferring("streaming_video.mp4"))
        with TransferGuard("streaming_video.mp4"):
            self.assertTrue(is_file_transferring("streaming_video.mp4"))
        self.assertFalse(is_file_transferring("streaming_video.mp4"))

    def test_cleanup_preserves_active_and_removes_expired(self):
        now = time.time()

        # 1. Active task file (should NOT be removed)
        active_file = os.path.join(self.test_dir, "__active123.mp4.part")
        with open(active_file, "w") as f:
            f.write("active partial")
        # Set old timestamp
        os.utime(active_file, (now - 10000, now - 10000))

        # 2. Abandoned partial file (SHOULD be removed)
        abandoned_file = os.path.join(self.test_dir, "__abandoned456.mp4.part")
        with open(abandoned_file, "w") as f:
            f.write("abandoned partial")
        os.utime(abandoned_file, (now - 10000, now - 10000))

        # 3. Expired completed file (SHOULD be removed)
        expired_file = os.path.join(self.test_dir, "old_completed.mp4")
        with open(expired_file, "w") as f:
            f.write("old completed")
        os.utime(expired_file, (now - 10000, now - 10000))

        # 4. Fresh completed file (should NOT be removed)
        fresh_file = os.path.join(self.test_dir, "fresh_download.mp4")
        with open(fresh_file, "w") as f:
            f.write("fresh")
        # Timestamp is right now

        # Active identifiers return "active123"
        get_active = lambda: {"active123"}

        purged = run_cleanup_pass(self.test_dir, get_active)

        self.assertTrue(os.path.exists(active_file), "Active file must not be purged")
        self.assertTrue(os.path.exists(fresh_file), "Fresh file must not be purged")
        self.assertFalse(os.path.exists(abandoned_file), "Abandoned partial file must be purged")
        self.assertFalse(os.path.exists(expired_file), "Expired completed file must be purged")
        self.assertEqual(purged, 2)


class TestSizeLimitEnforcement(unittest.TestCase):
    """Verifies that the progress hook aborts downloads when size exceeds limit."""

    def test_progress_hook_raises_download_cancelled_on_oversized(self):
        from downloader.extractor import check_size_limit

        max_limit = 100 * 1024 * 1024 # 100 MB limit

        # 1. Normal size chunk (50 MB) - should NOT raise
        d_normal = {
            'status': 'downloading',
            'downloaded_bytes': 50 * 1024 * 1024,
            'total_bytes': 80 * 1024 * 1024,
            'filename': 'temp.mp4'
        }
        try:
            check_size_limit(d_normal, max_limit)
        except yt_dlp.utils.DownloadCancelled:
            self.fail("check_size_limit raised DownloadCancelled on file under max limit")

        # 2. Oversized total_bytes chunk (150 MB) - MUST raise DownloadCancelled
        d_oversized = {
            'status': 'downloading',
            'downloaded_bytes': 10 * 1024 * 1024,
            'total_bytes': 150 * 1024 * 1024,
            'filename': 'temp.mp4'
        }
        with self.assertRaises(yt_dlp.utils.DownloadCancelled):
            check_size_limit(d_oversized, max_limit)

        # 3. Oversized downloaded_bytes chunk (120 MB downloaded) - MUST raise
        d_oversized_dl = {
            'status': 'downloading',
            'downloaded_bytes': 120 * 1024 * 1024,
            'filename': 'temp.mp4'
        }
        with self.assertRaises(yt_dlp.utils.DownloadCancelled):
            check_size_limit(d_oversized_dl, max_limit)


class TestServerEndpoints(unittest.TestCase):
    """Verifies HTTP responses, headers, and security on Flask endpoints."""

    def setUp(self):
        self.client = app.test_client()

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_session_cookie_assigned(self):
        response = self.client.get("/")
        self.assertIn("omni_sid", response.headers.get("Set-Cookie", ""))

    def test_engine_status_api(self):
        response = self.client.get("/api/engine/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("ffmpeg_ready", data)

    def test_fetch_formats_rejects_ssrf(self):
        response = self.client.post("/fetch_formats", data={"url": "http://127.0.0.1:8000/steal"})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["status"], "error")

    def test_get_file_blocks_path_traversal(self):
        response = self.client.get("/get-file/../../etc/passwd")
        # Should return 404 (file not found) or 400/403, NOT internal server error or contents
        self.assertIn(response.status_code, (403, 404))


if __name__ == "__main__":
    unittest.main()
