import os
import sys
import shutil
import subprocess
import tempfile
import base64

base_dir = os.path.abspath(os.path.dirname(__file__))
target_bat = os.path.join(base_dir, "start_backup_system.bat")
# 1. 대상 스크립트를 launch_dashboard.vbs로 변경하여 웹 UI가 열리도록 수정
start_vbs = os.path.join(base_dir, "launch_dashboard.vbs")

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

# 2. Create single unified .lnk shortcut
lnk_path = os.path.join(desktop, "백업시스템 대시보드.lnk")

def create_shortcut_via_com():
    """win32com.client를 사용하여 바로가기를 생성합니다."""
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(lnk_path)
    shortcut.TargetPath = "wscript.exe"
    shortcut.Arguments = f'"{start_vbs}"'
    shortcut.WorkingDirectory = base_dir
    shortcut.Description = "서버 & 시스템 백업 매니저 웹 대시보드"
    shortcut.IconLocation = "shell32.dll,259"
    shortcut.Save()
    return True

def create_shortcut_via_powershell():
    """PowerShell -EncodedCommand를 사용하여 인코딩 문제를 방지하며 바로가기를 생성합니다."""
    ps_script = f"""
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop '백업시스템 대시보드.lnk'
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($lnkPath)
$shortcut.TargetPath = 'wscript.exe'
$shortcut.Arguments = '"{start_vbs}"'
$shortcut.WorkingDirectory = '{base_dir}'
$shortcut.Description = '서버 & 시스템 백업 매니저 웹 대시보드'
$shortcut.IconLocation = 'shell32.dll,259'
$shortcut.Save()
"""
    encoded_cmd = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
    
    kwargs = {"check": True}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_cmd], **kwargs)
    return True

try:
    try:
        create_shortcut_via_com()
    except Exception:
        create_shortcut_via_powershell()
except Exception as e:
    print(f"오류: 바로가기 생성 실패 - {e}")
    sys.exit(1)

print("성공: 바탕화면에 '백업시스템 대시보드' 바로가기를 생성했습니다.")


