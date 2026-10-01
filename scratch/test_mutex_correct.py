import os
import sys
import subprocess

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
internal_py = os.path.join(app_dir, "python", "python.exe")
out_file = os.path.join(os.environ.get("TEMP", ""), "mx_res.txt")
if os.path.exists(out_file):
    os.remove(out_file)

script_path = os.path.join(os.environ.get("TEMP", ""), "test_mx.py")
with open(script_path, "w", encoding="utf-8") as f:
    f.write(
        "import sys, os\n"
        f"sys.path.insert(0, r'{app_dir}')\n"
        "import run\n"
        "h1 = run.acquire_single_instance_mutex(is_silent=True, port=8765)\n"
        "h2 = run.acquire_single_instance_mutex(is_silent=True, port=8765)\n"
        f"with open(r'{out_file}', 'w') as out:\n"
        "    out.write(f'FIRST:{h1 is not None} SECOND_NONE:{h2 is None}')\n"
    )

res = subprocess.run([internal_py, script_path], capture_output=True, text=True, cwd=app_dir)
print("Internal Py Returncode:", res.returncode)
if os.path.exists(out_file):
    print("Result File Content:", open(out_file).read())
