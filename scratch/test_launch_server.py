import os
import subprocess
import time
import urllib.request
import json

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
vbs_path = os.path.join(app_dir, "start_silent.vbs")

# Launch via VBScript
subprocess.Popen(["wscript.exe", vbs_path], cwd=app_dir)
time.sleep(3)

# Test local status endpoint
try:
    with urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print("API_STATUS_OK:", data.get("version"), data.get("status"))
except Exception as e:
    print("API_ERR:", e)
