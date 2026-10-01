# -*- coding: utf-8 -*-
"""
scratch/check_desktop_services.py
==================================
Runs on Desktop:
1. Checks Tabby process & port 8080.
2. Checks BackupSystem process & port 8765.
3. If BackupSystem not running, launches it cleanly via WMI.
4. If Tabby not running, launches it cleanly.
"""

import os
import sys
import subprocess
import time
import socket
import urllib.request
import json

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0

print("=" * 60)
print(" [DESKTOP SERVICE HEALTH & RECOVERY]")
print("=" * 60)

tabby_open = is_port_open(8080)
backup_open = is_port_open(8765)

print(f"[*] Port 8080 (Tabby/Qwen) Open: {tabby_open}")
print(f"[*] Port 8765 (BackupSystem) Open: {backup_open}")

# If BackupSystem not running, start it
if not backup_open:
    print("[*] Starting BackupSystem v2.10.0 via pythonw...")
    app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
    py_exe = os.path.join(app_dir, "python", "pythonw.exe")
    if not os.path.exists(py_exe):
        py_exe = "pythonw.exe"
    vbs = os.path.join(app_dir, "start_silent.vbs")
    subprocess.Popen(["wscript.exe", vbs], cwd=app_dir)
    time.sleep(3)
    backup_open = is_port_open(8765)
    print(f"    - After restart: Port 8765 Open = {backup_open}")

# If Tabby not running, start it
if not tabby_open:
    print("[*] Starting Tabby/Qwen via start_tabby_task.bat...")
    tabby_dir = r"C:\Users\kksjmj\tabbyAPI"
    tabby_vbs = os.path.join(tabby_dir, "run_tabby_hidden.vbs")
    if os.path.exists(tabby_vbs):
        subprocess.Popen(["wscript.exe", tabby_vbs], cwd=tabby_dir)
    time.sleep(5)
    tabby_open = is_port_open(8080)
    print(f"    - After restart: Port 8080 Open = {tabby_open}")

# Check BackupSystem API
if backup_open:
    try:
        url = "http://127.0.0.1:8765/api/system/release-info"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            ver = data.get("data", {}).get("version")
            print(f"[+] BackupSystem Live Version: {ver}")
    except Exception as e:
        print(f"[-] BackupSystem API check error: {e}")

print("=" * 60)
