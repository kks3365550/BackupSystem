# -*- coding: utf-8 -*-
import os
import re

base_dir = r"c:\Users\kksjmj\Desktop\ai\백업시스템"

# 1. VERSION
with open(os.path.join(base_dir, "VERSION"), "w", encoding="utf-8") as f:
    f.write("2.9.21\n")

# 2. core/__init__.py
p_init = os.path.join(base_dir, "core", "__init__.py")
if os.path.exists(p_init):
    c = open(p_init, "r", encoding="utf-8").read()
    c = re.sub(r"__version__\s*=\s*['\"][^'\"]+['\"]", "__version__ = '2.9.21'", c)
    open(p_init, "w", encoding="utf-8").write(c)

# 3. web/app.py
p_app = os.path.join(base_dir, "web", "app.py")
if os.path.exists(p_app):
    c = open(p_app, "r", encoding="utf-8").read()
    c = re.sub(r"VERSION\s*=\s*['\"][^'\"]+['\"]", "VERSION = '2.9.21'", c)
    open(p_app, "w", encoding="utf-8").write(c)

# 4. web/templates/index.html
p_html = os.path.join(base_dir, "web", "templates", "index.html")
if os.path.exists(p_html):
    c = open(p_html, "r", encoding="utf-8").read()
    c = re.sub(r"v2\.9\.\d+", "v2.9.21", c)
    open(p_html, "w", encoding="utf-8").write(c)

print("[+] All version references bumped to 2.9.21 successfully.")
