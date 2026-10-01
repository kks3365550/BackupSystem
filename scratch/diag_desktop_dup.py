# -*- coding: utf-8 -*-
import os
import subprocess
import winreg

print("=== 1. STARTUP FOLDERS ===")
user_startup = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
common_startup = os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup")

for name, path in [("User Startup", user_startup), ("Common Startup", common_startup)]:
    print(f"[{name}] {path}")
    if os.path.exists(path):
        for f in os.listdir(path):
            print(f"  - {f}")
    else:
        print("  (Path not found)")

print("\n=== 2. REGISTRY RUN KEYS ===")
def check_reg(hive, subkey):
    try:
        with winreg.OpenKey(hive, subkey) as k:
            count = winreg.QueryInfoKey(k)[1]
            for i in range(count):
                name, val, _ = winreg.EnumValue(k, i)
                if "backup" in name.lower() or "backup" in str(val).lower():
                    print(f"  [{name}] => {val}")
    except Exception as e:
        pass

print("[HKCU Run]")
check_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
print("[HKLM Run]")
check_reg(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")

print("\n=== 3. SCHEDULED TASKS ===")
try:
    res = subprocess.run('schtasks /query /fo csv /v | findstr -i "BackupSystem"', shell=True, capture_output=True, text=True, errors="ignore")
    print(res.stdout)
except Exception as e:
    print(e)

print("\n=== 4. RUNNING PROCESSES (python, pythonw, vbs, tray) ===")
try:
    res = subprocess.run('powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like \'*백업시스템*\' -or $_.CommandLine -like \'*tray*\' -or $_.CommandLine -like \'*run.py*\' } | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-List"', shell=True, capture_output=True, text=True, errors="ignore")
    print(res.stdout)
except Exception as e:
    print(e)
