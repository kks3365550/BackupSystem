# -*- coding: utf-8 -*-
import os
import subprocess

backup_dir = os.path.expandvars(r"%LOCALAPPDATA%\Programs\백업시스템\logs\task_backups")
os.makedirs(backup_dir, exist_ok=True)

print("=== 1. EXPORTING TASK XMLS ===")
for tn in ["BackupSystem_WebServer", "BackupSystem_Server_Daemon"]:
    xml_path = os.path.join(backup_dir, f"{tn}.xml")
    try:
        out = subprocess.check_output(f'schtasks /query /tn "{tn}" /xml', shell=True, text=True, errors="ignore")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"  [+] Saved {tn}.xml ({len(out)} bytes)")
    except Exception as e:
        print(f"  [-] Failed to export {tn}: {e}")

print("\n=== 2. DELETING DUPLICATE TASKS ===")
for tn in ["BackupSystem_WebServer", "BackupSystem_Server_Daemon"]:
    try:
        res = subprocess.run(f'schtasks /delete /tn "{tn}" /f', shell=True, capture_output=True, text=True)
        print(f"  [+] Deleted {tn}: returncode {res.returncode}")
    except Exception as e:
        print(f"  [-] Error deleting {tn}: {e}")

print("\n=== 3. VERIFYING REMAINING TASKS ===")
res = subprocess.run('schtasks /query /fo csv | findstr -i "BackupSystem"', shell=True, capture_output=True, text=True)
if not res.stdout.strip():
    print("  [+] No remaining BackupSystem scheduled tasks (CLEAN).")
else:
    print("  [-] Remaining:\n" + res.stdout)
