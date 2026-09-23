import os
import sys
import time
import socket
import asyncio
import webbrowser
import threading
import subprocess
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Handle headless execution where stdio might be None (Critical for pythonw.exe)
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
try:
    os.makedirs(_log_dir, exist_ok=True)
    _server_log = open(os.path.join(_log_dir, "server.log"), "a", encoding="utf-8", buffering=1)
except Exception:
    _server_log = None

if sys.stdin is None:
    try:
        sys.stdin = open(os.devnull, 'r')
    except Exception:
        pass
if _server_log:
    sys.stdout = _server_log
    sys.stderr = _server_log

def ensure_dependencies():
    required = ["uvicorn", "fastapi", "cryptography", "psutil", "jinja2", "requests", "pydantic", "zstandard"]
    missing = []
    for mod in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    
    if missing:
        req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
        if os.path.exists(req_file):
            print(f"[*] 필수 패키지({', '.join(missing)})가 누락되어 자동으로 설치합니다...")
            try:
                cmd = [sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"]
                # Add --break-system-packages if running under uv / PEP 668 managed python
                try:
                    subprocess.check_call(cmd + ["--break-system-packages"])
                except Exception:
                    subprocess.check_call(cmd)
            except Exception as e:
                print(f"[!] 필수 패키지 자동 설치 경고 (계속 진행 시도): {e}")

ensure_dependencies()
import uvicorn
from core.config import ConfigManager

def is_port_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False

def open_browser(port: int):
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        if is_port_in_use(port):
            break
        time.sleep(0.1)

    # 1. Open via Windows native ShellExecute (Strictly respects Windows Default Browser)
    try:
        if sys.platform.startswith("win"):
            os.startfile(url)
            return
    except Exception:
        pass

    # 2. Safe fallback to standard webbrowser library
    try:
        webbrowser.open(url)
    except Exception:
        pass

def main():
    settings = ConfigManager.get_settings()
    port = settings.get("server_port", 8765)
    host = settings.get("server_host", "0.0.0.0")
    auto_open = settings.get("auto_open_browser", True)

    # 1. If server is already running on this port, simply open default browser and return!
    if is_port_in_use(port):
        open_browser(port)
        return

    # 2. Start server and open browser
    print("=" * 60)
    print("  백업 매니저 시스템 (Backup System Manager)")
    print("=" * 60)
    print(f"[*] 백업 서버를 시작합니다 (포트: {port})...")
    print(f"[*] 접속 주소: http://127.0.0.1:{port}")
    print("=" * 60)

    if auto_open:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    config = uvicorn.Config(
        "web.app:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

def show_error_dialog(title: str, message: str):
    try:
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10 | 0x10000)
    except Exception:
        pass

def log_startup_error(err_str: str):
    try:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "startup_error.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {err_str}\n")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        log_startup_error(err_msg)
        show_error_dialog("백업시스템 시작 오류", f"백업시스템 기동 중 오류가 발생했습니다:\n\n{e}\n\n자세한 내용은 logs/startup_error.log를 확인하세요.")
        sys.exit(1)
