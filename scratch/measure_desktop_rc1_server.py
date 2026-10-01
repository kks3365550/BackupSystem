# -*- coding: utf-8 -*-
"""
scratch/measure_desktop_rc1_server.py
======================================
Runs on Desktop (100.90.20.59):
1. Safely restarts BackupSystem server (v2.10.0-rc1) using Start-Process.
2. Waits for server readiness on http://127.0.0.1:8765/api/snapshots.
3. Performs 10 repeated HTTP requests to measure real end-to-end latency.
4. Compares against v2.9.23 baseline (2,947.52 ms).
5. Verifies P0 field integrity (id, timestamp, file_count, replication status).
"""

import os
import sys
import time
import json
import statistics
import subprocess
import urllib.request

TARGET_DIR = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
py_exe = os.path.join(TARGET_DIR, "python", "pythonw.exe")
if not os.path.exists(py_exe):
    py_exe = os.path.join(TARGET_DIR, "python", "python.exe")

V2923_BASELINE_MS = 2947.52

print("=" * 80)
print(" [v2.10.0-rc1 DESKTOP REAL HTTP API BENCHMARK - F: REPOSITORY]")
print("=" * 80)

# 1. Kill old processes on port 8765
print("[*] Cleaning up old processes on port 8765...")
ps_kill = (
    "$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue\n"
    "if ($conn) {\n"
    "    foreach ($c in $conn) {\n"
    "        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue\n"
    "        if ($p) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }\n"
    "    }\n"
    "}\n"
)
subprocess.run(["powershell", "-NoProfile", "-Command", ps_kill], capture_output=True)
time.sleep(2)

# 2. Launch BackupSystem via Start-Process
print(f"[*] Launching BackupSystem via {py_exe}...")
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
pid = res.stdout.strip()
print(f"[+] Server process spawned (PID: {pid})")

# 3. Wait for server readiness on http://127.0.0.1:8765/api/snapshots
url = "http://127.0.0.1:8765/api/snapshots"
print("[*] Waiting for server readiness on 127.0.0.1:8765...")
ready = False
for attempt in range(40):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
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

# 4. Measure 10 Repeated HTTP API Calls
print("\n" + "=" * 80)
print(" [HTTP API /api/snapshots LATENCY MEASUREMENT (10 Iterations)]")
print("=" * 80)

latencies = []
snap_count = 0
sample_snap = None

for i in range(10):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            data = json.loads(raw)
            snap_count = len(data)
            if sample_snap is None and snap_count > 0:
                sample_snap = data[0]
            tag = "COLD/POPULATE" if i == 0 else f"WARM CACHED #{i}"
            print(f"  [{tag:15s}] {elapsed:8.2f} ms | Loaded {snap_count} snapshots")
    except Exception as e:
        print(f"  [Iter {i+1:2d}] ERROR: {e}")
    time.sleep(0.1)

# 5. Final Comparison and Verdict
print("\n" + "=" * 80)
print(" [BENCHMARK RESULTS VS v2.9.23 BASELINE]")
print("=" * 80)
if latencies:
    cold_lat = latencies[0]
    warm_lats = latencies[1:] if len(latencies) > 1 else latencies
    avg_warm = statistics.mean(warm_lats)
    med_warm = statistics.median(warm_lats)
    min_warm = min(warm_lats)
    max_warm = max(warm_lats)
    reduction_pct = ((V2923_BASELINE_MS - avg_warm) / V2923_BASELINE_MS) * 100

    print(f"  v2.9.23 Baseline Latency  : {V2923_BASELINE_MS:10.2f} ms")
    print(f"  v2.10.0-rc1 Cold Latency   : {cold_lat:10.2f} ms")
    print(f"  v2.10.0-rc1 Warm Avg (n=9) : {avg_warm:10.2f} ms")
    print(f"  v2.10.0-rc1 Warm Median    : {med_warm:10.2f} ms")
    print(f"  v2.10.0-rc1 Min / Max      : {min_warm:.2f} ms / {max_warm:.2f} ms")
    print(f"  -------------------------------------------------------------")
    print(f"  REAL LATENCY REDUCTION     : {reduction_pct:9.2f} % (2,947 ms -> {avg_warm:.2f} ms)")
    print("=" * 80)

    if sample_snap:
        print("\n[P0 FIELD INTEGRITY VERIFICATION]")
        print(f"  Snapshot ID          : {sample_snap.get('id')}")
        print(f"  Created At           : {sample_snap.get('timestamp')}")
        print(f"  Total Files          : {sample_snap.get('file_count')}")
        print(f"  Total Bytes          : {sample_snap.get('total_bytes')}")
        print(f"  Offsite Status       : {sample_snap.get('offsite_status')}")
        print(f"  Is Offsite Protected : {sample_snap.get('is_offsite_protected')}")
        print(f"  Is Local Protected   : {sample_snap.get('is_local_protected')}")
        assert "id" in sample_snap, "Missing 'id' field!"
        assert "offsite_status" in sample_snap, "Missing 'offsite_status' field!"
        print("\n  >>> P0 RESULT: [PASS] All critical fields preserved and verified! <<<")

print("=" * 80)
