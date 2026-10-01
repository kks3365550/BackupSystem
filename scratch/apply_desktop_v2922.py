import os
import zipfile
import subprocess
import time
import shutil

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
zip_path = r"C:\Users\kksjmj\AppData\Local\Temp\release_v2.9.22.zip"

print("[*] 1. Stopping existing server on port 8765...")
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

print("[*] 2. Extracting release_v2.9.22.zip to staging...")
staging = r"C:\Users\kksjmj\AppData\Local\Temp\staging_v2922"
if os.path.exists(staging):
    shutil.rmtree(staging, ignore_errors=True)
os.makedirs(staging, exist_ok=True)

with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(staging)

print("[*] 3. Applying files to app directory...")
# Robocopy from staging to app_dir, preserving data/ and keys/
cmd = f'robocopy "{staging}" "{app_dir}" /E /NP /R:3 /W:1 /XF profiles.json auth_config.json app_settings.json metadata.db'
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(f"Robocopy return code: {res.returncode}")

shutil.rmtree(staging, ignore_errors=True)

# 4. Verify VERSION
ver_file = os.path.join(app_dir, "VERSION")
v = open(ver_file, "r", encoding="utf-8").read().strip()
print(f"[+] Post-update VERSION on desktop: {v}")
assert v == "2.9.22", f"Expected 2.9.22, got {v}"
print("[SUCCESS] Desktop updated to v2.9.22!")
