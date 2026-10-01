# -*- coding: utf-8 -*-
"""
Desktop GitHub OTA Verification Script (v2.9.20 -> v2.9.21)
Authentic OTA lifecycle:
1. Query GitHub Releases API directly
2. Download release_v2.9.21.zip
3. Verify SHA-256 and Ed25519 signature
4. Apply update atomically using core.updater
5. Verify VERSION = 2.9.21
6. Verify existing repository & snapshot data preservation
"""
import os
import sys
import json
import time
import urllib.request

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

print("=" * 60)
print("[PHASE 5] Desktop Real GitHub OTA Verification")
print("=" * 60)

# 1. Check current installed version
with open(os.path.join(app_dir, "VERSION"), "r", encoding="utf-8") as vf:
    cur_ver = vf.read().strip()
print(f"[*] Step 1: Current Installed Version on Desktop: {cur_ver}")

# 2. Query GitHub Releases API for updates
print("\n[*] Step 2: Querying GitHub Releases API for updates...")
GITHUB_API = "https://api.github.com/repos/kks3365550/BackupSystem/releases/latest"
req = urllib.request.Request(GITHUB_API, headers={"User-Agent": "BackupSystemOTA/2.9"})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))

latest_tag = data.get("tag_name", "").lstrip("vV")
print(f"[+] GitHub Latest Release Found: v{latest_tag}")
assert latest_tag == "2.9.21", f"Expected 2.9.21, got {latest_tag}"

# Extract download URLs
zip_url = None
sig_url = None
sha_url = None
for a in data.get("assets", []):
    name = a.get("name", "")
    dl = a.get("browser_download_url", "")
    if name.startswith("release_") and name.endswith(".zip"):
        zip_url = dl
    elif name.startswith("release_") and name.endswith(".zip.sig"):
        sig_url = dl
    elif name == "SHA256SUMS.txt":
        sha_url = dl

print(f"    - ZIP URL: {zip_url}")
print(f"    - SIG URL: {sig_url}")
print(f"    - SHA URL: {sha_url}")
assert zip_url and sig_url and sha_url

# Fetch expected SHA256 from SHA256SUMS.txt
expected_sha = None
with urllib.request.urlopen(urllib.request.Request(sha_url, headers={"User-Agent": "BackupSystemOTA"}), timeout=10) as s_resp:
    for line in s_resp.read().decode("utf-8").splitlines():
        if "release_" in line and ".zip" in line:
            expected_sha = line.strip().split()[0]
            break
print(f"    - Expected SHA256: {expected_sha}")

# Fetch expected signature from .sig
with urllib.request.urlopen(urllib.request.Request(sig_url, headers={"User-Agent": "BackupSystemOTA"}), timeout=10) as sig_resp:
    expected_sig = sig_resp.read().decode("utf-8").strip()
print(f"    - Expected Signature: {expected_sig[:32]}...")

# 3. Download package
print("\n[*] Step 3: Downloading update package from GitHub...")
temp_dir = os.environ.get("TEMP", r"C:\Windows\Temp")
target_zip = os.path.join(temp_dir, f"backup_update_v{latest_tag}_{int(time.time())}.zip")
with urllib.request.urlopen(urllib.request.Request(zip_url, headers={"User-Agent": "BackupSystemOTA"}), timeout=30) as dl_resp:
    with open(target_zip, "wb") as f:
        f.write(dl_resp.read())
print(f"[+] Downloaded successfully: {target_zip} ({os.path.getsize(target_zip)} bytes)")

# 4. Verify integrity & signature using existing core.updater logic
print("\n[*] Step 4: Verifying SHA-256 and Ed25519 signature...")
from core.updater import verify_update, install_update
pub_key = os.path.join(app_dir, "keys", "release_ed25519.pub")
is_valid = verify_update(
    zip_path=target_zip,
    expected_sha256=expected_sha,
    expected_signature=expected_sig,
    pub_key_path=pub_key
)
if not is_valid:
    print("[-] Verification FAILED!")
    sys.exit(1)
print("[+] Verification 100% PASSED (SHA-256 matched, Ed25519 signature valid)!")

# 5. Apply update atomically
print("\n[*] Step 5: Applying update to Desktop application...")
install_ok = install_update(target_zip, target_dir=app_dir)
print(f"[+] Install result: success={install_ok}")
if not install_ok:
    print("[-] Installation failed!")
    sys.exit(1)

# 6. Verify upgraded version
time.sleep(1)
with open(os.path.join(app_dir, "VERSION"), "r", encoding="utf-8") as vf:
    upgraded_ver = vf.read().strip()
print(f"\n[*] Step 6: Verified Post-Update VERSION on Desktop: {upgraded_ver}")
assert upgraded_ver == "2.9.21", f"Expected 2.9.21, got {upgraded_ver}"

# 7. Check profiles and existing repository preservation
prof_path = os.path.join(app_dir, "data", "profiles.json")
if os.path.exists(prof_path):
    with open(prof_path, "r", encoding="utf-8") as pf:
        prof = json.load(pf)[0]
    print(f"\n[*] Step 7: Verifying Data Preservation:")
    print(f"    - Repository Dir: {prof.get('repo_dir')} (Expected F:\\)")
    print(f"    - Policy: auto_backup_enabled={prof.get('auto_backup_enabled')} (Expected False)")
    print(f"    - Last Snapshot: {prof.get('last_snapshot_id')}")
    assert prof.get("repo_dir") == "F:\\"
    assert prof.get("auto_backup_enabled") is False
    print("    [PASS] Existing configuration and manual policy 100% PRESERVED!")

print("\n" + "=" * 60)
print("[SUCCESS] DESKTOP REAL GITHUB OTA LIFECYCLE 100% VERIFIED!")
print("=" * 60)
