import os
import sys
import time
import asyncio
import webbrowser
import threading
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

def open_browser(port: int):
    import socket
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.08):
                break
        except OSError:
            time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    try:
        webbrowser.open(url)
    except Exception:
        pass

def main():
    settings = ConfigManager.get_settings()
    port = settings.get("server_port", 8765)
    host = settings.get("server_host", "127.0.0.1")
    auto_open = settings.get("auto_open_browser", True)

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
