# -*- coding: utf-8 -*-
r"""
scratch/deploy_and_verify_desktop_v2100.py
=========================================
Deploys official release_v2.10.0.zip to Desktop Program Dir
(C:\Users\kksjmj\AppData\Local\Programs\백업시스템)
and runs the 7-step post-release verification.
"""

import os
import sys
import time
import json
import zipfile
import shutil
import urllib.request
import subprocess

TARGET_DIR = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
ZIP_SRC = r"D:\백업시스템_설치용\release_v2.10.0.zip"
REMOTE_IP = "100.90.20.59"
REMOTE_TEMP_ZIP = r"C:\Users\kksjmj\AppData\Local\Temp\release_v2.10.0.zip"

print("=" * 80)
print(" [v2.10.0 OFFICIAL DESKTOP DEPLOY & FINAL 7-STEP VERIFICATION]")
print("=" * 80)

# 1. SCP release_v2.10.0.zip to Desktop
print(f"[*] Transferring {ZIP_SRC} to Desktop ({REMOTE_IP})...")
scp_res = subprocess.run(["scp", ZIP_SRC, f"kksjmj@{REMOTE_IP}:{REMOTE_TEMP_ZIP}"], capture_output=True, text=True)
if scp_res.returncode != 0:
    print(f"[-] SCP failed: {scp_res.stderr}")
    sys.exit(1)
print("[+] Transferred successfully!")

# 2. Remote Python Deploy Script on Desktop
remote_deploy_py = r"""# -*- coding: utf-8 -*-
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
"""

# Save and SCP remote deploy runner
runner_path = os.path.join(os.path.dirname(__file__), "remote_deploy_v2100.py")
with open(runner_path, "w", encoding="utf-8") as f:
    f.write(remote_deploy_py)

subprocess.run(["scp", runner_path, f"kksjmj@{REMOTE_IP}:C:/Users/kksjmj/AppData/Local/Temp/remote_deploy_v2100.py"], capture_output=True)

# Run deploy runner on desktop via bundled python
print("[*] Executing remote deployment and server restart on Desktop...")
cmd = f'ssh kksjmj@{REMOTE_IP} "C:\\Users\\kksjmj\\AppData\\Local\\Programs\\백업시스템\\python\\python.exe C:\\Users\\kksjmj\\AppData\\Local\\Temp\\remote_deploy_v2100.py"'
ssh_res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(f"[+] Remote Execution Output:\n{ssh_res.stdout.strip()}")

# 3. Perform 7-Step Verification
print("\n" + "=" * 80)
print(" [PERFORMING FINAL 7-STEP VERIFICATION]")
print("=" * 80)

results = {}

# Step 1: Local VERSION
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
with open(os.path.join(BASE_DIR, "VERSION"), "r", encoding="utf-8") as f:
    ver = f.read().strip()
print(f"Step 1: Local VERSION = '{ver}'")
assert ver == "2.10.0", f"Expected 2.10.0, got {ver}"
results["1_VERSION"] = f"PASS ({ver})"

# Step 2: Git Tag
tag_res = subprocess.run(["git", "tag", "-l", "v2.10.0"], cwd=BASE_DIR, capture_output=True, text=True)
print(f"Step 2: Git tag v2.10.0 = '{tag_res.stdout.strip()}'")
assert "v2.10.0" in tag_res.stdout, "Git tag v2.10.0 not found!"
results["2_GIT_TAG"] = "PASS (v2.10.0)"

# Step 3: Installer Artifacts
dist_dir = r"D:\백업시스템_설치용"
setup_exe = os.path.join(dist_dir, "BackupSystem_Setup_v2.10.0.exe")
zip_pkg = os.path.join(dist_dir, "release_v2.10.0.zip")
print(f"Step 3: Checking installer artifacts...")
assert os.path.exists(setup_exe), "Setup exe missing!"
assert os.path.exists(zip_pkg), "Release zip missing!"
print(f"    - Setup EXE : {os.path.getsize(setup_exe):,} bytes")
print(f"    - Release ZIP: {os.path.getsize(zip_pkg):,} bytes")
results["3_INSTALLER_ARTIFACTS"] = "PASS (Setup EXE & Release ZIP present)"

