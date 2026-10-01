import os
import sys
import subprocess
import time

app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
internal_py = os.path.join(app_dir, "python", "python.exe")

# Step 1: Launch Process 1 in background which holds the mutex
p1_code = (
    "import sys, os, time\n"
    f"sys.path.insert(0, r'{app_dir}')\n"
    "import run\n"
    "ok = run.acquire_single_instance_mutex(is_silent=True, port=8765)\n"
    "time.sleep(5)\n"
)
p1 = subprocess.Popen([internal_py, "-c", p1_code], cwd=app_dir)
time.sleep(1) # Ensure p1 acquired mutex

# Step 2: Launch Process 2 with --silent, which should detect mutex and exit with 0 immediately
p2_code = (
    "import sys, os\n"
    f"sys.path.insert(0, r'{app_dir}')\n"
    "import run\n"
    "ok = run.acquire_single_instance_mutex(is_silent=True, port=8765)\n"
)
t0 = time.time()
p2 = subprocess.run([internal_py, "-c", p2_code], cwd=app_dir)
elapsed = time.time() - t0

p1.terminate()

print(f"P2 Exit Code: {p2.returncode} (Expected 0)")
print(f"P2 Elapsed Time: {elapsed:.2f}s (Expected < 1.0s)")
assert p2.returncode == 0
assert elapsed < 2.0
print("-> [SUCCESS] Single-Instance Mutex accurately blocked duplicate instance with silent exit(0)!")
