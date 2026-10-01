import os
import subprocess
import time
import urllib.request
import json

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"

# 1. Kill old processes on port 8765
ps_kill = (
    "$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue\n"
    "if ($conn) {\n"
    "    foreach ($c in $conn) {\n"
    "        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue\n"
    "        if ($p) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }\n"
    "    }\n"
    "}\n"
)
subprocess.run(["powershell", "-NoProfile", "-Command", ps_kill], capture_output=True)
time.sleep(2)

# 2. Launch cleanly via start_silent.vbs
vbs_path = os.path.join(app_dir, "start_silent.vbs")
subprocess.Popen(["wscript.exe", vbs_path], cwd=app_dir)
time.sleep(4)

# 3. Test release-info
for _ in range(10):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/system/release-info", timeout=2) as resp:
            data = json.loads(resp.read().decode())
            print("RESTARTED_RELEASE_INFO:", data)
            break
    except Exception as e:
        time.sleep(1)
