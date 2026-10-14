# -*- coding: utf-8 -*-
"""
tests/test_disk_clone.py: 라이브 SSD 마이그레이션(클론 & 부트로더 주입) 단위 테스트 스위트
"""
from unittest.mock import patch, MagicMock

from core.disk_clone import (
    DiskCloneManager,
    get_candidate_target_drives,
    normalize_drive
)


def test_normalize_drive_various_inputs():
    assert normalize_drive("e") == "E:"
    assert normalize_drive("E") == "E:"
    assert normalize_drive("E:") == "E:"
    assert normalize_drive("e:\\") == "E:"
    assert normalize_drive("D:/") == "D:"
    assert normalize_drive("  F:  ") == "F:"
    assert normalize_drive("") == ""


def test_get_candidate_target_drives_excludes_c():
    with patch("core.disk_clone.psutil.disk_partitions") as mock_parts, \
         patch("core.disk_clone.shutil.disk_usage") as mock_usage:
        
        # C: 드라이브 사용량: total=500GB, used=100GB, free=400GB
        # E: 드라이브 용량: total=250GB, used=10GB, free=240GB (수용 가능: 250 > 100 * 1.05)
        # F: 드라이브 용량: total=80GB, used=10GB, free=70GB (용량 부족: 80 < 100 * 1.05)
        def fake_usage(path):
            p = str(path).upper()
            if "C:" in p:
                return type("Usage", (), {"total": 500 * (1024**3), "used": 100 * (1024**3), "free": 400 * (1024**3)})()
            elif "E:" in p:
                return type("Usage", (), {"total": 250 * (1024**3), "used": 10 * (1024**3), "free": 240 * (1024**3)})()
            elif "F:" in p:
                return type("Usage", (), {"total": 80 * (1024**3), "used": 10 * (1024**3), "free": 70 * (1024**3)})()
            return type("Usage", (), {"total": 100 * (1024**3), "used": 10 * (1024**3), "free": 90 * (1024**3)})()

        mock_usage.side_effect = fake_usage
        mock_parts.return_value = [
            type("Part", (), {"mountpoint": "C:\\", "fstype": "NTFS", "device": "C:"})(),
            type("Part", (), {"mountpoint": "E:\\", "fstype": "NTFS", "device": "E:"})(),
            type("Part", (), {"mountpoint": "F:\\", "fstype": "NTFS", "device": "F:"})(),
        ]

        candidates = get_candidate_target_drives()
        drives = [c["drive"] for c in candidates]

        # C: 는 원천 제외
        assert "C:" not in drives
        assert "E:" in drives
        assert "F:" in drives

        e_cand = next(c for c in candidates if c["drive"] == "E:")
        assert e_cand["acceptable"] is True

        f_cand = next(c for c in candidates if c["drive"] == "F:")
        assert f_cand["acceptable"] is False
        assert "용량 부족" in f_cand["reason"]


def test_disk_clone_manager_singleton():
    mgr1 = DiskCloneManager.get_instance()
    mgr2 = DiskCloneManager.get_instance()
    mgr3 = DiskCloneManager()
    assert mgr1 is mgr2
    assert mgr2 is mgr3


def test_disk_clone_manager_start_validation():
    mgr = DiskCloneManager.get_instance()
    # C: 드라이브 입력 거부
    res1 = mgr.start_clone("C:")
    assert res1["success"] is False
    assert "C:" in res1["error"]

    # 존재하지 않는 드라이브 거부
    with patch("os.path.exists", return_value=False):
        res2 = mgr.start_clone("Z:")
        assert res2["success"] is False
        assert "경로" in res2["error"]


def test_disk_clone_manager_pipeline_execution():
    mgr = DiskCloneManager.get_instance()
    mgr._init_state()

    with patch("core.disk_clone.shutil.disk_usage") as mock_usage, \
         patch("core.disk_clone.VSSContext") as mock_vss_cls, \
         patch("core.disk_clone.subprocess.Popen") as mock_popen, \
         patch("core.disk_clone.subprocess.run") as mock_run, \
         patch("os.path.exists", return_value=True):

        # 용량 충분
        mock_usage.side_effect = lambda p: type("Usage", (), {
            "total": 500 * (1024**3),
            "used": 50 * (1024**3),
            "free": 450 * (1024**3)
        })()

        # VSS Context Mock
        vss_mock = MagicMock()
        vss_mock.vss_active = True
        vss_mock.get_shadow_path.return_value = "GLOBALROOT\\Device\\HarddiskVolumeShadowCopy1"
        mock_vss_cls.return_value = vss_mock

        # Robocopy Popen Mock (returncode 1 = 복사 성공)
        proc_mock = MagicMock()
        proc_mock.poll.side_effect = [None, 1]
        proc_mock.stdout.readline.side_effect = ["New File: test.txt\n", ""]
        proc_mock.returncode = 1
        mock_popen.return_value = proc_mock

        # bcdboot subprocess.run Mock
        mock_run.return_value = type("SubRes", (), {"returncode": 0, "stdout": "부팅 파일이 성공적으로 만들어졌습니다.", "stderr": ""})()

        # 파이프라인 동기 실행
        mgr._run_clone_pipeline("E:")

        status = mgr.get_status()
        assert status["status"] == "completed"
        assert status["progress_percent"] == 100.0
        assert status["is_running"] is False
        logs = mgr.get_logs()
        assert any("마이그레이션이 성공적으로 완료되었습니다" in l for l in logs)


def test_disk_clone_manager_pipeline_cancel():
    mgr = DiskCloneManager.get_instance()
    mgr._init_state()

    with patch("core.disk_clone.shutil.disk_usage") as mock_usage, \
         patch("core.disk_clone.subprocess.Popen") as mock_popen, \
         patch("os.path.exists", return_value=True):

        mock_usage.side_effect = lambda p: type("Usage", (), {
            "total": 500 * (1024**3),
            "used": 50 * (1024**3),
            "free": 450 * (1024**3)
        })()

        proc_mock = MagicMock()
        proc_mock.poll.return_value = None
        mock_popen.return_value = proc_mock

        # 취소 이벤트 미리 활성화
        mgr._cancel_event.set()

        mgr._run_clone_pipeline("E:")

        status = mgr.get_status()
        assert status["status"] == "cancelled"
        assert "취소되었습니다" in status["error_message"]


def test_api_migration_fastapi_endpoints():
    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)

    # 1. GET /api/migration/disks
    with patch("web.api_migration.get_candidate_target_drives", return_value=[{"drive": "E:", "acceptable": True}]):
        res = client.get("/api/migration/disks")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["drives"]) == 1

    # 2. GET /api/migration/status
    res = client.get("/api/migration/status")
    assert res.status_code == 200
    assert "status" in res.json()

    # 3. GET /api/migration/logs
    res = client.get("/api/migration/logs")
    assert res.status_code == 200
    assert "logs" in res.json()

    # 4. POST /api/migration/start (유효성 검증 실패: C: 지정)
    res = client.post("/api/migration/start", json={"target_drive": "C:"})
    assert res.status_code == 400

    # 5. POST /api/migration/stop
    res = client.post("/api/migration/stop")
    assert res.status_code == 400 or res.status_code == 200  # 실행 중이 아니면 400 반환 정상
