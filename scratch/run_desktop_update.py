# -*- coding: utf-8 -*-
import subprocess
import time
import sys

DESKTOP_HOST = "kksjmj@100.90.20.59"
INSTALLER_PATH = r"C:\Users\kksjmj\Downloads\BackupSystem_Setup_v2.9.20.exe"
TARGET_DIR = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
LOG_PATH = r"C:\Users\kksjmj\Downloads\install_v2920.log"

def ssh_cmd(cmd: str) -> subprocess.CompletedProcess:
    full_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", DESKTOP_HOST, cmd]
    print(f">> [SSH]: {cmd}")
    res = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.stdout:
        print(f"STDOUT: {res.stdout.strip()}")
    if res.stderr:
        print(f"STDERR: {res.stderr.strip()}")
    return res

def main():
    print("=== [데스크탑 v2.9.20 업데이트 시작] ===")
    
    # 1. 백업시스템 전용 파이썬 프로세스(웹서버 + 트레이)만 안전하게 선별 종료 (타 워크로드 절대 무관)
    kill_cmd = (
        'powershell -NoProfile -Command "'
        '$procs = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like \'*Programs\\백업시스템\\python\\*\' }; '
        'if ($procs) { foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host Stopped Backup PID: $p.ProcessId } } else { Write-Host No active backup processes }'
        '"'
    )
    ssh_cmd(kill_cmd)
    time.sleep(2)
    
    # 2. 인스톨러 무음 실행 (지정 디렉토리에 설치)
    install_cmd = (
        f'start /wait {INSTALLER_PATH} '
        f'/DIR="{TARGET_DIR}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="{LOG_PATH}"'
    )
    res_inst = ssh_cmd(install_cmd)
    print(f"Installer executed. Return code: {res_inst.returncode}")
    time.sleep(3)
    
    # 3. 서비스/트레이 재기동
    start_cmd = (
        f'powershell -NoProfile -Command "'
        f'$vbs = Join-Path \'{TARGET_DIR}\' \'start_silent.vbs\'; '
        f'if (Test-Path $vbs) {{ Start-Process wscript.exe -ArgumentList \"`\"$vbs`\"\" }}; '
        f'Start-Sleep -Seconds 2'
        f'"'
    )
    ssh_cmd(start_cmd)
    time.sleep(3)
    
    # 4. 버전 확인
    ver_cmd = f'type "{TARGET_DIR}\\VERSION"'
    res_ver = ssh_cmd(ver_cmd)
    new_ver = res_ver.stdout.strip()
    print(f"[*] 데스크탑 신규 버전: {new_ver}")
    
    if "2.9.20" in new_ver:
        print(">>> [PASS] 데스크탑 v2.9.20 배포 및 기동 성공!")
    else:
        print(f">>> [FAIL] 버전 확인 실패: {new_ver}")
        sys.exit(1)

if __name__ == "__main__":
    main()
