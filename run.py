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
import uvicorn
from core.config import ConfigManager

# Handle headless execution where stdin/stdout/stderr are None
if sys.stdin is None:
    try:
        sys.stdin = open(os.devnull, 'r')
    except Exception:
        pass
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass

if sys.platform.startswith("win"):
    # Fix 100% CPU spinning on Windows headless background event loop
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

    try:
        if sys.stdout:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if sys.stderr:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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

    # 1. Prioritize Samsung Internet if installed
    samsung_path = r"C:\Program Files\Samsung\Internet\Application\samsunginternet.exe"
    if sys.platform.startswith("win") and os.path.exists(samsung_path):
        try:
            subprocess.Popen([samsung_path, url])
            return
        except Exception:
            pass

    # 2. Fallback to system default browser
    try:
        if sys.platform.startswith("win"):
            os.startfile(url)
        else:
            webbrowser.open(url)
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass

def main():
    settings = ConfigManager.get_settings()
    port = settings.get("server_port", 8765)
    host = settings.get("server_host", "0.0.0.0")
    auto_open = settings.get("auto_open_browser", True)

    # 1. If server is already running on this port, just open the dashboard!
    if is_port_in_use(port):
        print("=" * 60)
        print("  백업시스템 매니저 (Backup System Manager)")
        print("=" * 60)
        print(f"[*] 백업 서버가 이미 정상 동작 중입니다 (포트: {port}).")
        print(f"[*] 웹 브라우저에서 대시보드를 열었습니다: http://127.0.0.1:{port}")
        print("=" * 60)
        open_browser(port)
        time.sleep(1.5)
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
        log_level="warning",
        access_log=False,
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    main()
