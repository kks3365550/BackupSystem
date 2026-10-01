# -*- coding: utf-8 -*-
import os
import subprocess
import urllib.request
import re

print("==================================================")
print("  Git 상태 & 릴리즈 산출물 4대 정합성 감사")
print("==================================================")

# 1. VERSION file in repo
with open("VERSION", "r", encoding="utf-8") as f:
    ver_repo = f.read().strip()
print(f"1. Repo VERSION:              {ver_repo}")

# 2. VERSION in D:\백업시스템_설치용
install_ver_path = r"D:\백업시스템_설치용\VERSION"
if os.path.exists(install_ver_path):
    with open(install_ver_path, "r", encoding="utf-8") as f:
        ver_install = f.read().strip()
    print(f"2. D:\\백업시스템_설치용 VERSION:    {ver_install}")
else:
    ver_install = "NOT FOUND"
    print("2. D:\\백업시스템_설치용 VERSION:    NOT FOUND")

# 3. Live Server UI header version
try:
    html = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=3).read().decode("utf-8")
    m = re.search(r'v(\d+\.\d+\.\d+)', html)
    ver_ui = m.group(1) if m else "NOT FOUND"
    print(f"3. Live Dashboard UI Version: {ver_ui}")
except Exception as e:
    ver_ui = f"ERROR: {e}"
    print(f"3. Live Dashboard UI Version: {ver_ui}")

# 4. Git Tag check
try:
    tags = subprocess.check_output(["git", "tag", "-l", "v2.10.1"], text=True).strip()
    print(f"4. Git Tag v2.10.1:           {tags if tags else 'MISSING'}")
except Exception as e:
    tags = f"ERROR: {e}"
    print(f"4. Git Tag:                   {tags}")

# 5. Git Status Clean check
try:
    status = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    modified = [l for l in status.splitlines() if not ("??" in l and "scratch/" in l)]
    status_str = "CLEAN (0 uncommitted changes)" if not modified else f"DIRTY ({len(modified)} files)"
    print(f"5. Git Tracked Status:        {status_str}")
except Exception as e:
    print(f"5. Git Status:                ERROR: {e}")

assert ver_repo == "2.10.1", "Repo version is not 2.10.1!"
assert ver_install == "2.10.1", "Install folder version mismatch!"
assert ver_ui == "2.10.1", "Live UI header version mismatch!"
assert tags == "v2.10.1", "Git tag v2.10.1 missing!"
print("\n==================================================")
print(">>> ALL 4 VERSION TARGETS & GIT TAG 100% PASS! <<<")
print("==================================================")
