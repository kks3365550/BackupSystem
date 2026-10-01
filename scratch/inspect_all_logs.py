import os

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
log_dir = os.path.join(app_dir, "logs")
if os.path.exists(log_dir):
    print("Files in logs:", os.listdir(log_dir))
    for f in os.listdir(log_dir):
        fp = os.path.join(log_dir, f)
        if os.path.isfile(fp):
            print(f"=== {f} ({os.path.getsize(fp)} bytes) ===")
            try:
                content = open(fp, "r", encoding="utf-8", errors="replace").read()
                print(content[-500:])
            except Exception as e:
                print("Read error:", e)
else:
    print("logs directory does not exist!")
