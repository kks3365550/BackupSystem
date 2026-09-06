import os
import subprocess
import tempfile

vbs = r'''
Set sh = CreateObject("WScript.Shell")
desktop = sh.SpecialFolders("Desktop")
Set lnk = sh.CreateShortcut(desktop & "\백업시스템 대시보드.lnk")
lnk.TargetPath = "C:\Users\kksjmj\Desktop\ai\백업시스템\start_backup_system.bat"
lnk.WorkingDirectory = "C:\Users\kksjmj\Desktop\ai\백업시스템"
lnk.Description = "서버 & 시스템 백업 매니저 웹 대시보드"
lnk.IconLocation = "shell32.dll,259"
lnk.Save
'''

tmp = os.path.join(tempfile.gettempdir(), "make_shortcut.vbs")
with open(tmp, "w", encoding="cp949") as f:
    f.write(vbs.strip())

subprocess.run(["cscript", "//nologo", tmp], check=True)
if os.path.exists(tmp):
    os.remove(tmp)
print("성공: 바탕화면에 '백업시스템 대시보드.lnk' 바로가기를 생성했습니다.")
