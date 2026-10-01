import os
import sys
import subprocess

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
py_candidates = [
    os.path.join(app_dir, "python", "python.exe"),
    os.path.join(app_dir, "python", "pythonw.exe"),
    sys.executable
]
for p in py_candidates:
    print(f"Candidate: {p} (exists={os.path.exists(p)})")

test_mutex_code = (
    "import sys, os\n"
    "sys.path.insert(0, r'" + app_dir + "')\n"
    "try:\n"
    "    import run\n"
    "    h1 = run._acquire_single_instance_mutex()\n"
    "    print('FIRST_ACQUIRE:', h1 is not None)\n"
    "    h2 = run._acquire_single_instance_mutex()\n"
    "    print('SECOND_ACQUIRE:', h2 is None)\n"
    "except Exception as e:\n"
    "    print('MUTEX_ERR:', e)\n"
)
res = subprocess.run([sys.executable, "-c", test_mutex_code], capture_output=True, text=True)
print("Returncode:", res.returncode)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)
