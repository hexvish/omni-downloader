import os
import sys
import time
import socket
import threading
import traceback
import webbrowser
from app import app
from downloader.engine import init_engine

def get_appdata_dir():
    """Returns persistent application directory for logs and state."""
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    app_dir = os.path.join(local_appdata, 'OmniDownloader')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def log_message(msg):
    """Appends diagnostic message to persistent crash.log."""
    try:
        log_file = os.path.join(get_appdata_dir(), 'crash.log')
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass

def show_error_dialog(title, message):
    """Displays a native Windows error dialog if available."""
    try:
        import ctypes
        MB_ICONERROR = 0x10
        MB_SETFOREGROUND = 0x10000
        ctypes.windll.user32.MessageBoxW(0, str(message), str(title), MB_ICONERROR | MB_SETFOREGROUND)
    except Exception:
        print(f"[ERROR] {title}: {message}", file=sys.stderr)

def setup_crash_logger():
    """Catches any uncaught exceptions and logs them persistently."""
    def excepthook(exc_type, exc_value, exc_traceback):
        err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log_message(f"UNHANDLED EXCEPTION:\n{err}")
        log_path = os.path.join(get_appdata_dir(), 'crash.log')
        show_error_dialog(
            "Omni Downloader - Critical Error",
            f"An unexpected error occurred:\n\n{exc_value}\n\nDiagnostic log saved to:\n{log_path}"
        )
    sys.excepthook = excepthook

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
    setup_crash_logger()
    log_message("Starting Omni Downloader desktop process...")

    # 1. Initialize engine (FFmpeg check and yt-dlp auto-update)
    try:
        init_engine()
    except Exception as e:
        log_message(f"Engine initialization warning: {e}")

    # 2. Start Flask in background thread
    port = find_free_port()
    log_message(f"Starting embedded server on port {port}...")
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # 3. Wait briefly for server to bind
    time.sleep(0.6)
    target_url = f'http://127.0.0.1:{port}'

    # 4. Resolve application icon
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon_candidates = [
        os.path.join(base_dir, 'app.ico'),
        os.path.join(base_dir, 'static', 'img', 'app.ico'),
        os.path.join(os.path.dirname(sys.executable), 'app.ico')
    ]
    icon_path = next((p for p in icon_candidates if os.path.exists(p)), None)

    # 5. Launch Desktop Window with automatic browser fallback
    gui_started = False
    try:
        import webview
        log_message("Attempting to initialize native pywebview window...")
        window = webview.create_window(
            title='Omni Downloader',
            url=target_url,
            width=920,
            height=880,
            min_size=(720, 600),
            background_color='#090d16'
        )
        gui_started = True
        webview.start(icon=icon_path)
        log_message("Desktop window closed cleanly.")
        sys.exit(0)
    except Exception as gui_err:
        log_message(f"Native WebView2 GUI failed ({gui_err}). Falling back to system default web browser.")
        try:
            webbrowser.open(target_url)
            log_message(f"Opened default web browser at {target_url}.")
            # Keep Flask server running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as browser_err:
            log_message(f"Failed to open web browser: {browser_err}")
            show_error_dialog("Omni Downloader", f"Could not launch browser:\n{browser_err}")
            sys.exit(1)

if __name__ == '__main__':
    main()
