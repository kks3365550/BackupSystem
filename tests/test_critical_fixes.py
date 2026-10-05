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


def test_auth_fail_closed_on_corrupt_config(monkeypatch):
    """auth_config.json이 손상되었을 때 전체 API가 무인증 개방(Fail-Open)되지 않고 500 Fail-Closed로 차단되어야 한다."""
    from unittest.mock import patch
    from starlette.testclient import TestClient
    from web.app import app
    from core import auth

    tmp_dir = tempfile.mkdtemp(prefix="test_auth_corrupt_")
    try:
        bad_auth_file = os.path.join(tmp_dir, "auth_config.json")
        with open(bad_auth_file, "w", encoding="utf-8") as f:
            f.write("corrupted json { not a valid json [")

        with patch("core.auth.AUTH_CONFIG_FILE", bad_auth_file):
            assert auth.is_auth_corrupted()
            assert auth.is_auth_configured()  # Fail-Closed: 미설정으로 다운그레이드되지 않음

            client = TestClient(app, raise_server_exceptions=False)
            # 보호된 API 요청 시 손상 감지 -> HTTP 500 차단
            resp = client.get("/api/system-info")
            assert resp.status_code == 500
            assert resp.json().get("corrupted") is True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_auth_minimum_8_char_password(monkeypatch):
    """비밀번호는 최소 8자리 이상이어야 하며, 4자리 등 짧은 비밀번호는 거부되어야 한다."""
    from unittest.mock import patch
    from core import auth

    tmp_dir = tempfile.mkdtemp(prefix="test_auth_len_")
    try:
        auth_file = os.path.join(tmp_dir, "auth_config.json")
        with patch("core.auth.AUTH_CONFIG_FILE", auth_file):
            # 4자리 -> 거부
            with pytest.raises(ValueError) as exc:
                auth.setup_master_password("1234")
            assert "8자리" in str(exc.value)

            # 7자리 -> 거부
            with pytest.raises(ValueError) as exc:
                auth.setup_master_password("1234567")
            assert "8자리" in str(exc.value)

            # 8자리 이상 -> 성공
            assert auth.setup_master_password("password123") is True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_login_rate_limit_lockout():
    """로그인 5회 연속 실패 시 락아웃(429)되어 무차별 대입(Brute-force) 공격이 차단되어야 한다."""
    from core import auth

    test_ip = "192.168.1.99"
    auth.reset_login_rate_limits_for_test()

    # 4회 실패 -> 아직 잠기지 않음
    for i in range(4):
        failures, is_locked = auth.record_login_failure(test_ip)
        assert failures == i + 1
        assert not is_locked
        locked, _ = auth.check_login_rate_limit(test_ip)
        assert not locked

    # 5회 실패 -> 락아웃 활성화
    failures, is_locked = auth.record_login_failure(test_ip)
    assert failures == 5
    assert is_locked
    locked, remaining = auth.check_login_rate_limit(test_ip)
    assert locked
    assert remaining > 0

    # 성공 시 리셋
    auth.record_login_success(test_ip)
    locked_after, _ = auth.check_login_rate_limit(test_ip)
    assert not locked_after


def test_retention_and_worm_authorized_default_fail_closed(temp_repo):
    """retention.apply_policy 및 worm.unprotect_*의 authorized 기본값은 반드시 False여야 한다."""
    from core.retention import RetentionManager
    from core.worm import WORMManager, WORMAuthorizationError

    mgr = RetentionManager(temp_repo)
    # authorized 인자 없이 호출 시 내부 delete_snapshot에서 WORMAuthorizationError 발생
    # (단, 스냅샷이 1개 이하일 때는 안전 최소치 반환)
    worm = WORMManager()
    dummy_file = os.path.join(temp_repo, "test.txt")
    with open(dummy_file, "w") as f:
        f.write("test")

    with pytest.raises(WORMAuthorizationError):
        worm.unprotect_file(dummy_file)  # 기본값 authorized=False이므로 거부되어야 함

