"""Start the V3 backend (port 8001) and chat UI (port 5173) together. Stop both with Ctrl+C.

Works on Windows, macOS and Linux. Uses the virtual environment in <repo>/.venv if it exists,
otherwise the Python that runs this script.

The chat UI is only reachable from this computer. To open it from other devices on your network
(e.g. a phone for a demo), set UI_ON_NETWORK=1 first - the app has no login, so only do that
on a network you trust.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(HERE, "backend")
CHAT_UI_DIR = os.path.join(HERE, "chat-UI")
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
IS_WINDOWS = os.name == "nt"

VENV_PYTHON = (os.path.join(REPO_ROOT, ".venv", "Scripts", "python.exe") if IS_WINDOWS
               else os.path.join(REPO_ROOT, ".venv", "bin", "python"))
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable


def main():
    on_network = os.getenv("UI_ON_NETWORK") == "1"
    print("Starting Odoo AI Agent V3...")
    print(f"  Python  : {PYTHON}")
    print(f"  Backend : {BACKEND_DIR}")
    print(f"  Frontend: {CHAT_UI_DIR}")

    backend = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "backend.main:app", "--reload", "--port", "8001"],
        cwd=HERE,
    )

    vite = ["npx.cmd" if IS_WINDOWS else "npx", "vite"] + (["--host"] if on_network else [])
    frontend = subprocess.Popen(vite, cwd=CHAT_UI_DIR, shell=IS_WINDOWS)

    print("\nBackend running at http://localhost:8001")
    print("Frontend running at http://localhost:5173" + ("  (ALSO open to your network!)" if on_network else ""))
    print("API docs at http://localhost:8001/docs")
    print("\nPress Ctrl+C to stop both services.\n")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        for proc in (backend, frontend):
            if proc.poll() is None:
                proc.terminate()
        sys.exit(0)


if __name__ == "__main__":
    main()
