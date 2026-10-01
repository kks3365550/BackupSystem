import os

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
log_file = os.path.join(app_dir, "logs", "server.log")
if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        print(f"Total lines in server.log: {len(lines)}")
        for l in lines[-30:]:
            print(l.rstrip())
else:
    print("server.log not found!")
