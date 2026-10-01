import os
import subprocess
import time
import psutil

# Kill tabby main.py
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = " ".join(p.info['cmdline'] or [])
        if "tabbyapi" in cmd.lower() and "main.py" in cmd.lower():
            print("Killing Tabby PID:", p.info['pid'])
            p.kill()
    except Exception:
        pass

time.sleep(2)

# Start Tabby via start_tabby_task.bat or pythonw
bat_path = r"C:\Users\kksjmj\tabbyAPI\start_tabby_task.bat"
if os.path.exists(bat_path):
    print("Restarting Tabby via bat...")
    subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=r"C:\Users\kksjmj\tabbyAPI")

print("Done. Waiting 10s for startup...")
time.sleep(10)
