# -*- coding: utf-8 -*-
import subprocess
import time

cmd = 'start /wait C:\\Users\\kksjmj\\Downloads\\BackupSystem_Setup_v2.9.20.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="C:\\Users\\kksjmj\\Downloads\\install_progfiles.log"'
print("Running official installer on desktop...")
res = subprocess.run(["ssh", "-o", "BatchMode=yes", "kksjmj@100.90.20.59", cmd], capture_output=True, text=True)
print("Exit:", res.returncode)
time.sleep(3)

# Check Version in Program Files
res_ver = subprocess.run(["ssh", "-o", "BatchMode=yes", "kksjmj@100.90.20.59", 'type "C:\\Program Files\\백업시스템\\VERSION"'], capture_output=True, text=True)
print("VERSION in Program Files:", res_ver.stdout.strip())
