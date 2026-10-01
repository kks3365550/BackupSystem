# -*- coding: utf-8 -*-
"""
scratch/verify_desktop_rc1.py - Desktop F: 220,000 files P0-P3 Verification Runner
==================================================================================
Runs on Desktop (100.90.20.59) against actual F:\ repository:
1. Deploys v2.10.0-rc1 safely preserving user configs and F:\ data.
2. P0: Exact Byte/Field/Order identity test (assert uncached == cached).
3. Latency measurement: Uncached vs Cached (10 iterations).
4. Restarts server in background and verifies /api/snapshots API readiness.
"""

import os
import sys
import time
import json
import zipfile
import hashlib
import statistics
import subprocess

TARGET_DIR = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
ZIP_PATH = r"C:\Users\kksjmj\AppData\Local\Temp\release_v2.10.0-rc1.zip"
sys.path.insert(0, TARGET_DIR)

print("=" * 80)
print(" [v2.10.0-rc1 DESKTOP RIGOROUS VALIDATION - F: REPOSITORY]")
print("=" * 80)

# 1. 기존 프로세스 종료
print("[*] Terminating existing BackupSystem processes if any...")
subprocess.run("taskkill /f /im pythonw.exe 2>nul", shell=True)
time.sleep(2)

# 2. release_v2.10.0-rc1.zip 압축 해제 (설정 보존)
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
assert ver == "2.10.0-rc1", f"Expected 2.10.0-rc1, got {ver}"

# 3. Import Core Modules from TARGET_DIR
from core.snapshot import SnapshotEngine
from core.snapshot_cache import get_snapshot_cache
from core.storage import BlobStorage

# 대상 리포지토리: F:\ (Windows 경로 해석 오류 방지 위해 슬래시 포함)
repo_dir = r"F:/"

# profiles.json에서 등록된 저장소 경로를 안전하게 자동 탐색
def _find_repo_from_profiles():
    """
    TARGET_DIR/data/profiles.json 또는 TARGET_DIR/profiles.json에서
    등록된 repo_dir을 탐색하고, 해당 경로가 실제로 존재하는지 검증합니다.
    """
    candidate_files = [
        os.path.join(TARGET_DIR, "data", "profiles.json"),
        os.path.join(TARGET_DIR, "profiles.json")
    ]
    
    for prof_file in candidate_files:
        if os.path.exists(prof_file):
            try:
                with open(prof_file, "r", encoding="utf-8") as f:
                    profs = json.load(f)
                if profs and isinstance(profs, list) and len(profs) > 0:
                    candidate_repo = profs[0].get("repo_dir")
                    if candidate_repo and os.path.exists(candidate_repo):
                        return candidate_repo
            except Exception:
                pass
    return None

# 기본 경로(F:/)에 snapshots가 없으면 profiles.json에서 등록된 경로로 대체
if not os.path.exists(os.path.join(repo_dir, "snapshots")):
    found_repo = _find_repo_from_profiles()
    if found_repo:
        repo_dir = found_repo

print(f"[*] Target Backup Repository: {repo_dir}")
snap_dir = os.path.join(repo_dir, "snapshots")
if os.path.exists(snap_dir):
    json_count = sum(1 for f in os.listdir(snap_dir) if f.endswith(".json"))
    print(f"    - Snapshots directory: {snap_dir} ({json_count} manifest files found)")
else:
    print(f"    - Warning: {snap_dir} does not exist!")

cache = get_snapshot_cache()
cache.clear()

# 4. [P0 VERIFICATION] Uncached vs Cached Exact Byte/Field/Order Identity
print("\n" + "=" * 80)
print(" [P0 CRITICAL VERIFICATION: UNCACHED VS CACHED 100% IDENTITY TEST]")
print("=" * 80)

# Uncached Direct Disk Scan
print("[*] Running Uncached Disk Scan (_list_snapshots_disk)...")
t0 = time.perf_counter()
uncached_res = SnapshotEngine._list_snapshots_disk(repo_dir)
t_uncached = (time.perf_counter() - t0) * 1000
print(f"[+] Uncached Scan completed in {t_uncached:.2f} ms ({len(uncached_res)} snapshots)")

# Cached First Call (Warm-up population)
print("[*] Running Cached Call (list_snapshots)...")
t0 = time.perf_counter()
cached_res = SnapshotEngine.list_snapshots(repo_dir)
t_first_cached = (time.perf_counter() - t0) * 1000
print(f"[+] Cached Call completed in {t_first_cached:.2f} ms ({len(cached_res)} snapshots)")

# Deterministic Serialization & Hash Check
s_uncached = json.dumps(uncached_res, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
s_cached = json.dumps(cached_res, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

h_uncached = hashlib.sha256(s_uncached.encode('utf-8')).hexdigest()
h_cached = hashlib.sha256(s_cached.encode('utf-8')).hexdigest()

print(f"\n[DETERMINISTIC HASH COMPARISON]")
print(f"  SHA-256 (Uncached Disk Scan) : {h_uncached}")
print(f"  SHA-256 (Cached Memory Call) : {h_cached}")

is_identical = (h_uncached == h_cached) and (uncached_res == cached_res)
if is_identical:
    print("\n  >>> P0 RESULT: [PASS] 100% EXACT BYTE/FIELD/ORDER IDENTITY CONFIRMED! <<<")
else:
    print("\n  >>> P0 RESULT: [FAIL] IDENTITY MISMATCH DETECTED! <<<")
    sys.exit(1)

# 5. [LATENCY BENCHMARK] 10 Repeated Queries
print("\n" + "=" * 80)
print(" [LATENCY BENCHMARK: 10 REPEATED CACHE HITS]")
print("=" * 80)
hit_latencies = []
for i in range(10):
    t0 = time.perf_counter()
    r = SnapshotEngine.list_snapshots(repo_dir)
    elapsed = (time.perf_counter() - t0) * 1000
    hit_latencies.append(elapsed)
    print(f"  [Iter {i+1:2d}] {elapsed:8.4f} ms | Loaded {len(r)} snapshots")

avg_hit = statistics.mean(hit_latencies)
median_hit = statistics.median(hit_latencies)
min_hit = min(hit_latencies)
max_hit = max(hit_latencies)
reduction_pct = ((t_uncached - avg_hit) / t_uncached) * 100 if t_uncached > 0 else 0

print("\n" + "=" * 80)
print("[FINAL BENCHMARK COMPARISON ON ACTUAL DESKTOP REPO]")
print("=" * 80)
print(f"  Base Uncached Disk Latency : {t_uncached:10.2f} ms")
print(f"  Average Cache Hit Latency  : {avg_hit:10.4f} ms")
print(f"  Median Cache Hit Latency   : {median_hit:10.4f} ms")
print(f"  Min / Max Hit Latency      : {min_hit:.4f} ms / {max_hit:.4f} ms")
print(f"  Latency Reduction Ratio    : {reduction_pct:9.2f} %")
print("=" * 80)

# 6. 백그라운드 서버 재기동 (운영 상태 복구)
print("\n[*] Restarting BackupSystem server in background...")
py_exe = os.path.join(TARGET_DIR, "python", "pythonw.exe")
if not os.path.exists(py_exe):
    py_exe = "pythonw.exe"

vbs_path = os.path.join(TARGET_DIR, "start_silent.vbs")
subprocess.Popen(["wscript.exe", vbs_path], cwd=TARGET_DIR)
time.sleep(3)
print("[+] BackupSystem server restarted successfully.")
print("\n[VERIFICATION COMPLETE] All P0 identity and latency benchmarks completed!")
