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
        r'D:\백업시스템_설치용',
        r'F:\백업시스템_설치용'
    ]
    for target in targets:
        drive = os.path.splitdrive(target)[0]
        if drive and not os.path.exists(drive + '\\'):
            continue
        os.makedirs(target, exist_ok=True)
        
        robo_kwargs = {'capture_output': True}
        if sys.platform.startswith('win') and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            robo_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        # Sync core and web
        subprocess.run(['robocopy', os.path.join(BASE_DIR, 'core'), os.path.join(target, 'core'), '/E', '/MIR'], **robo_kwargs)
        subprocess.run(['robocopy', os.path.join(BASE_DIR, 'web'), os.path.join(target, 'web'), '/E', '/MIR'], **robo_kwargs)
        
        # Sync emergency_restore (with embedded python)
        if os.path.exists(os.path.join(BASE_DIR, 'emergency_restore')):
            subprocess.run(['robocopy', os.path.join(BASE_DIR, 'emergency_restore'), os.path.join(target, 'emergency_restore'), '/E', '/MIR'], **robo_kwargs)
        
        # Sync root py and bat files
        for item in os.listdir(BASE_DIR):
            full_path = os.path.join(BASE_DIR, item)
            if os.path.isfile(full_path) and (item.endswith('.py') or item.endswith('.bat') or item.endswith('.vbs') or item.endswith('.txt') or item.endswith('.md') or item == 'VERSION'):
                try:
                    with open(full_path, 'rb') as rf, open(os.path.join(target, item), 'wb') as wf:
                        wf.write(rf.read())
                except Exception:
                    pass
        print(f"      Synced to: {target}")

    # Also sync emergency disaster recovery kit to D:\MyBackup_Repository if it exists
    repo_backup = r"D:\MyBackup_Repository"
    if os.path.exists(repo_backup):
        emerg_src = os.path.join(BASE_DIR, 'emergency_restore')
        if os.path.exists(emerg_src):
            subprocess.run(['robocopy', emerg_src, os.path.join(repo_backup, 'emergency_restore'), '/E', '/MIR'], **robo_kwargs)
        recovery_files = [
            "원클릭_C드라이브_전체복구.bat",
            "선택복구_대화형.bat",
            "Restore_Full_C_Drive.bat",
            "Restore_Interactive.bat",
            "README_재해복구_가이드.txt",
            "5_베어메탈_시스템이미지_백업(OS+오피스).bat"
        ]
        for rf in recovery_files:
            rf_src = os.path.join(BASE_DIR, rf)
            if os.path.exists(rf_src):
                try:
                    with open(rf_src, 'rb') as f_in, open(os.path.join(repo_backup, rf), 'wb') as f_out:
                        f_out.write(f_in.read())
                except Exception:
                    pass
        print(f"      Synced Disaster Recovery Kit to: {repo_backup}")

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
    ts_kwargs = {'capture_output': True, 'timeout': 5}
    if sys.platform.startswith('win') and hasattr(subprocess, 'CREATE_NO_WINDOW'):
        ts_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    try:
        ping_res = subprocess.run(['tailscale', 'ping', '-c', '1', remote_ip], text=True, **ts_kwargs)
        if ping_res.returncode == 0 and 'pong' in ping_res.stdout:
            print(f"      Remote host {remote_ip} is ONLINE (Tailscale)!")
            print(f"      Dispatching standalone updater to {remote_ip} via Taildrop...")
            cp_kwargs = dict(ts_kwargs)
            cp_kwargs['timeout'] = 15
            subprocess.run(['tailscale', 'file', 'cp', bat_path, f"{remote_ip}:"], **cp_kwargs)
            print("      Taildrop dispatch complete!")
        else:
            print(f"      Remote host {remote_ip} is offline or unreachable via Tailscale. Remote deploy skipped.")
    except Exception as e:
        print(f"      Remote check skipped: {e}")

def restart_local_server():
    """로컬 백업 서버(pythonw run.py)를 Kill 후 start_silent.vbs로 재시작하고, 포트 8765가 열릴 때까지 확인."""
    print("[5/5] Restarting local backup server...")
    if not sys.platform.startswith('win'):
        print("      Non-Windows: server restart skipped.")
        return

    no_win = {}
    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
        no_win = {'creationflags': subprocess.CREATE_NO_WINDOW}

    # 1. Kill running pythonw processes
    try:
        subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             'Get-Process -Name pythonw -ErrorAction SilentlyContinue | Stop-Process -Force'],
            capture_output=True, timeout=8, **no_win
        )
        print("      Stopped existing pythonw process(es).")
    except Exception as e:
        print(f"      Stop warning (may be OK if nothing was running): {e}")

    import time
    time.sleep(1)

    # 2. Restart via start_silent.vbs
    vbs_path = os.path.join(BASE_DIR, 'start_silent.vbs')
    if not os.path.exists(vbs_path):
        print(f"      start_silent.vbs not found at {vbs_path}. Restart skipped.")
        return

    try:
        subprocess.Popen(
            ['wscript.exe', vbs_path],
            cwd=BASE_DIR,
            **no_win
        )
        print("      start_silent.vbs launched.")
    except Exception as e:
        print(f"      Failed to launch start_silent.vbs: {e}")
        return

    # 3. Wait up to 20s for port 8765 to open
    import socket
    deadline = time.time() + 20
    alive = False
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', 8765), timeout=1):
                alive = True
                break
        except OSError:
            time.sleep(0.5)

    if alive:
        print("      [OK] Server is live on http://127.0.0.1:8765")
    else:
        print("      [WARN] Server did not respond within 20s -- check logs/startup_error.log")

def main():
    parser = argparse.ArgumentParser(description="Backup System Release & Versioning Manager")
    parser.add_argument('--bump', choices=['patch', 'minor', 'major', 'none'], default='patch', help="Version bump type")
    parser.add_argument('-m', '--message', type=str, default="Automated engine build and bugfix release", help="Commit and changelog message")
    parser.add_argument('--remote-ip', type=str, default="100.90.20.59", help="Tailscale remote desktop IP")
    parser.add_argument('--skip-remote', action="store_true", help="Skip remote deployment")
    parser.add_argument('--skip-restart', action="store_true", help="Skip local server restart after release")
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

    if not args.skip_restart:
        restart_local_server()

    print("=" * 60)
    print(f"   SUCCESS: Release v{new_ver} completely built and deployed!")
    print("=" * 60)

if __name__ == '__main__':
    main()
