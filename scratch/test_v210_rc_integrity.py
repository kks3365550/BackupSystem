# -*- coding: utf-8 -*-
"""
scratch/test_v210_rc_integrity.py - P0~P3 Integrity & Regression Verification Suite
===================================================================================
Rigorous verification for v2.10.0-rc:
1. P0: Uncached vs Cached Byte/Field/Order 100% Identity (JSON SHA256 Match)
2. P1: Source of Truth separation (Snapshot CAS vs SQLite Replication)
3. P2: Fail-Safe Eviction on error (No exception swallowing)
4. P3: External directory change detection (dir_mtime + count heuristic)
"""

import os
import sys
import json
import time
import shutil
import tempfile
import hashlib

# 프로젝트 루트 경로
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from typing import Any
from core.snapshot import SnapshotEngine
from core.snapshot_cache import get_snapshot_cache
from core.replication_queue import ReplicationQueueManager
from core.storage import BlobStorage, unlock_file_writable
import web.app as web_app


def compute_deterministic_hash(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def run_integrity_suite():
    print("=" * 80)
    print(" [v2.10.0-rc RIGOROUS INTEGRITY & REGRESSION SUITE]")
    print("=" * 80)

    temp_root = tempfile.mkdtemp(prefix="rc_test_integrity_")
    repo_dir = os.path.join(temp_root, "repo")
    src_dir = os.path.join(temp_root, "source")
    os.makedirs(repo_dir, exist_ok=True)
    os.makedirs(src_dir, exist_ok=True)

    # 1. 20개 소스 파일 생성
    for i in range(20):
        with open(os.path.join(src_dir, f"file_{i:02d}.dat"), "w", encoding="utf-8") as f:
            f.write(f"Payload block {i}\n" * 100)

    cache = get_snapshot_cache()
    cache.clear()

    try:
        # 스냅샷 5개 생성
        print("[*] Creating 5 test snapshots...")
        sids = []
        for i in range(5):
            res = SnapshotEngine.create_snapshot(
                repo_dir=repo_dir,
                sources=[src_dir],
                profile_id=f"prof_{i}",
                profile_name=f"Profile {i}",
                use_vss=False
            )
            sids.append(res["id"])
            time.sleep(0.05)

        print(f"[+] Created snapshots: {len(sids)}")

        # -----------------------------------------------------------------
        # TEST 1 [P0]: Engine Level Byte/Field/Order Exact Identity
        # -----------------------------------------------------------------
        print("\n[*] TEST 1 [P0]: SnapshotEngine Uncached vs Cached Identity...")
        uncached_engine = SnapshotEngine._list_snapshots_disk(repo_dir)
        cached_engine = SnapshotEngine.list_snapshots(repo_dir)

        h_uncached = compute_deterministic_hash(uncached_engine)
        h_cached = compute_deterministic_hash(cached_engine)

        assert h_uncached == h_cached, f"Engine Hash mismatch! {h_uncached} != {h_cached}"
        assert uncached_engine == cached_engine, "Engine dict list not identical!"
        print(f"    [+] Hash Uncached: {h_uncached}")
        print(f"    [+] Hash Cached  : {h_cached}")
        print("    [PASS] P0 Engine-level 100% Byte/Field/Order Match!")

        # -----------------------------------------------------------------
        # TEST 2 [P0]: Web API Level Byte/Field/Order Exact Identity
        # -----------------------------------------------------------------
        print("\n[*] TEST 2 [P0]: web.app.list_snapshots Uncached vs Cached Identity...")
        # 임의로 캐시를 비우고 최초 조회
        cache.clear()
        api_res_cold = web_app.list_snapshots(repo_dir)
        # 캐시된 상태에서 2차 조회
        api_res_cached = web_app.list_snapshots(repo_dir)

        h_api_cold = compute_deterministic_hash(api_res_cold)
        h_api_cached = compute_deterministic_hash(api_res_cached)

        assert h_api_cold == h_api_cached, f"API Hash mismatch! {h_api_cold} != {h_api_cached}"
        assert api_res_cold == api_res_cached, "API dict list not identical!"
        print(f"    [+] Hash API Cold  : {h_api_cold}")
        print(f"    [+] Hash API Cached: {h_api_cached}")
        print("    [PASS] P0 Web API-level 100% Byte/Field/Order Match!")

        # -----------------------------------------------------------------
        # TEST 3 [P1]: Source of Truth Separation (Replication DB)
        # -----------------------------------------------------------------
        print("\n[*] TEST 3 [P1]: Replication Status Separation & Freshness...")
        rq = ReplicationQueueManager(repo_dir)
        target_sid = sids[0]
        # DB에 복제 상태 등록 및 커밋
        rq.enqueue(target_sid, repo_dir, r"D:\RemoteRepo")
        task = rq._fetch_next_task()
        if task:
            rq._update_state(task['id'], 'COMMITTED')

        # 캐시 무효화 없이 web_app.list_snapshots()를 호출했을 때,
        # 캐시는 파일 메타데이터만 갖고 있고 복제 상태는 DB에서 실시간 병합하므로
        # 즉시 COMMITTED가 반영되어야 함!
        snaps_after_repl = web_app.list_snapshots(repo_dir)
        target_snap = next((s for s in snaps_after_repl if s["id"] == target_sid), None)
        assert target_snap is not None, "Target snapshot missing"
        assert target_snap["offsite_status"] == "COMMITTED", f"Expected COMMITTED, got {target_snap['offsite_status']}"
        assert target_snap["is_offsite_protected"] is True, "is_offsite_protected must be True"
        print(f"    [+] Snapshot {target_sid} offsite_status: {target_snap['offsite_status']} (is_offsite_protected={target_snap['is_offsite_protected']})")
        print("    [PASS] P1 Source of Truth cleanly separated! Real-time DB state reflected without split-brain.")

        # -----------------------------------------------------------------
        # TEST 4 [P2]: Fail-Safe Eviction on Cache Corrupt / Error
        # -----------------------------------------------------------------
        print("\n[*] TEST 4 [P2]: Fail-Safe Eviction & Clean Fallback...")
        # 인위적으로 캐시 데이터 변조 (손상 시뮬레이션)
        repo_key = os.path.abspath(repo_dir)
        cache._cache[repo_key]["snapshots"] = "CORRUPTED_STRING_NOT_LIST"

        # 손상된 상태에서 list_snapshots 호출 시, 예외를 삼키지 않고 evict 후 정상 디스크 로드로 복구해야 함
        recovered_list = SnapshotEngine.list_snapshots(repo_dir)
        assert isinstance(recovered_list, list), "Must fallback to clean list"
        assert len(recovered_list) == 5, "Must recover all 5 snapshots"
        assert cache._stats["evictions"] > 0, "Eviction must be recorded"
        print(f"    [+] Successfully evicted corrupted entry and cleanly recovered {len(recovered_list)} snapshots")
        print("    [PASS] P2 Fail-Safe Eviction operates correctly!")

        # -----------------------------------------------------------------
        # TEST 5 [P3]: External Directory Mutation Detection (Fingerprint)
        # -----------------------------------------------------------------
        print("\n[*] TEST 5 [P3]: External Directory Mutation Detection...")
        # 외부에서 스냅샷 1건 임의 삭제
        storage = BlobStorage(repo_dir)
        del_target_sid = sids[3]
        del_file = os.path.join(storage.snapshots_dir, f"{del_target_sid}.json")
        if os.path.exists(del_file):
            unlock_file_writable(del_file, authorized=True)
            os.remove(del_file)
            os.utime(storage.snapshots_dir, None)

        # 호출 시 mtime/count 변경으로 즉시 재스캔되어 삭제가 반영되어야 함
        snaps_after_del = SnapshotEngine.list_snapshots(repo_dir)
        assert len(snaps_after_del) == 4, f"Expected 4 snapshots, got {len(snaps_after_del)}"
        assert not any(s["id"] == del_target_sid for s in snaps_after_del), "Deleted snapshot must not be present"
        print(f"    [+] External file deletion cleanly detected via fingerprint (Remaining: {len(snaps_after_del)})")
        print("    [PASS] P3 External Change Safeguard verified!")

        print("\n" + "=" * 80)
        print(" [ALL INTEGRITY & REGRESSION TESTS PASSED (P0, P1, P2, P3 100%)]")
        print("=" * 80)
        return True

    finally:
        def _del_rw(func, path, exc_info):
            try:
                os.chmod(path, 0o777)
                func(path)
            except Exception:
                pass
        shutil.rmtree(temp_root, onerror=_del_rw)


if __name__ == "__main__":
    success = run_integrity_suite()
    sys.exit(0 if success else 1)
