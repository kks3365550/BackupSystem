import psutil

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = " ".join(p.info['cmdline'] or [])
        if "tabby" in cmd.lower() or "tabby" in p.info['name'].lower():
            print(f"PID: {p.info['pid']}, Name: {p.info['name']}, Cmd: {cmd[:100]}")
    except Exception:
        pass
