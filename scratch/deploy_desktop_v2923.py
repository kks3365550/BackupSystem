import os
import sys
import time
import zipfile
import shutil
import subprocess
import urllib.request
import json
import statistics

TARGET_DIR = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
ZIP_PATH = r"C:\Users\kksjmj\AppData\Local\Temp\release_v2.9.23.zip"

print("=" * 60)
print("[*] Starting v2.9.23 Deployment & Verified Benchmark on Desktop")
print("=" * 60)

# 1. 기존 프로세스 확인 및 종료
print("[*] Terminating existing BackupSystem processes if any...")
subprocess.run("taskkill /f /im pythonw.exe 2>nul", shell=True)
time.sleep(2)

# 2. 압축 해제 및 덮어쓰기
print(f"[*] Extracting {ZIP_PATH} to {TARGET_DIR}...")
skip_files = {"profiles.json", "auth_config.json", "app_settings.json", "metadata.db"}

with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    for member in zf.infolist():
        target_path = os.path.join(TARGET_DIR, member.filename)
        base_name = os.path.basename(member.filename)
        if base_name in skip_files and os.path.exists(target_path):
            continue
        zf.extract(member, TARGET_DIR)

v_file = os.path.join(TARGET_DIR, "VERSION")
with open(v_file, "r", encoding="utf-8") as f:
    ver = f.read().strip()
print(f"[+] Deployed version verified: {ver}")
assert ver == "2.9.23", f"Expected 2.9.23, got {ver}"

# 3. 임베디드 파이썬 바이너리 확인
py_exe = os.path.join(TARGET_DIR, "python", "pythonw.exe")
if not os.path.exists(py_exe):
    py_exe = os.path.join(TARGET_DIR, "python", "python.exe")
if not os.path.exists(py_exe):
    py_exe = "pythonw.exe"
print(f"[*] Using Python binary: {py_exe}")

# 4. PowerShell Start-Process로 세션 분리 독립 백그라운드 기동
print("[*] Launching BackupSystem via PowerShell Start-Process...")
log_stdout = os.path.join(TARGET_DIR, "logs", "server_stdout.log")
log_stderr = os.path.join(TARGET_DIR, "logs", "server_stderr.log")
os.makedirs(os.path.join(TARGET_DIR, "logs"), exist_ok=True)

ps_cmd = f"""
$proc = Start-Process -FilePath "{py_exe}" `
                      -ArgumentList "run.py", "--silent" `
                      -WorkingDirectory "{TARGET_DIR}" `
                      -WindowStyle Hidden `
                      -RedirectStandardOutput "{log_stdout}" `
                      -RedirectStandardError "{log_stderr}" `
                      -PassThru;
Write-Output $proc.Id
"""
res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
print(f"[+] Process spawned with PID: {res.stdout.strip()}")

# 5. 서버 8765 LISTEN 대기 (최대 20초)
url = "http://127.0.0.1:8765/api/snapshots"
print("[*] Waiting for server readiness on 127.0.0.1:8765...")
ready = False
for attempt in range(40):
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            if resp.status == 200:
                ready = True
                print(f"[+] Server is READY! (took ~{(attempt + 1) * 0.5:.1f}s)")
                break
    except Exception:
        time.sleep(0.5)

if not ready:
    print("[-] Server failed to respond within 20 seconds. Checking logs:")
    startup_err = os.path.join(TARGET_DIR, "logs", "startup_error.log")
    if os.path.exists(startup_err):
        print(f"--- startup_error.log ---\n{open(startup_err, 'r', encoding='utf-8', errors='replace').read()}")
    if os.path.exists(log_stderr):
        print(f"--- STDERR ---\n{open(log_stderr, 'r', encoding='utf-8', errors='replace').read()}")
    sys.exit(1)

# 6. 정밀 레이턴시 측정 (10 Iterations)
print("\n[*] Measuring Verified Latency for /api/snapshots (10 iterations)...")
latencies = []
snap_count = 0

for i in range(10):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
            snap_count = len(data)
            print(f"    - Iteration {i+1}: {elapsed_ms:.2f} ms ({snap_count} snapshots)")
    except Exception as e:
        print(f"    - Iteration {i+1} ERROR: {e}")
    time.sleep(0.1)

print("\n" + "=" * 60)
print("[VERIFIED BENCHMARK RESULTS]")
print("=" * 60)
if latencies:
    print(f"Total Snapshots Loaded : {snap_count}")
    print(f"Min Latency            : {min(latencies):.2f} ms")
    print(f"Max Latency            : {max(latencies):.2f} ms")
    print(f"Average Latency        : {statistics.mean(latencies):.2f} ms")
    print(f"Median Latency         : {statistics.median(latencies):.2f} ms")
    print(f"Std Deviation          : {statistics.stdev(latencies):.2f} ms")
print("=" * 60)
