# -*- coding: utf-8 -*-
import subprocess
import sys

cmd = (
    'powershell -NoProfile -Command "'
    '$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like \'*백업시스템*\' }; '
    'if ($procs) { foreach ($p in $procs) { Write-Host $p.ProcessId : $p.Name } } else { Write-Host No backup process }'
    '"'
)
res = subprocess.run(["ssh", "-o", "BatchMode=yes", "kksjmj@100.90.20.59", cmd], capture_output=True)
sys.stdout.buffer.write(b"STDOUT:\n" + res.stdout + b"\n")
