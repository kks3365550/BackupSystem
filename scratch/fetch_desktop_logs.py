# -*- coding: utf-8 -*-
import subprocess
import base64

ps_script = """
$ps1s = Get-ChildItem "$env:TEMP\\run_updater*.ps1" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
foreach ($p in $ps1s) {
    Write-Output "=== FILE: $($p.FullName) (Time: $($p.LastWriteTime)) ==="
    Get-Content $p.FullName -Raw
}
"""

b64 = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
proc = subprocess.run(['ssh', '100.90.20.59', 'powershell', '-NoProfile', '-EncodedCommand', b64], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
with open('scratch/res.txt', 'w', encoding='utf-8') as f:
    f.write(proc.stdout)
print("SUCCESS")
