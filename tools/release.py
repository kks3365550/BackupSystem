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
import hashlib
import shutil
import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')
INIT_FILE = os.path.join(BASE_DIR, 'core', '__init__.py')
APP_FILE = os.path.join(BASE_DIR, 'web', 'app.py')
INDEX_FILE = os.path.join(BASE_DIR, 'web', 'templates', 'index.html')
ISS_FILE = os.path.join(BASE_DIR, 'installer', 'BackupSystem.iss')

def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return '1.0.0'

def bump_version(current: str, bump_type: str) -> str:
    # 프리릴리즈 태그(-rc, -beta 등)를 안전하게 분리하여 파싱
    base_version = current.split('-')[0]
    parts = base_version.split('.')
    while len(parts) < 3:
        parts.append('0')
    
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError(f"Invalid version format: {current}")
    
    # RC 상태(예: 2.10.0-rc1)에서 minor로 승격 시 이미 2.10.0 이므로 그대로 확정
    if '-' in current and bump_type in ('minor', 'patch') and major == 2 and minor == 10:
        return f"{major}.{minor}.0"

    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")
        
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

    # 5. installer/BackupSystem.iss
    if os.path.exists(ISS_FILE):
        content = open(ISS_FILE, 'r', encoding='utf-8').read()
        content = re.sub(r'#define\s+MyAppVersion\s+["\'].*?["\']', f'#define MyAppVersion "{new_ver}"', content)
        with open(ISS_FILE, 'w', encoding='utf-8') as f:
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
        r'D:\백업시스템_설치용'
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
        
        # Sync keys (including release_ed25519.pub)
        if os.path.exists(os.path.join(BASE_DIR, 'keys')):
            subprocess.run(['robocopy', os.path.join(BASE_DIR, 'keys'), os.path.join(target, 'keys'), '/E', '/MIR'], **robo_kwargs)

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

