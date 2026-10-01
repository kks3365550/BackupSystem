# -*- coding: utf-8 -*-
import os, sys, zipfile, time, subprocess, urllib.request, json

TARGET_DIR = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
ZIP_PATH = r"C:\Users\kksjmj\AppData\Local\Temp\release_v2.10.0.zip"

# Kill existing processes
subprocess.run("taskkill /f /im pythonw.exe 2>nul", shell=True)
time.sleep(2)

# Extract preserving configs
skip_files = {"profiles.json", "auth_config.json", "app_settings.json", "metadata.db"}
with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    for member in zf.infolist():
        target_path = os.path.join(TARGET_DIR, member.filename)
        base_name = os.path.basename(member.filename)
        if base_name in skip_files and os.path.exists(target_path):
            continue
        zf.extract(member, TARGET_DIR)

v_file = os.path.join(TARGET_DIR, "VERSION")
with open(v_file, "r", encoding="utf-8") as f:
    ver = f.read().strip()
print(f"DEPLOYED_VER:{ver}")

# Launch server cleanly
py_exe = os.path.join(TARGET_DIR, "python", "pythonw.exe")
if not os.path.exists(py_exe):
    py_exe = "pythonw.exe"

ps_cmd = f'''
$proc = Start-Process -FilePath "{py_exe}" -ArgumentList "run.py", "--silent" -WorkingDirectory "{TARGET_DIR}" -WindowStyle Hidden -PassThru;
Write-Output $proc.Id
'''
res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
print(f"SPAWNED_PID:{res.stdout.strip()}")

# Wait for 127.0.0.1:8765 ready
ready = False
url = "http://127.0.0.1:8765/api/snapshots"
for _ in range(40):
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            if resp.status == 200:
                ready = True
                break
    except Exception:
        time.sleep(0.5)

print(f"SERVER_READY:{ready}")
