# -*- coding: utf-8 -*-
"""
Automated Git Versioning, Release Builder and Remote Deploy Tool
"""

import os
import sys
import re
import io
import time
import base64
import zipfile
import argparse
import subprocess
import urllib.request
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')
INIT_FILE = os.path.join(BASE_DIR, 'core', '__init__.py')
APP_FILE = os.path.join(BASE_DIR, 'web', 'app.py')
INDEX_FILE = os.path.join(BASE_DIR, 'web', 'templates', 'index.html')

def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return '1.0.0'

def bump_version(current: str, bump_type: str) -> str:
    parts = current.split('.')
    while len(parts) < 3:
        parts.append('0')
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    return f"{major}.{minor}.{patch}"

def update_source_versions(new_ver: str):
    # 1. VERSION file
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        f.write(f"{new_ver}\n")
    
    # 2. core/__init__.py
    if os.path.exists(INIT_FILE):
        content = open(INIT_FILE, 'r', encoding='utf-8').read()
        content = re.sub(r'__version__\s*=\s*["\'].*?["\']', f'__version__ = "{new_ver}"', content)
        with open(INIT_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
            
    # 3. web/app.py
    if os.path.exists(APP_FILE):
        content = open(APP_FILE, 'r', encoding='utf-8').read()
        content = re.sub(r'FastAPI\(title="Server & System Backup Manager",\s*version=["\'].*?["\']\)', f'FastAPI(title="Server & System Backup Manager", version="{new_ver}")', content)
        with open(APP_FILE, 'w', encoding='utf-8') as f:
            f.write(content)

    # 4. web/templates/index.html
    if os.path.exists(INDEX_FILE):
        content = open(INDEX_FILE, 'r', encoding='utf-8').read()
        content = re.sub(r'>v\d+\.\d+\.\d+<', f'>v{new_ver}<', content)
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"[1/5] Codebase version bumped to v{new_ver}")

