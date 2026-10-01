import os
import subprocess
import urllib.request
import json

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
print("--- 1. Port 8765 Check ---")
res = subprocess.run("netstat -ano | findstr :8765", shell=True, capture_output=True, text=True)
print(res.stdout)

print("--- 2. Process Check (python/wscript) ---")
res2 = subprocess.run('powershell -Command "Get-Process -Name python*, wscript* -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Path"', shell=True, capture_output=True, text=True)
print(res2.stdout)

print("--- 3. Local HTTP Ping ---")
try:
    with urllib.request.urlopen("http://127.0.0.1:8765/api/system/release-info", timeout=2) as resp:
        print("HTTP 200 OK:", resp.read().decode()[:200])
except Exception as e:
    print("HTTP FAIL:", e)

print("--- 4. Last 20 lines of server.log ---")
log_path = os.path.join(app_dir, "logs", "server.log")
if os.path.exists(log_path):
    lines = open(log_path, "r", encoding="utf-8", errors="replace").readlines()
    for l in lines[-20:]:
        print(l.rstrip())
