import re

# 1. VERSION
with open("VERSION", "w", encoding="utf-8") as f:
    f.write("2.9.22\n")

# 2. core/__init__.py
p = "core/__init__.py"
content = open(p, "r", encoding="utf-8").read()
content = re.sub(r'__version__\s*=\s*"[^"]+"', '__version__ = "2.9.22"', content)
open(p, "w", encoding="utf-8").write(content)

# 3. web/app.py
p = "web/app.py"
content = open(p, "r", encoding="utf-8").read()
content = re.sub(r'version="[^"]+"', 'version="2.9.22"', content, count=1)
open(p, "w", encoding="utf-8").write(content)

# 4. web/templates/index.html
p = "web/templates/index.html"
content = open(p, "r", encoding="utf-8").read()
content = content.replace("v2.9.21", "v2.9.22").replace("2.9.21", "2.9.22")
open(p, "w", encoding="utf-8").write(content)

# 5. installer/BackupSystem.iss
p = "installer/BackupSystem.iss"
content = open(p, "r", encoding="utf-8").read()
content = re.sub(r'#define MyAppVersion "[^"]+"', '#define MyAppVersion "2.9.22"', content)
open(p, "w", encoding="utf-8").write(content)

print("[PASS] Bumped all versions to 2.9.22 successfully!")
