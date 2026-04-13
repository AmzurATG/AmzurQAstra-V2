"""
QAstra Silent Launcher
Compiled into QAstra.exe by PyInstaller.

1. Runs Alembic migrations against the configured database
2. Starts FastAPI (uvicorn) as a hidden background process
3. Waits for the /health endpoint to respond
4. Opens the default browser to http://127.0.0.1:8000
"""
import subprocess
import sys
import os
import time
import webbrowser
import threading
import urllib.request


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


def run_migrations(backend_dir, env):
    """Run Alembic migrations before starting the server."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            err_path = os.path.join(get_exe_dir(), "migration_error.log")
            with open(err_path, "w") as f:
                f.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n")
            return False
        return True
    except Exception as e:
        err_path = os.path.join(get_exe_dir(), "migration_error.log")
        with open(err_path, "w") as f:
            f.write(f"Migration exception: {e}\n")
        return False


def start_backend(backend_dir, env):
    """Start uvicorn as a hidden subprocess."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return proc


if __name__ == "__main__":
    base = get_base_path()
    backend_dir = os.path.join(base, "backend")
    exe_dir = get_exe_dir()

    # Build environment — config.py reads .env from this location when frozen
    env = os.environ.copy()
    env["ENV_FILE_PATH"] = os.path.join(exe_dir, ".env")

    # 1. Run database migrations
    if not run_migrations(backend_dir, env):
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "Database migration failed.\n\n"
            "Check migration_error.log next to QAstra.exe for details.\n"
            "Verify your DATABASE_URL in .env is correct and the database is running.",
            "QAstra \u2014 Startup Error",
            0x10,  # MB_ICONERROR
        )
        sys.exit(1)

    # 2. Start FastAPI server
    proc = start_backend(backend_dir, env)
    url = "http://127.0.0.1:8000"

    # 3. Open browser once server is ready
    def open_browser():
        if wait_for_server(f"{url}/health"):
            webbrowser.open(url)

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
