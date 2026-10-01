import os

updater_file = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템\core\updater.py"
if os.path.exists(updater_file):
    with open(updater_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        for idx in range(355, min(430, len(lines))):
            print(f"{idx+1:03d}: {lines[idx].rstrip()}")
