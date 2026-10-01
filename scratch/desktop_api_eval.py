# -*- coding: utf-8 -*-
import urllib.request, json, time, sys, os, socket, subprocess

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0

# Self-Start if server not listening
if not is_port_open(8765):
    app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
    py_exe = os.path.join(app_dir, "python", "pythonw.exe")
    if not os.path.exists(py_exe):
        py_exe = "pythonw.exe"
    subprocess.Popen([py_exe, "run.py", "--silent"], cwd=app_dir)
    for _ in range(30):
        if is_port_open(8765):
            break
        time.sleep(0.5)

# 1. Version Check
try:
    with urllib.request.urlopen("http://127.0.0.1:8765/api/system/release-info", timeout=5) as resp:
        d = json.loads(resp.read().decode('utf-8'))
        print("VER:" + d.get("data", {}).get("version", "UNKNOWN"))
except Exception as e:
    print("VER_ERR:" + str(e))

# 2. Snapshot API Check (HTTP 200 & Schema)
try:
    with urllib.request.urlopen("http://127.0.0.1:8765/api/snapshots", timeout=10) as resp:
        raw = resp.read().decode('utf-8')
        snaps = json.loads(raw)
        print("SNAP_COUNT:" + str(len(snaps)))
        print("SNAP_STATUS:" + str(resp.status))
except Exception as e:
    print("SNAP_ERR:" + str(e))

# 3. Cache Hit Latency (5 iterations)
lats = []
for _ in range(5):
    t0 = time.perf_counter()
    with urllib.request.urlopen("http://127.0.0.1:8765/api/snapshots", timeout=5) as resp:
        resp.read()
    lats.append((time.perf_counter() - t0) * 1000)
    time.sleep(0.02)

print("AVG_LAT:" + f"{sum(lats)/len(lats):.2f}")
print("MIN_LAT:" + f"{min(lats):.2f}")
print("MAX_LAT:" + f"{max(lats):.2f}")
