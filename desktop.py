import os
import sys
import time
import socket
import threading
import webview
from app import app
from downloader.engine import init_engine

def find_free_port():
    """Finds an unused local port to run the embedded server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def run_server(port):
    """Runs the Flask application in a quiet, embedded server mode."""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)

def main():
    # 1. Initialize engine (FFmpeg check and yt-dlp auto-update)
    init_engine()

    # 2. Start Flask in background thread
    port = find_free_port()
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # 3. Wait briefly for server to bind
    time.sleep(0.6)

    # 4. Launch Desktop Window
    window = webview.create_window(
        title='Omni Downloader',
        url=f'http://127.0.0.1:{port}',
        width=880,
        height=860,
        min_size=(700, 600),
        background_color='#090d16'
    )
    webview.start()
    sys.exit(0)

if __name__ == '__main__':
    main()
