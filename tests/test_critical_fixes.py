# -*- coding: utf-8 -*-
"""
tests/test_critical_fixes.py: CRITICAL 결함 2건에 대한 회귀 방지 검증 테스트
1. CRITICAL #1: GC/Prune 락 보호 및 BackupLock 재진입성(Re-entrancy)
2. CRITICAL #2: 매니페스트 손상 시 prune_storage Fail-Closed 즉시 중단 (블롭 보호)
"""

import os
import shutil
import tempfile
import json
import pytest
from core.lock import BackupLock, BackupAlreadyRunningError
from core.snapshot import SnapshotEngine
from core.storage import BlobStorage


@pytest.fixture
def temp_repo():
    tmp_dir = tempfile.mkdtemp(prefix="test_backup_critical_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_backuplock_reentrancy(temp_repo):
    """동일 프로세스 내에서 BackupLock이 재진입(RLock) 가능해야 한다."""
    lock1 = BackupLock(temp_repo, timeout_sec=1.0, process_desc="Outer Lock")
    lock2 = BackupLock(temp_repo, timeout_sec=1.0, process_desc="Inner Lock")

    with lock1:
        assert lock1._is_locked
        with lock2:
            assert lock2._is_locked
            assert getattr(lock2, "_is_reentrant", False)
        # lock2 해제 후에도 lock1은 여전히 잠겨 있어야 함
        assert lock1._is_locked
        assert os.path.exists(lock1.lock_path)

    # lock1 해제 후에는 락 파일이 정리되어야 함
    assert not lock1._is_locked
    assert not os.path.exists(lock1.lock_path)


def test_prune_storage_fail_closed_on_corrupt_manifest(temp_repo):
    """매니페스트 중 하나라도 손상된 경우 prune_storage는 Fail-Closed로 즉시 예외를 발생시키고 블롭을 삭제하지 않아야 한다."""
    storage = BlobStorage(temp_repo)
    os.makedirs(storage.snapshots_dir, exist_ok=True)
    os.makedirs(storage.blobs_dir, exist_ok=True)

    # 1. 테스트 블롭 생성
    test_data = b"important production backup data"
    blob_id, _, _, _ = storage.put_bytes_blob(test_data)
    assert storage.has_blob(blob_id)

    # 2. 유효한 매니페스트 생성 (해당 블롭 참조)
    valid_manifest = {
        "id": "snap_valid",
        "created_at": 1000.0,
        "entries": [{"blob_id": blob_id, "path": "file.txt"}]
    }
    with open(os.path.join(storage.snapshots_dir, "snap_valid.json"), "w", encoding="utf-8") as f:
        json.dump(valid_manifest, f)

    # 3. 손상된 매니페스트 파일 생성 (문법 오류)
    with open(os.path.join(storage.snapshots_dir, "snap_corrupted.json"), "w", encoding="utf-8") as f:
        f.write("{corrupted json contents: [invalid")

    # 4. prune_storage 실행 시 RuntimeError (Fail-Closed)가 발생해야 함
    with pytest.raises(RuntimeError) as exc_info:
        SnapshotEngine.prune_storage(temp_repo)

    assert "Fail-Closed" in str(exc_info.value) or "데이터 보호를 위해" in str(exc_info.value)

    # 5. [핵심 검증] 블롭이 절대 삭제되지 않고 온전히 보존되어 있어야 함!
    assert storage.has_blob(blob_id), "손상된 매니페스트로 인해 블롭이 삭제되어서는 안 됩니다!"


def test_prune_storage_success_when_all_manifests_valid(temp_repo):
    """모든 매니페스트가 정상일 경우 정상적으로 GC가 수행되어야 한다."""
    storage = BlobStorage(temp_repo)
    os.makedirs(storage.snapshots_dir, exist_ok=True)

    # 1. 활성 블롭 및 고아 블롭 생성
    active_data = b"active data"
    orphan_data = b"orphan data to be pruned"
    active_id, _, _, _ = storage.put_bytes_blob(active_data)
    orphan_id, _, _, _ = storage.put_bytes_blob(orphan_data)

    assert storage.has_blob(active_id)
    assert storage.has_blob(orphan_id)

    # 2. active_id만 참조하는 정상 매니페스트 기록
    valid_manifest = {
        "id": "snap_normal",
        "created_at": 1000.0,
        "entries": [{"blob_id": active_id, "path": "active.txt"}]
    }
    with open(os.path.join(storage.snapshots_dir, "snap_normal.json"), "w", encoding="utf-8") as f:
        json.dump(valid_manifest, f)

    # 3. prune_storage 정상 수행
    res = SnapshotEngine.prune_storage(temp_repo)
    assert res["deleted_blobs"] == 1
    assert storage.has_blob(active_id)
    assert not storage.has_blob(orphan_id)
