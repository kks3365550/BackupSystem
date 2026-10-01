# -*- coding: utf-8 -*-
import subprocess
import json

DESKTOP_IP = "100.90.20.59"
DESKTOP_USER = "kksjmj"

def run_ssh(cmd):
    full_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", f"{DESKTOP_USER}@{DESKTOP_IP}", cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res

if __name__ == "__main__":
    ps = (
        "$dir = 'C:\\Users\\kksjmj\\AppData\\Local\\Programs\\백업시스템'; "
        "$profPath = Join-Path $dir 'data\\profiles.json'; "
        "if (Test-Path $profPath) { "
        "  $p = Get-Content $profPath -Raw | ConvertFrom-Json; "
        "  Write-Host 'PROFILES_COUNT:' $p.Count; "
        "  foreach ($item in $p) { "
        "    Write-Host 'PROFILE_NAME:' $item.name; "
        "    Write-Host 'REPO_DIR:' $item.repo_dir; "
        "    Write-Host 'AUTO_BACKUP_ENABLED:' $item.auto_backup_enabled; "
        "    $snapsDir = Join-Path $item.repo_dir 'snapshots'; "
        "    if (Test-Path $snapsDir) { "
        "      $snaps = Get-ChildItem $snapsDir -Filter '*.json'; "
        "      Write-Host 'SNAPSHOTS_COUNT:' $snaps.Count; "
        "      if ($snaps.Count -gt 0) { Write-Host 'LATEST_SNAPSHOT:' ($snaps | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name } "
        "    } else { Write-Host 'NO_SNAPSHOTS_DIR' } "
        "  } "
        "} else { Write-Host 'NO_PROFILES_FILE' }"
    )
    r = run_ssh(f"powershell -NoProfile -Command \"{ps}\"")
    print(r.stdout.strip())
