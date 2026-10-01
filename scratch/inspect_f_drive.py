import os
import json

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
prof_path = os.path.join(app_dir, "data", "profiles.json")
if os.path.exists(prof_path):
    with open(prof_path, "r", encoding="utf-8") as f:
        profs = json.load(f)
    print(f"Total profiles: {len(profs)}")
    for p in profs:
        print("Profile ID:", p.get("id"))
        print("  Name:", p.get("name"))
        print("  Repo Dir:", p.get("repo_dir"))
        print("  Auto Backup:", p.get("auto_backup_enabled"))
        print("  Schedule:", p.get("schedule_type"), p.get("schedule_time"))
