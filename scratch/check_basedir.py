# -*- coding: utf-8 -*-
import subprocess
import base64

ps_script = """
$py = "C:\\Program Files\\백업시스템\\python\\python.exe"
$out = & $py -c "import os; BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); print(repr(BASE_DIR))"
Write-Output "PYTHON_REPR: $out"
"""

b64 = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
proc = subprocess.run(['ssh', '100.90.20.59', 'powershell', '-NoProfile', '-EncodedCommand', b64], capture_output=True, text=True, timeout=15)
with open('scratch/res2.txt', 'w', encoding='utf-8') as f:
    f.write(proc.stdout)
print("CHECKED")