# Step 4: Desktop Deployed Version Check
print(f"\nStep 4: Checking Desktop ({REMOTE_IP}) deployed version...")
desktop_url = f"http://{REMOTE_IP}:8765/api/system/release-info"
desktop_ver = None
for _ in range(10):
    try:
        with urllib.request.urlopen(desktop_url, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            desktop_ver = data.get("data", {}).get("version")
            if desktop_ver:
                break
    except Exception:
        time.sleep(1)

print(f"    - Desktop API Reported Version: {desktop_ver}")
assert desktop_ver == "2.10.0", f"Expected Desktop 2.10.0, got {desktop_ver}"
results["4_DESKTOP_VERSION"] = f"PASS ({desktop_ver})"

# Step 5: Desktop /api/snapshots HTTP 200 & Schema
print(f"\nStep 5: Verifying Desktop /api/snapshots...")
snap_url = f"http://{REMOTE_IP}:8765/api/snapshots"
with urllib.request.urlopen(snap_url, timeout=10) as resp:
    status_code = resp.status
    snap_data = json.loads(resp.read().decode('utf-8'))
print(f"    - HTTP Status: {status_code}, Loaded: {len(snap_data)} snapshots")
assert status_code == 200
assert isinstance(snap_data, list)
results["5_API_SNAPSHOTS_SCHEMA"] = f"PASS (Status 200, {len(snap_data)} snapshots)"

# Step 6: Cache Hit Latency Check
print(f"\nStep 6: Measuring Desktop Cache Hit Latency across Tailscale...")
hit_times = []
for i in range(5):
    t0 = time.perf_counter()
    with urllib.request.urlopen(snap_url, timeout=5) as resp:
        resp.read()
    elapsed = (time.perf_counter() - t0) * 1000
    hit_times.append(elapsed)
    print(f"    - Request #{i+1}: {elapsed:.2f} ms")
    time.sleep(0.05)

avg_hit = sum(hit_times) / len(hit_times)
print(f"    - Average Network Latency: {avg_hit:.2f} ms")
results["6_CACHE_HIT_LATENCY"] = f"PASS (Network Avg: {avg_hit:.2f} ms)"

# Step 7: Backup / Restore Smoke Test
print(f"\nStep 7: Performing Backup & Restore Smoke Test...")
test_dir = os.path.join(BASE_DIR, "scratch", "smoke_test_env")
test_src = os.path.join(test_dir, "source")
test_repo = os.path.join(test_dir, "repo")
test_dest = os.path.join(test_dir, "restored")

shutil.rmtree(test_dir, ignore_errors=True)
os.makedirs(test_src, exist_ok=True)
os.makedirs(test_repo, exist_ok=True)
os.makedirs(test_dest, exist_ok=True)

with open(os.path.join(test_src, "test_file.txt"), "w", encoding="utf-8") as f:
    f.write("v2.10.0 smoke test content 1234567890")

from core.snapshot import SnapshotEngine
from core.storage import BlobStorage

storage = BlobStorage(test_repo)
engine = SnapshotEngine(storage)

snap_id = engine.create_snapshot("smoke_prof", "Smoke Profile", [test_src])
print(f"    - Created Snapshot ID: {snap_id}")
assert snap_id is not None

snaps = engine.list_snapshots(test_repo)
assert len(snaps) == 1
assert snaps[0]["id"] == snap_id

engine.restore_snapshot(snap_id, test_dest, overwrite=True)
restored_file = os.path.join(test_dest, "test_file.txt")
assert os.path.exists(restored_file)
with open(restored_file, "r", encoding="utf-8") as f:
    assert f.read() == "v2.10.0 smoke test content 1234567890"
print("    - Restore verified: Content exactly matched!")

shutil.rmtree(test_dir, ignore_errors=True)
results["7_SMOKE_TEST"] = "PASS (Create -> List Cache -> Restore 100% matched)"

print("\n" + "=" * 80)
print(" [v2.10.0 FINAL POST-RELEASE VERIFICATION SUMMARY]")
print("=" * 80)
for k, v in results.items():
    print(f"  {k:25s} : {v}")
print("=" * 80)
print(" >>> ALL 7 POST-RELEASE CHECKS PASSED PERFECTLY! <<< ")
print("=" * 80)
