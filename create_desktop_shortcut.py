import os
import shutil
import subprocess
import tempfile

base_dir = os.path.abspath(os.path.dirname(__file__))
target_bat = os.path.join(base_dir, "start_backup_system.bat")
start_vbs = os.path.join(base_dir, "start_silent.vbs")

# 1. Desktop paths
desktop = os.path.join(os.path.expanduser("~"), "Desktop")

# Remove any old corrupted shortcuts
if os.path.exists(desktop):
    for f in os.listdir(desktop):
        if (f.endswith(".lnk") or f.endswith(".url")) and any(c in f for c in ["\ufffd", "ý", "ú", "백업시스템"]):
            try:
                os.remove(os.path.join(desktop, f))
            except Exception:
                pass

# 2. Create high-reliability Web URL shortcut
url_path = os.path.join(desktop, "백업시스템 대시보드.url")
url_content = """[InternetShortcut]
URL=http://127.0.0.1:8765
IconIndex=259
IconFile=C:\\Windows\\System32\\shell32.dll
"""
with open(url_path, "w", encoding="utf-8") as f:
    f.write(url_content)

# 3. Create .lnk batch shortcut via VBS
lnk_path = os.path.join(desktop, "백업시스템 대시보드.lnk")
vbs = f'''
Set sh = CreateObject("WScript.Shell")
Set lnk = sh.CreateShortcut("{lnk_path}")
lnk.TargetPath = "{target_bat}"
lnk.WorkingDirectory = "{base_dir}"
lnk.Description = "서버 & 시스템 백업 매니저 웹 대시보드"
lnk.IconLocation = "shell32.dll,259"
lnk.Save
'''
tmp = os.path.join(tempfile.gettempdir(), "make_shortcut.vbs")
with open(tmp, "w", encoding="utf-16") as f:
    f.write(vbs.strip())

try:
    subprocess.run(["cscript", "//nologo", tmp], check=True)
finally:
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except Exception:
            pass

# 4. Register in Windows Startup folder so dashboard daemon runs on boot automatically!
startup_folder = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
if os.path.exists(startup_folder) and os.path.exists(start_vbs):
    shutil.copy2(start_vbs, os.path.join(startup_folder, "start_backup_daemon.vbs"))

print("성공: 바탕화면에 '백업시스템 대시보드' 바로가기 및 부팅 시 자동실행 등록을 완료했습니다.")


