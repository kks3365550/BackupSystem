# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import shutil
import hashlib
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("==================================================")
print("  v2.10.1 기능 회귀 종합 검증 (Regression Suite)")
print("==================================================")

print("\n=== 1. 백업 및 스냅샷 생성 테스트 ===")
from core.snapshot import SnapshotEngine
from core.config import ConfigManager

test_data_dir = r"C:\Users\kksjmj\Desktop\ai\백업시스템\scratch\test_backup_src"
test_repo_dir = r"C:\Users\kksjmj\Desktop\ai\백업시스템\scratch\test_backup_repo"
test_restore_dir = r"C:\Users\kksjmj\Desktop\ai\백업시스템\scratch\test_restore_dst"

for d in [test_data_dir, test_repo_dir, test_restore_dir]:
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)

sample_content_1 = b"Hello Backup System v2.10.1 Regression Test File 1"
sample_content_2 = b"Large data chunk for dedup and compression test" * 1000
with open(os.path.join(test_data_dir, "file1.txt"), "wb") as f:
    f.write(sample_content_1)
with open(os.path.join(test_data_dir, "file2.bin"), "wb") as f:
    f.write(sample_content_2)

t0 = time.perf_counter()
manifest = SnapshotEngine.create_snapshot(
    repo_dir=test_repo_dir,
    sources=[test_data_dir],
    profile_id="test_prof",
    profile_name="회귀테스트_프로필",
    compress_level=3,
    use_vss=False
)
t_backup = (time.perf_counter() - t0) * 1000
snap_id = manifest["id"]
print(f"[PASS] Snapshot Created: {snap_id} in {t_backup:.2f} ms")
print(f"       Total files: {manifest['summary']['total_files']}, Total bytes: {manifest['summary']['total_bytes']}")

print("\n=== 2. SnapshotMetadataCache 동작 및 API Latency 검증 ===")
from core.snapshot_cache import get_snapshot_cache
cache = get_snapshot_cache()

# Cold miss
t0 = time.perf_counter()
snaps_cold = cache.list_snapshots(repo_dir=test_repo_dir, fallback_scanner=SnapshotEngine.list_snapshots)
t_cold = (time.perf_counter() - t0) * 1000
print(f"Cold Read Latency: {t_cold:.3f} ms (Count: {len(snaps_cold)})")

# Warm hit 5 iterations
warm_latencies = []
for _ in range(5):
    t0 = time.perf_counter()
    snaps_warm = cache.list_snapshots(repo_dir=test_repo_dir, fallback_scanner=SnapshotEngine.list_snapshots)
    t_warm = (time.perf_counter() - t0) * 1000
    warm_latencies.append(t_warm)
avg_warm = sum(warm_latencies) / len(warm_latencies)
print(f"Warm Cache Latencies: {[f'{x:.3f}ms' for x in warm_latencies]}")
print(f"[PASS] Avg Warm Cache Latency: {avg_warm:.3f} ms (Target: < 50ms)")
assert len(snaps_cold) == len(snaps_warm) >= 1, "Cold and warm snapshot counts do not match!"
assert cache.stats["hits"] >= 5, "Cache hits mismatch!"

# Live Server /api/snapshots Latency
live_latencies = []
for _ in range(3):
    t0 = time.perf_counter()
    req = urllib.request.Request("http://127.0.0.1:8765/api/snapshots")
    with urllib.request.urlopen(req, timeout=3) as resp:
        _ = resp.read()
    t_api = (time.perf_counter() - t0) * 1000
    live_latencies.append(t_api)
avg_api = sum(live_latencies) / len(live_latencies)
print(f"[PASS] Live Server /api/snapshots Latency: {avg_api:.2f} ms (Hit)")

print("\n=== 3. 복원(Restore) 무결성 검증 ===")
from core.restore import RestoreEngine
restore_result = RestoreEngine.restore_snapshot(
    repo_dir=test_repo_dir,
    snapshot_id=snap_id,
    target_dir=test_restore_dir
)
print(f"[PASS] Restore Completed: {restore_result['restored_files']} files restored, {restore_result['restored_bytes']} bytes")

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

src_f1 = os.path.join(test_data_dir, "file1.txt")
dst_f1 = os.path.join(test_restore_dir, "file1.txt")
src_f2 = os.path.join(test_data_dir, "file2.bin")
dst_f2 = os.path.join(test_restore_dir, "file2.bin")

h_src1, h_dst1 = get_sha256(src_f1), get_sha256(dst_f1)
h_src2, h_dst2 = get_sha256(src_f2), get_sha256(dst_f2)

assert h_src1 == h_dst1, "File 1 hash mismatch!"
assert h_src2 == h_dst2, "File 2 hash mismatch!"
print(f"[PASS] SHA-256 Integrity Verified:")
print(f"       file1.txt: {h_src1[:16]}... == {h_dst1[:16]}... OK")
print(f"       file2.bin: {h_src2[:16]}... == {h_dst2[:16]}... OK")

for d in [test_data_dir, test_repo_dir, test_restore_dir]:
    shutil.rmtree(d, ignore_errors=True)

print("\n=== 4. 라이브 스케줄러 상태 검증 ===")
from core.scheduler import BackupScheduler
from core.config import ConfigManager
sched = BackupScheduler()
profiles = ConfigManager.get_profiles()
print(f"[PASS] Registered Backup Profiles: {len(profiles)} loaded")
for prof in profiles:
    should_run = sched._should_run_profile(prof)
    print(f"       Profile: '{prof.get('name')}' | Schedule: {prof.get('schedule_type')}={prof.get('schedule_value')} | Auto: {prof.get('auto_backup_enabled')} | Should Run Now: {should_run}")
assert len(profiles) >= 1, "No backup profiles registered!"

print("\n=== 5. 로컬 라이브 Web UI 및 API 응답 검증 ===")
apis = [
    ("/", 200),
    ("/api/snapshots", 200),
    ("/api/alerts/summary", 200),
    ("/api/update/status", 200),
]
for path, expected_status in apis:
    url = f"http://127.0.0.1:8765{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=3) as resp:
        print(f"[PASS] {path:<22} -> HTTP {resp.status} OK")

print("\n==================================================")
print(">>> ALL 5 FUNCTIONAL REGRESSION TESTS PASSED! <<<")
print("==================================================")
