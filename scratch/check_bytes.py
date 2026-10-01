import os

p = r"C:\Users\kksjmj\AppData\Local\Temp\execute_desktop_ota.py"
if os.path.exists(p):
    with open(p, "rb") as f:
        data = f.read()
    print("execute_desktop_ota size:", len(data))
    for line in data.splitlines()[:25]:
        if b"app_dir" in line:
            print("RAW LINE:", line)
            print("DECODED CP949:", line.decode("cp949", errors="replace"))
            print("DECODED UTF8 :", line.decode("utf-8", errors="replace"))

ps1_path = r"C:\Users\kksjmj\AppData\Local\Temp\run_updater_1790777421.ps1"
if os.path.exists(ps1_path):
    with open(ps1_path, "rb") as f:
        ps1_data = f.read()
    print("PS1 size:", len(ps1_data))
    for line in ps1_data.splitlines():
        if b"robocopy" in line:
            print("PS1 RAW:", line)
            print("PS1 UTF8:", line.decode("utf-8", errors="replace"))
            print("PS1 CP949:", line.decode("cp949", errors="replace"))
