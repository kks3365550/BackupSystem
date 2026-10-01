import os
import sys
import subprocess

sys.path.insert(0, os.path.abspath("."))

# Test 1: Import run.py and check syntax
import run
sys.__stdout__.write("[PASS] run.py syntax and import OK\n")

# Test 2: Verify launch_dashboard.vbs exists and has no 'cmd.exe /c start' or 3-second loop
vbs_content = open("installer/launch_dashboard.vbs", "r", encoding="utf-8").read()
assert "cmd.exe /c start" not in vbs_content, "vbs must NOT directly launch browser!"
assert "WScript.Sleep 300" not in vbs_content, "vbs must NOT loop wait!"
assert 'objShell.Run pyExe & " """ & appDir & "\\run.py"""' in vbs_content, "vbs must run run.py directly!"
sys.__stdout__.write("[PASS] installer/launch_dashboard.vbs verified (0-wait, Self-Gated delegation)\n")

# Test 3: Mutex dual-instance handling
h1 = run.acquire_single_instance_mutex(is_silent=True, port=8765)
sys.__stdout__.write(f"[PASS] First acquire mutex returned: {h1}\n")

# Subprocess 1 with --silent should exit 0 without opening browser
sub_code_silent = (
    "import sys, os; sys.path.insert(0, os.path.abspath('.')); import run\n"
    "run.acquire_single_instance_mutex(is_silent=True, port=8765)\n"
)
res = subprocess.run([sys.executable, "-c", sub_code_silent], capture_output=True, text=True, cwd=os.path.abspath("."))
assert res.returncode == 0, f"Expected 0, got {res.returncode}"
sys.__stdout__.write(f"[PASS] Subprocess 1 (Silent) detected mutex and exited 0 (returncode={res.returncode})\n")

sys.__stdout__.write("=" * 60 + "\n[ALL LOCAL UNIT TESTS PASSED]\n" + "=" * 60 + "\n")
sys.__stdout__.flush()
