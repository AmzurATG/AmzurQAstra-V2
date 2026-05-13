"""
QAstra Silent Launcher
Compiled into QAstra.exe by PyInstaller.

1. Adds backend/ to sys.path so all imports resolve
2. Opens the browser once the server is ready
3. Starts uvicorn in-process (blocking)

NOTE: Database migrations are NOT run automatically.
Run the SQL scripts in backend/alembic/sql/ against your database
before launching QAstra for the first time (or after upgrading).

NOTE: In a frozen PyInstaller exe, sys.executable points to QAstra.exe —
not a Python interpreter — so subprocess-based approaches (sys.executable -m uvicorn)
do not work. Everything must run in-process.
"""
import sys
import os
import time
import webbrowser
import threading
import urllib.request
import traceback


def get_base_path():
    """Code/data root: _MEIPASS when frozen, project root in dev."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(__file__)


def get_exe_dir():
    """Directory where the exe lives (where .env also lives)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def write_error_log(filename, message):
    """Write an error log file next to the exe."""
    try:
        err_path = os.path.join(get_exe_dir(), filename)
        with open(err_path, "w", encoding="utf-8") as f:
            f.write(message)
    except Exception:
        pass


def show_error(title, message):
    """Show a Windows MessageBox for fatal errors."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        print(f"ERROR: {title}\n{message}", file=sys.stderr)


def wait_for_server(url, timeout=60):
    """Poll the server until it responds or times out."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def start_uvicorn_inprocess(backend_dir):
    """Start uvicorn in-process (blocking call)."""
    os.chdir(backend_dir)
    import uvicorn
    # Import the app from backend/main.py
    from main import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    base = get_base_path()
    backend_dir = os.path.join(base, "backend")
    exe_dir = get_exe_dir()

    # Add backend/ to sys.path so imports like "from config import settings" work
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # 1. Open browser once server is ready (in background thread)
    url = "http://127.0.0.1:8000"

    def open_browser():
        if wait_for_server(f"{url}/health"):
            webbrowser.open(url)

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    # 2. Start uvicorn in-process (blocks until server stops)
    try:
        start_uvicorn_inprocess(backend_dir)
    except Exception as e:
        write_error_log("startup_error.log", f"{e}\n\n{traceback.format_exc()}")
        show_error(
            "QAstra \u2014 Server Error",
            f"Failed to start the server.\n\n{e}\n\n"
            "Check startup_error.log next to QAstra.exe for details.",
        )
        sys.exit(1)
