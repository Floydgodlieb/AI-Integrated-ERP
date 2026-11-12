import subprocess
import sys
import os
import signal

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
CHAT_UI_DIR = os.path.join(os.path.dirname(__file__), "chat-UI")
VENV_PYTHON = os.path.join(os.path.dirname(__file__), "..", "..", ".venv", "Scripts", "python.exe")


def main():
    print("Starting Odoo AI Agent V3...")
    print(f"  Backend : {BACKEND_DIR}")
    print(f"  Frontend: {CHAT_UI_DIR}")

    backend = subprocess.Popen(
        [VENV_PYTHON, "-m", "uvicorn", "backend.main:app", "--reload", "--port", "8001"],
        cwd=os.path.dirname(__file__),
    )

    frontend = subprocess.Popen(
        ["npx.cmd", "vite", "--host"],
        cwd=CHAT_UI_DIR,
        shell=True,
    )

    print("\nBackend running at http://localhost:8001")
    print("Frontend running at http://localhost:5173")
    print("API docs at http://localhost:8001/docs")
    print("\nPress Ctrl+C to stop both services.\n")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)


if __name__ == "__main__":
    main()