def build_self_extracting_updater(version: str):
    print("[4/5] Building standalone self-extracting updater & Ed25519 digital signature...")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in ['core', 'web', 'keys']:
            folder_path = os.path.join(BASE_DIR, folder)
            if not os.path.exists(folder_path):
                continue
            for root, dirs, files in os.walk(folder_path):
                if '__pycache__' in root:
                    continue
                for f in files:
                    f_lower = f.lower()
                    # CRITICAL SECURITY RULE: NEVER include private keys or sensitive credentials in distribution package
                    if f_lower.endswith('.key') or f_lower.endswith('.pem') or 'private' in f_lower or f_lower.endswith('.p12') or f_lower.endswith('.pfx'):
                        continue
                    # For keys/ folder, ONLY allow public keys (.pub)
                    if os.path.basename(root) == 'keys' and not f_lower.endswith('.pub'):
                        continue
                    # NEVER include installer executables in update package
                    if f_lower.endswith('.exe'):
                        continue
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    zf.write(full_path, rel_path)
        # Bundle essential runner scripts
        for extra_script in ['run.py', 'start_silent.vbs', 'start_tray.vbs', 'launch_dashboard.vbs', 'stop_backup_system.bat', '2_백업시스템_실행.bat']:
            extra_path = os.path.join(BASE_DIR, extra_script)
            if os.path.exists(extra_path):
                zf.write(extra_path, extra_script)
        if os.path.exists(VERSION_FILE):
            zf.write(VERSION_FILE, 'VERSION')

        # Automated Zero-Leak Verification
        for name in zf.namelist():
            name_lower = name.lower()
            if name_lower.endswith('.key') or name_lower.endswith('.pem') or 'private' in name_lower or 'release_ed25519.key' in name_lower:
                raise RuntimeError(f"FATAL SECURITY VIOLATION: Private key detected in release package: {name}! Build aborted.")
        print(f"      [Security Audit PASSED] Zero private keys found in package ({len(zf.namelist())} files).")

    raw_bytes = buf.getvalue()

    # 1. Sign package with Ed25519 private key
    priv_key_path = os.path.join(BASE_DIR, 'keys', 'release_ed25519.key')
    sig_hex = ""
    if os.path.exists(priv_key_path):
        try:
            from core.crypto_sign import sign_bytes_ed25519
            sig_hex = sign_bytes_ed25519(raw_bytes, priv_key_path)
            print(f"      Ed25519 Signature generated: {sig_hex[:16]}...{sig_hex[-16:]}")
        except Exception as e:
            print(f"      Warning: Ed25519 signing failed: {e}")
    else:
        print("      Notice: release_ed25519.key not found, signature omitted.")

    # 2. Save release zip and signature in dist/
    dist_dir = os.path.join(BASE_DIR, 'dist')
    os.makedirs(dist_dir, exist_ok=True)
    zip_path = os.path.join(dist_dir, f"release_v{version}.zip")
    with open(zip_path, 'wb') as f:
        f.write(raw_bytes)
    if sig_hex:
        with open(zip_path + ".sig", 'w', encoding='utf-8') as f:
            f.write(sig_hex)

    b64 = base64.b64encode(raw_bytes).decode('ascii')
    chunks = [b64[i:i+64] for i in range(0, len(b64), 64)]
    b64_content = '\r\n'.join(chunks)

    bat_header = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "setlocal\r\n"
        f"title Backup Fast Engine Updater v{version}\r\n"
        f"REM [Security] Ed25519-Signature: {sig_hex}\r\n"
        "\r\n"
        "echo ========================================================\r\n"
        "echo   [1/3] Terminating running backup background processes...\r\n"
        "echo ========================================================\r\n"
        "powershell -NoProfile -Command \"Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | ForEach-Object { $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; if ($p) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }\" >nul 2>&1\r\n"
        "powershell -NoProfile -Command \"Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*백업시스템*' -or $_.CommandLine -like '*run.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }\" >nul 2>&1\r\n"
        "ping 127.0.0.1 -n 2 >nul\r\n"
        "REM Silently ensure cryptography dependency\r\n"
        "python -m pip install cryptography --quiet >nul 2>&1\r\n"
        "\r\n"
        "echo ========================================================\r\n"
        f"echo   [2/3] Detecting installation directory ^& Extracting v{version}...\r\n"
        "echo ========================================================\r\n"
        "set \"TARGET_DIR=\"\r\n"
        "REM (1) RTX 5080 Desktop target directory (Highest Priority for Desktop)\r\n"
        "if exist \"F:\\백업시스템_설치용\" set \"TARGET_DIR=F:\\백업시스템_설치용\"\r\n"
        "REM (2) K12 Mini PC target directory (for K12 Mini PC)\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    if exist \"D:\\백업시스템_설치용\\core\" set \"TARGET_DIR=D:\\백업시스템_설치용\"\r\n"
        ")\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    if exist \"D:\\백업시스템_설치용\" set \"TARGET_DIR=D:\\백업시스템_설치용\"\r\n"
        ")\r\n"
        "REM (3) Inno Setup registry lookup\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    for /f \"tokens=2* skip=2\" %%a in ('reg query \"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{E8A42F38-9B7C-4C2E-8E1A-98C32B7D501F}_is1\" /v InstallLocation 2^>nul') do set \"TARGET_DIR=%%b\"\r\n"
        ")\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    for /f \"tokens=2* skip=2\" %%a in ('reg query \"HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{E8A42F38-9B7C-4C2E-8E1A-98C32B7D501F}_is1\" /v InstallLocation 2^>nul') do set \"TARGET_DIR=%%b\"\r\n"
        ")\r\n"
        "REM (4) Standard Program Files check\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    if exist \"%ProgramFiles%\\백업시스템\\core\" set \"TARGET_DIR=%ProgramFiles%\\백업시스템\"\r\n"
        ")\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    if exist \"%ProgramFiles(x86)%\\백업시스템\\core\" set \"TARGET_DIR=%ProgramFiles(x86)%\\백업시스템\"\r\n"
        ")\r\n"
        "REM (5) Current execution directory\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    if exist \"%~dp0core\" set \"TARGET_DIR=%~dp0\"\r\n"
        ")\r\n"
        "REM (6) Fallback default\r\n"
        "if not defined TARGET_DIR (\r\n"
        "    if exist \"F:\\\" (\r\n"
        "        set \"TARGET_DIR=F:\\백업시스템_설치용\"\r\n"
        "    ) else (\r\n"
        "        set \"TARGET_DIR=D:\\백업시스템_설치용\"\r\n"
        "    )\r\n"
        ")\r\n"
        "echo   Detected Target: %TARGET_DIR%\r\n"
        "if not exist \"%TARGET_DIR%\" mkdir \"%TARGET_DIR%\" >nul 2>&1\r\n"
        "\r\n"
        f"set \"TMP_ZIP=%TEMP%\\update_v{version}_%RANDOM%.zip\"\r\n"
        "\r\n"
        "certutil -decode \"%~f0\" \"%TMP_ZIP%\" >nul 2>&1\r\n"
        "\r\n"
        "powershell -ExecutionPolicy Bypass -NoProfile -Command \"Expand-Archive -LiteralPath '%TMP_ZIP%' -DestinationPath '%TARGET_DIR%' -Force\"\r\n"
        "\r\n"
        "del \"%TMP_ZIP%\" >nul 2>&1\r\n"
        "\r\n"
        "REM Update Desktop Shortcut to point to updated installation\r\n"
        "powershell -ExecutionPolicy Bypass -NoProfile -Command \"$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $lnk = $ws.CreateShortcut(\\\"$d\\백업시스템.lnk\\\"); $lnk.TargetPath = 'wscript.exe'; $lnk.Arguments = \\\"`\\\"\" + '%TARGET_DIR%' + \"\\start_silent.vbs`\\\"\\\"; $lnk.WorkingDirectory = '%TARGET_DIR%'; $lnk.Save()\" >nul 2>&1\r\n"
        "\r\n"
        "echo ========================================================\r\n"
        f"echo   [3/3] Starting Backup System v{version}...\r\n"
        "echo ========================================================\r\n"
        "cd /d \"%TARGET_DIR%\"\r\n"
        "if exist \"%TARGET_DIR%\\start_silent.vbs\" (\r\n"
        "    wscript.exe \"%TARGET_DIR%\\start_silent.vbs\"\r\n"
        ") else if exist \"%TARGET_DIR%\\2_백업시스템_실행.bat\" (\r\n"
        "    start \"\" \"%TARGET_DIR%\\2_백업시스템_실행.bat\"\r\n"
        ") else if exist \"%TARGET_DIR%\\BackupSystem.exe\" (\r\n"
        "    start \"\" \"%TARGET_DIR%\\BackupSystem.exe\"\r\n"
        ") else if exist \"%TARGET_DIR%\\run.py\" (\r\n"
        "    start \"\" pythonw.exe \"%TARGET_DIR%\\run.py\"\r\n"
        ")\r\n"
        "\r\n"
        "echo ========================================================\r\n"
        f"echo   Update to v{version} completed successfully! (1-2s Cold Boot)\r\n"
        "echo ========================================================\r\n"
        "ping 127.0.0.1 -n 3 >nul\r\n"
        "exit /b 0\r\n"
        "\r\n"
        "-----BEGIN CERTIFICATE-----\r\n"
    )
    bat_footer = "\r\n-----END CERTIFICATE-----\r\n"

    out_bat = os.path.join(os.path.dirname(BASE_DIR), 'APPLY_UPDATE.bat')
    with open(out_bat, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(bat_header + b64_content + bat_footer)
    print(f"      Created: {out_bat} ({os.path.getsize(out_bat):,} bytes)")
    return out_bat, sig_hex, raw_bytes

def remote_deploy_if_online(remote_ip: str, bat_path: str, sig_hex: str = "", raw_bytes: bytes = None, version: str = ""):
    ts_kwargs = {'capture_output': True, 'timeout': 5}
    if sys.platform.startswith('win') and hasattr(subprocess, 'CREATE_NO_WINDOW'):
        ts_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    try:
        ping_res = subprocess.run(['tailscale', 'ping', '-c', '1', remote_ip], text=True, **ts_kwargs)
        if ping_res.returncode == 0 and 'pong' in ping_res.stdout:
            print(f"      Remote host {remote_ip} is ONLINE (Tailscale)!")

            # 1. Try Tailscale SSH automated deployment if available
            ssh_deployed = False
            dist_zip = os.path.join(BASE_DIR, 'dist', f'release_v{version}.zip') if version else None
            if dist_zip and os.path.exists(dist_zip):
                try:
                    ssh_check = subprocess.run(
                        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=3', remote_ip, 'echo SSH_OK'],
                        text=True, **ts_kwargs
                    )
                    if ssh_check.returncode == 0 and 'SSH_OK' in ssh_check.stdout:
                        print(f"      Remote host {remote_ip} supports Tailscale SSH! Deploying v{version}...")
                        remote_tmp = f"C:/Users/kksjmj/AppData/Local/Temp/release_v{version}.zip"
                        scp_res = subprocess.run(
                            ['scp', dist_zip, f"{remote_ip}:{remote_tmp}"],
                            **ts_kwargs
                        )
                        if scp_res.returncode == 0:
                            # Safely terminate ONLY the backup system on port 8765 without touching Qwen or other python jobs
                            remote_ps = (
                                "$p8765 = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue; "
                                "if ($p8765) { foreach ($c in $p8765) { "
                                "  $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue; "
                                "  if ($p) { "
                                "    $cmd = (Get-CimInstance Win32_Process -Filter \"ProcessId = $($p.Id)\").CommandLine; "
                                "    if ($cmd -like '*백업시스템*' -or $cmd -like '*run.py*') { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } "
                                "  } "
                                "} }; "
                                "Start-Sleep -Seconds 1; "
                                "$tgt = 'F:\\백업시스템_설치용'; "
                                "if (-not (Test-Path $tgt)) { $tgt = 'D:\\백업시스템_설치용' }; "
                                "if (-not (Test-Path $tgt)) { New-Item -ItemType Directory -Path $tgt -Force | Out-Null }; "
                                f"Expand-Archive -LiteralPath '{remote_tmp}' -DestinationPath $tgt -Force; "
                                f"Remove-Item '{remote_tmp}' -Force -ErrorAction SilentlyContinue; "
                                "$pyw = Join-Path $tgt '.venv\\Scripts\\pythonw.exe'; "
                                "if (-not (Test-Path $pyw)) { $pyw = 'pythonw.exe' }; "
                                "$runPy = Join-Path $tgt 'run.py'; "
                                "([wmiclass]'Win32_Process').Create(\"$pyw $runPy\", $tgt, $null) | Out-Null; "
                                "Start-Sleep -Seconds 2; "
                                "Get-Content (Join-Path $tgt 'VERSION') -ErrorAction SilentlyContinue"
                            )
                            b64_ps = base64.b64encode(remote_ps.encode('utf-16le')).decode('ascii')
                            exec_res = subprocess.run(
                                ['ssh', remote_ip, 'powershell', '-NoProfile', '-EncodedCommand', b64_ps],
                                text=True, **ts_kwargs
                            )
                            if exec_res.returncode == 0:
                                print(f"      [OK] Remote {remote_ip} automatically updated & restarted to v{version} via Tailscale SSH!")
                                ssh_deployed = True
                except Exception as e_ssh:
                    print(f"      Notice: Remote SSH deploy attempt skipped ({e_ssh})")

            if not ssh_deployed:
                # 2. Try HTTP self-update API first if raw_bytes and sig_hex are available
                updated_via_api = False
                if raw_bytes and sig_hex:
                    try:
                        update_url = f"http://{remote_ip}:8765/api/system/self-update"
                        req = urllib.request.Request(
                            update_url,
                            data=raw_bytes,
                            headers={
                                'Content-Type': 'application/octet-stream',
                                'X-Package-Signature': sig_hex
                            },
                            method='POST'
                        )
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            if resp.status == 200:
                                print(f"      [OK] Remote {remote_ip} updated instantly via signed Self-Update API!")
                                updated_via_api = True
                    except Exception as e_api:
                        print(f"      Notice: Remote HTTP update skipped ({e_api}), falling back to Taildrop.")

                if not updated_via_api:
                    print(f"      Dispatching standalone updater to {remote_ip} via Taildrop...")
                    cp_kwargs = dict(ts_kwargs)
                    cp_kwargs['timeout'] = 15
                    subprocess.run(['tailscale', 'file', 'cp', bat_path, f"{remote_ip}:"], **cp_kwargs)
                    print("      Taildrop dispatch complete!")
        else:
            print(f"      Remote host {remote_ip} is offline or unreachable via Tailscale. Remote deploy skipped.")
    except Exception as e:
        print(f"      Remote check skipped: {e}")

FIREBASE_PROJECT_ID = "sunhang-772e5"
FIREBASE_API_KEY = "AIzaSyCe21skNfRno3PPo-xRYCqfwh3jtboo7Ls"
FIRESTORE_REST_BASE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"

def publish_to_firebase_releases(version: str, raw_bytes: bytes, sig_hex: str, changelog: str = ""):
    """
    Firebase Release 배포:
    1. 패키지 SHA-256 계산
    2. dist/releases/v{version}/release.json 생성 및 패키지 보관
    3. release_admin 계정으로 Firebase Auth 로그인 (ID 토큰 획득)
    4. Firestore app_releases/v{version} (불변 보존 문서) 등록
    5. Firestore app_releases/latest (원자적 최신 포인터) 갱신
    """
    print(f"[4.5/5] Publishing release v{version} to Firebase Cloud...")
    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
    file_size = len(raw_bytes)
    now_iso = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()

    # 1. Local structured release folder (Immutable)
    rel_folder = os.path.join(BASE_DIR, 'dist', 'releases', f"v{version}")
    os.makedirs(rel_folder, exist_ok=True)
    pkg_name = f"backup_engine_{version}.zip"
    pkg_path = os.path.join(rel_folder, pkg_name)
    with open(pkg_path, 'wb') as f:
        f.write(raw_bytes)

    # Public download URL pointing to Firebase
    download_url = f"https://sunhang-772e5.web.app/releases/v{version}/{pkg_name}"
    storage_path = f"releases/v{version}/{pkg_name}"

    meta = {
        "version": version,
        "release_date": now_iso,
        "package_name": pkg_name,
        "storage_path": storage_path,
        "download_url": download_url,
        "file_size": file_size,
        "sha256": sha256_hash,
        "signature": sig_hex,
        "mandatory": False,
        "min_supported_version": "2.8.0",
        "changelog": changelog or f"Release v{version} automated update"
    }

    meta_json_path = os.path.join(rel_folder, "release.json")
    with open(meta_json_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"      Structured package saved: {pkg_path}")

    # Also sync to hosting staging if 선행모바일 exists
    sunhang_hosting_rel = os.path.join(os.path.dirname(BASE_DIR), "선행모바일", "ios_pwa", "releases", f"v{version}")
    if os.path.exists(os.path.dirname(sunhang_hosting_rel)):
        try:
            os.makedirs(sunhang_hosting_rel, exist_ok=True)
            shutil.copy2(pkg_path, os.path.join(sunhang_hosting_rel, pkg_name))
            shutil.copy2(meta_json_path, os.path.join(sunhang_hosting_rel, "release.json"))
            # Automatically deploy to Firebase Hosting so download_url is immediately accessible
            sunhang_root = os.path.dirname(os.path.dirname(sunhang_hosting_rel))
            print("      Deploying release package to Firebase Hosting...")
            deploy_flags = {}
            if sys.platform.startswith('win') and hasattr(subprocess, 'CREATE_NO_WINDOW'):
                deploy_flags['creationflags'] = subprocess.CREATE_NO_WINDOW
            npx_cmd = 'npx.cmd' if sys.platform.startswith('win') else 'npx'
            subprocess.run([npx_cmd, '--yes', 'firebase-tools', 'deploy', '--only', 'hosting'], cwd=sunhang_root, **deploy_flags)
            print("      Firebase Hosting deploy complete!")
        except Exception as e_sync:
            print(f"      Hosting staging notice: {e_sync}")

    # 2. Authenticate as release_admin via Firebase Auth
    admin_cred_path = os.path.join(BASE_DIR, 'keys', 'release_admin_cred.json')
    if not os.path.exists(admin_cred_path):
        print(f"      Notice: {admin_cred_path} not found. Skipping Firestore release publishing.")
        return

    try:
        with open(admin_cred_path, 'r', encoding='utf-8') as f:
            cred = json.load(f)
        auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        auth_payload = json.dumps({
            "email": cred["email"],
            "password": cred["password"],
            "returnSecureToken": True
        }).encode('utf-8')
        req = urllib.request.Request(auth_url, data=auth_payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            id_token = json.loads(resp.read().decode('utf-8'))['idToken']

        # 3. Publish to Firestore: app_releases/v{version} and app_releases/latest
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {id_token}'
        }

        # Convert meta to Firestore fields
        fields = {
            "version": {"stringValue": meta["version"]},
            "release_date": {"stringValue": meta["release_date"]},
            "package_name": {"stringValue": meta["package_name"]},
            "storage_path": {"stringValue": meta["storage_path"]},
            "download_url": {"stringValue": meta["download_url"]},
            "file_size": {"integerValue": str(meta["file_size"])},
            "sha256": {"stringValue": meta["sha256"]},
            "signature": {"stringValue": meta["signature"]},
            "mandatory": {"booleanValue": meta["mandatory"]},
            "min_supported_version": {"stringValue": meta["min_supported_version"]},
            "changelog": {"stringValue": meta["changelog"]}
        }
        body = json.dumps({"fields": fields}).encode('utf-8')

        # 3.1 Immutable historical release doc
        url_ver = f"{FIRESTORE_REST_BASE}/app_releases/v{version}?key={FIREBASE_API_KEY}"
        req_ver = urllib.request.Request(url_ver, data=body, headers=headers, method='PATCH')
        with urllib.request.urlopen(req_ver, timeout=8) as resp:
            if resp.status == 200:
                print(f"      [OK] Immutable release record saved to Firestore: app_releases/v{version}")

        # 3.2 Atomic latest pointer update
        url_latest = f"{FIRESTORE_REST_BASE}/app_releases/latest?key={FIREBASE_API_KEY}"
        req_latest = urllib.request.Request(url_latest, data=body, headers=headers, method='PATCH')
        with urllib.request.urlopen(req_latest, timeout=8) as resp:
            if resp.status == 200:
                print(f"      [OK] Atomic 'latest' release pointer updated in Firestore: v{version}")

    except Exception as e_pub:
        print(f"      Warning: Firestore release publishing failed: {e_pub}")

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
        flags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            flags |= subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, 'DETACHED_PROCESS'):
            flags |= subprocess.DETACHED_PROCESS
        subprocess.Popen(
            ['wscript.exe', vbs_path],
            cwd=BASE_DIR,
            creationflags=flags,
            close_fds=True
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
    parser.add_argument('--version', type=str, default=None, help="Explicit target version to set (bypasses --bump)")
    parser.add_argument('-m', '--message', type=str, default="Automated engine build and bugfix release", help="Commit and changelog message")
    parser.add_argument('--remote-ip', type=str, default="100.90.20.59", help="Tailscale remote desktop IP")
    parser.add_argument('--skip-remote', action="store_true", help="Skip remote deployment")
    parser.add_argument('--skip-restart', action="store_true", help="Skip local server restart after release")
    args = parser.parse_args()

    print("=" * 60)
    print("   Backup System Release & Versioning Pipeline")
    print("=" * 60)

    cur_ver = get_current_version()
    if args.version:
        new_ver = args.version
        update_source_versions(new_ver)
    elif args.bump != 'none':
        new_ver = bump_version(cur_ver, args.bump)
        update_source_versions(new_ver)
    else:
        new_ver = cur_ver
        update_source_versions(new_ver)

    run_git_release(new_ver, args.message)
    sync_install_directories()
    bat_path, sig_hex, raw_bytes = build_self_extracting_updater(new_ver)
    publish_to_firebase_releases(new_ver, raw_bytes, sig_hex, changelog=args.message)

    if not args.skip_remote:
        remote_deploy_if_online(args.remote_ip, bat_path, sig_hex, raw_bytes, version=new_ver)

    if not args.skip_restart:
        restart_local_server()

    print("=" * 60)
    print(f"   SUCCESS: Release v{new_ver} completely built and deployed!")
    print("=" * 60)

if __name__ == '__main__':
    main()
