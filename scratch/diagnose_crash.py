# -*- coding: utf-8 -*-
import subprocess
import base64

ps_script = """
$bat = "C:\\Users\\kksjmj\\AppData\\Local\\Temp\\run_updater_1790602220.bat"
if (Test-Path $bat) {
    Write-Output "=== BAT CONTENT ==="
    Get-Content $bat -Raw
}

Write-Output "`n=== PORT 8765 STATUS ==="
$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($c in $conn) {
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        Write-Output "PID: $($p.Id), Name: $($p.ProcessName), State: $($c.State)"
    }
} else {
    Write-Output "No listener on 8765"
}

Write-Output "`n=== STDERR FROM RUN.PY ==="
if (Test-Path "$env:TEMP\\backup_err.log") {
    Get-Content "$env:TEMP\\backup_err.log" -Tail 30
}
"""

b64 = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
proc = subprocess.run(['ssh', '100.90.20.59', 'powershell', '-NoProfile', '-EncodedCommand', b64], capture_output=True, text=True, timeout=20)
print(proc.stdout)
