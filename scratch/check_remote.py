import os
import datetime

p = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템\VERSION"
if os.path.exists(p):
    with open(p, "r", encoding="utf-8") as f:
        print("DESKTOP_VERSION:", f.read().strip())
    print("DESKTOP_MTIME:", datetime.datetime.fromtimestamp(os.path.getmtime(p)))
else:
    print("DESKTOP_VERSION: NOT_FOUND")

ps1_pattern = os.path.join(os.environ.get("TEMP", ""), "run_updater_*.ps1")
import glob
ps1_files = glob.glob(ps1_pattern)
print("UPDATER_PS1_FILES:", ps1_files)
for f in ps1_files[-3:]:
    print("PS1:", f)
    try:
        with open(f, "r", encoding="utf-8-sig") as pf:
            print("--- CONTENT ---")
            print(pf.read())
            print("--- END ---")
    except Exception as e:
        print("Read error:", e)