def run_git_release(version: str, message: str):
    print(f"[2/5] Running Git commit and tagging v{version}...")
    try:
        subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR, check=True)
        commit_msg = f"release: v{version} - {message}" if message else f"release: v{version}"
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=BASE_DIR, check=True)
        tag_name = f"v{version}"
        subprocess.run(['git', 'tag', '-a', tag_name, '-m', f"Release {tag_name}"], cwd=BASE_DIR, check=True)
        print(f"      Git commit and tag '{tag_name}' created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"      Git warning/skip: {e}")

def sync_install_directories():
    print("[3/5] Synchronizing install distribution folders...")
    targets = [
        r'c:\Users\kksjmj\Desktop\ai\백업시스템_설치용',
        r'D:\백업시스템_설치용',
        r'F:\백업시스템_설치용'
    ]
    for target in targets:
        drive = os.path.splitdrive(target)[0]
        if drive and not os.path.exists(drive + '\\'):
            continue
        os.makedirs(target, exist_ok=True)
        
        # Sync core and web
        subprocess.run(['robocopy', os.path.join(BASE_DIR, 'core'), os.path.join(target, 'core'), '/E', '/MIR'], capture_output=True)
        subprocess.run(['robocopy', os.path.join(BASE_DIR, 'web'), os.path.join(target, 'web'), '/E', '/MIR'], capture_output=True)
        
        # Sync emergency_restore (with embedded python)
        if os.path.exists(os.path.join(BASE_DIR, 'emergency_restore')):
            subprocess.run(['robocopy', os.path.join(BASE_DIR, 'emergency_restore'), os.path.join(target, 'emergency_restore'), '/E', '/MIR'], capture_output=True)
        
        # Sync root py and bat files
        for item in os.listdir(BASE_DIR):
            full_path = os.path.join(BASE_DIR, item)
            if os.path.isfile(full_path) and (item.endswith('.py') or item.endswith('.bat') or item.endswith('.txt') or item.endswith('.md') or item == 'VERSION'):
                try:
                    with open(full_path, 'rb') as rf, open(os.path.join(target, item), 'wb') as wf:
                        wf.write(rf.read())
                except Exception:
                    pass
        print(f"      Synced to: {target}")

def build_self_extracting_updater(version: str) -> str:
    print("[4/5] Building standalone self-extracting updater...")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in ['core', 'web']:
            folder_path = os.path.join(BASE_DIR, folder)
            for root, dirs, files in os.walk(folder_path):
                if '__pycache__' in root:
                    continue
                for f in files:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    zf.write(full_path, rel_path)
        zf.write(os.path.join(BASE_DIR, 'run.py'), 'run.py')
        if os.path.exists(VERSION_FILE):
            zf.write(VERSION_FILE, 'VERSION')

    raw_bytes = buf.getvalue()
    b64 = base64.b64encode(raw_bytes).decode('ascii')
    chunks = [b64[i:i+64] for i in range(0, len(b64), 64)]
    b64_content = '\n'.join(chunks)

    bat_header = f"""@echo off
setlocal
title Backup Fast Engine Updater v{version}

echo ========================================================
echo   [1/3] Terminating running backup background processes...
echo ========================================================
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 1 /nobreak >nul

echo ========================================================
echo   [2/3] Extracting engine v{version} to F:\\백업시스템_설치용...
echo ========================================================
set "TARGET_DIR=F:\\백업시스템_설치용"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1

set "TMP_ZIP=%TEMP%\\update_v{version}_%RANDOM%.zip"

certutil -decode "%~f0" "%TMP_ZIP%" >nul 2>&1

powershell -ExecutionPolicy Bypass -NoProfile -Command "Expand-Archive -LiteralPath '%TMP_ZIP%' -DestinationPath '%TARGET_DIR%' -Force"

del "%TMP_ZIP%" >nul 2>&1

echo ========================================================
echo   [3/3] Starting Backup System v{version}...
echo ========================================================
cd /d "%TARGET_DIR%"
start "" "%TARGET_DIR%\\2_백업시스템_실행.bat"

echo ========================================================
echo   Update to v{version} completed successfully! (1-2s Cold Boot)
echo ========================================================
timeout /t 3 >nul
exit /b 0

-----BEGIN CERTIFICATE-----
"""
    bat_footer = """
-----END CERTIFICATE-----
"""
    out_bat = os.path.join(os.path.dirname(BASE_DIR), 'APPLY_UPDATE.bat')
    with open(out_bat, 'w', encoding='cp949', errors='ignore') as f:
        f.write(bat_header + b64_content + bat_footer)
    print(f"      Created: {out_bat} ({os.path.getsize(out_bat)} bytes)")
    return out_bat

def remote_deploy_if_online(remote_ip: str, bat_path: str):
    print(f"[5/5] Checking remote desktop connection ({remote_ip})...")
    try:
        ping_res = subprocess.run(['tailscale', 'ping', '-c', '1', remote_ip], capture_output=True, text=True, timeout=5)
        if ping_res.returncode == 0 and 'pong' in ping_res.stdout:
            print(f"      Remote host {remote_ip} is ONLINE (Tailscale)!")
            print(f"      Dispatching standalone updater to {remote_ip} via Taildrop...")
            subprocess.run(['tailscale', 'file', 'cp', bat_path, f"{remote_ip}:"], capture_output=True, timeout=15)
            print("      Taildrop dispatch complete!")
        else:
            print(f"      Remote host {remote_ip} is offline or unreachable via Tailscale. Remote deploy skipped.")
    except Exception as e:
        print(f"      Remote check skipped: {e}")

def main():
    parser = argparse.ArgumentParser(description="Backup System Release & Versioning Manager")
    parser.add_argument('--bump', choices=['patch', 'minor', 'major', 'none'], default='patch', help="Version bump type")
    parser.add_argument('-m', '--message', type=str, default="Automated engine build and bugfix release", help="Commit and changelog message")
    parser.add_argument('--remote-ip', type=str, default="100.99.168.69", help="Tailscale remote desktop IP")
    parser.add_argument('--skip-remote', action="store_true", help="Skip remote deployment")
    args = parser.parse_args()

    print("=" * 60)
    print("   Backup System Release & Versioning Pipeline")
    print("=" * 60)

    cur_ver = get_current_version()
    if args.bump != 'none':
        new_ver = bump_version(cur_ver, args.bump)
        update_source_versions(new_ver)
    else:
        new_ver = cur_ver
        update_source_versions(new_ver)

    run_git_release(new_ver, args.message)
    sync_install_directories()
    bat_path = build_self_extracting_updater(new_ver)

    if not args.skip_remote:
        remote_deploy_if_online(args.remote_ip, bat_path)

    print("=" * 60)
    print(f"   SUCCESS: Release v{new_ver} completely built and deployed!")
    print("=" * 60)

if __name__ == '__main__':
    main()
