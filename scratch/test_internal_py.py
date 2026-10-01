import os
import sys
import subprocess

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
internal_py = os.path.join(app_dir, "python", "python.exe")

test_mutex_code = (
    "import sys, os\n"
    "sys.path.insert(0, r'" + app_dir + "')\n"
    "import run\n"
    "h1 = run._acquire_single_instance_mutex()\n"
    "print('FIRST_ACQUIRE:', h1 is not None)\n"
    "h2 = run._acquire_single_instance_mutex()\n"
    "print('SECOND_ACQUIRE:', h2 is None)\n"
)
res = subprocess.run([internal_py, "-c", test_mutex_code], capture_output=True, text=True, cwd=app_dir)
print("Internal Py Returncode:", res.returncode)
print("Internal Py Stdout:\n", res.stdout)
print("Internal Py Stderr:\n", res.stderr)
