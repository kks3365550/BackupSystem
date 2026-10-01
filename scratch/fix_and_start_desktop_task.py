# -*- coding: utf-8 -*-
import subprocess

DESKTOP_IP = "100.90.20.59"
DESKTOP_USER = "kksjmj"

def run_ssh(cmd):
    full_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", f"{DESKTOP_USER}@{DESKTOP_IP}", cmd]
    print(f"\n>>> [SSH {DESKTOP_IP}]: {cmd}")
    res = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.stdout:
        print(f"[STDOUT]\n{res.stdout.strip()}")
    if res.stderr:
        print(f"[STDERR]\n{res.stderr.strip()}")
    return res

if __name__ == "__main__":
    ps = (
        "$dir = 'C:\\Users\\kksjmj\\AppData\\Local\\Programs\\백업시스템'; "
        "$pyw = Join-Path $dir 'python\\pythonw.exe'; "
        "$action = New-ScheduledTaskAction -Execute $pyw -Argument 'run.py' -WorkingDirectory $dir; "
        "$principal = New-ScheduledTaskPrincipal -UserId 'kksjmj' -LogonType Interactive -RunLevel Highest; "
        "$trigger = New-ScheduledTaskTrigger -AtLogon; "
        "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0); "
        "Register-ScheduledTask -TaskName 'BackupSystem_WebServer' -Action $action -Principal $principal -Trigger $trigger -Settings $settings -Force; "
        "Start-ScheduledTask -TaskName 'BackupSystem_WebServer'; "
        "Start-Sleep -Seconds 4; "
        "Get-ScheduledTask -TaskName 'BackupSystem_WebServer' | Select-Object TaskName, State; "
        "netstat -ano | findstr 8765; "
        "try { "
        "  $res = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/system-info' -TimeoutSec 5; "
        "  Write-Host 'System Info Check:' ($res | ConvertTo-Json -Compress); "
        "} catch { "
        "  Write-Host 'System Info Error:' $_; "
        "}"
    )
    run_ssh(f"powershell -NoProfile -Command \"{ps}\"")
