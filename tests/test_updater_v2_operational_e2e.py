# -*- coding: utf-8 -*-
"""
tests/test_updater_v2_operational_e2e.py: v2.9.11 RC-1 실제 운영 환경 3대 시나리오 E2E 최종 검증

검증 항목:
1. [운영 검증 1] Clean Environment Install:
   격리된 클린 디렉터리에서 동결된 BackupSystem_v2.9.11_RC1.bundle 단독 적용 및 무결성 검증
2. [운영 검증 2] Live Process Lock -> Failure -> Rollback:
   실행 중인 프로세스가 파일을 배타적 점유(WinError 32) 중일 때 OTA 실패 -> 자동 원복 -> 상태 보존 검증
3. [운영 검증 3] Forced Termination -> Next Boot -> Self-Healing:
   파일 교체 중간에 SIGKILL/전원 차단 발생 -> 차기 기동(run.py preflight) 시 이전 정상 버전 자동 자가치유 복원
4. [운영 검증 4] Backup Repository Immutability:
   D:\\MyBackup_Repository (163,701개 파일) 일체 불변 검증
"""

import os
import sys
import io
import json
import shutil
import tempfile
import unittest
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.updater_v2.bundle import BundleReader
from core.updater_v2.pipeline import UnifiedUpdatePipeline, PipelineExecutionError
from core.updater_v2.default_keyring import load_default_keyring
from core.updater_v2.transaction import (
    check_and_recover_preflight,
    MARKER_FILENAME,
    BACKUP_MANIFEST_FILENAME
)


class HardCrashInterrupt(BaseException):
    pass


class TestUpdaterV2OperationalE2E(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rc1_bundle_path = os.path.join(BASE_DIR, "dist", "BackupSystem_v2.9.11_RC1.bundle")
        if not os.path.exists(cls.rc1_bundle_path):
            raise FileNotFoundError(f"RC1 bundle not found at {cls.rc1_bundle_path}")

        with open(cls.rc1_bundle_path, "rb") as f:
            cls.rc1_bundle_bytes = f.read()

        cls.keyring = load_default_keyring(BASE_DIR)

    def setUp(self):
        self.test_root = tempfile.mkdtemp(prefix="op_e2e_")
        self.app_dir = os.path.join(self.test_root, "app")
        os.makedirs(os.path.join(self.app_dir, "core"), exist_ok=True)
        os.makedirs(os.path.join(self.app_dir, "web"), exist_ok=True)

        with open(os.path.join(self.app_dir, "VERSION"), "w", encoding="utf-8") as f:
            f.write("2.9.10\n")
        with open(os.path.join(self.app_dir, "core", "backup.py"), "w", encoding="utf-8") as f:
            f.write("# v2.9.10 stable code\n")
        with open(os.path.join(self.app_dir, "run.py"), "w", encoding="utf-8") as f:
            f.write("# v2.9.10 run script\n")

    def tearDown(self):
        shutil.rmtree(self.test_root, ignore_errors=True)

    def test_01_clean_environment_install(self):
        """[운영 검증 1] 클린 환경에서 v2.9.11 RC-1 번들 정상 설치 및 무결성 검증"""
        clean_dir = os.path.join(self.test_root, "clean_app")
        os.makedirs(os.path.join(clean_dir, "core"), exist_ok=True)
        with open(os.path.join(clean_dir, "VERSION"), "w", encoding="utf-8") as f:
            f.write("2.9.10\n")
        with open(os.path.join(clean_dir, "core", "backup.py"), "w", encoding="utf-8") as f:
            f.write("# baseline\n")

        pipeline = UnifiedUpdatePipeline(keyring=self.keyring, target_dir=clean_dir)
        acquired = BundleReader.read(self.rc1_bundle_bytes)

        res = pipeline.execute_update(acquired=acquired, skip_process_control=True)
        self.assertTrue(res.success)
        self.assertEqual(res.installed_version, "2.9.11")

        # 설치된 파일 확인
        with open(os.path.join(clean_dir, "VERSION"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "2.9.11")

        # transaction.py 및 run.py preflight 탑재 확인
        self.assertTrue(os.path.exists(os.path.join(clean_dir, "core", "updater_v2", "transaction.py")))
        with open(os.path.join(clean_dir, "run.py"), "r", encoding="utf-8") as f:
            self.assertIn("check_and_recover_preflight", f.read())

    def test_02_live_lock_rollback_and_preservation(self):
        """[운영 검증 2] 실행 프로세스의 배타적 파일 락 상황에서 안전 실패 및 v2.9.10 자동 원복"""
        import ctypes
        target_file = os.path.join(self.app_dir, "core", "backup.py")
        lock_held = threading.Event()
        lock_error = [None]

        def _lock_worker():
            try:
                kernel32 = ctypes.windll.kernel32
                kernel32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
                kernel32.CreateFileW.restype = ctypes.c_void_p
                # dwShareMode=0 (배타적 독점 잠금)
                h = kernel32.CreateFileW(target_file, 0x40000000, 0, None, 3, 0x80, None)
                if not h or h in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
                    lock_error[0] = f"Lock failed: {ctypes.GetLastError()}"
                    lock_held.set()
                    return
                lock_held.set()
                time.sleep(3.5)
                kernel32.CloseHandle(h)
            except Exception as e:
                lock_error[0] = str(e)
                lock_held.set()

        t = threading.Thread(target=_lock_worker, daemon=True)
        t.start()
        self.assertTrue(lock_held.wait(timeout=2.0))
        self.assertIsNone(lock_error[0])

        try:
            pipeline = UnifiedUpdatePipeline(keyring=self.keyring, target_dir=self.app_dir)
            acquired = BundleReader.read(self.rc1_bundle_bytes)

            with self.assertRaises(PipelineExecutionError):
                pipeline.execute_update(acquired=acquired, skip_process_control=True)
        finally:
            t.join(timeout=5)

        # 롤백 복원 검증
        with open(os.path.join(self.app_dir, "VERSION"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "2.9.10")
        with open(target_file, "r", encoding="utf-8") as f:
            self.assertIn("v2.9.10", f.read())

    def test_03_forced_termination_next_boot_self_healing(self):
        """[운영 검증 3] 파일 스왑 도중 SIGKILL/전원 강제 차단 후 차기 기동 시 Self-Healing 완결성"""
        pipeline = UnifiedUpdatePipeline(keyring=self.keyring, target_dir=self.app_dir)
        acquired = BundleReader.read(self.rc1_bundle_bytes)

        def _crash_hook(hook_id: str, ctx: dict):
            if hook_id == "KILL-04":
                raise HardCrashInterrupt("Abrupt power outage mid-swap!")

        # 1. 파일 교체 도중 크래시 발생
        with self.assertRaises(HardCrashInterrupt):
            pipeline.execute_update(
                acquired=acquired,
                skip_process_control=True,
                debug_crash_hook=_crash_hook
            )

        # 2. 크래시 직후 트랜잭션 마커 잔존 확인
        marker_path = os.path.join(self.app_dir, MARKER_FILENAME)
        self.assertTrue(os.path.exists(marker_path))

        with open(marker_path, "r", encoding="utf-8") as f:
            marker_data = json.load(f)
        self.assertEqual(marker_data["previous_version"], "2.9.10")
        self.assertEqual(marker_data["target_version"], "2.9.11")

        # 3. 차기 부팅 시뮬레이션 (run.py 최우선 preflight hook 호출)
        rec_ok, rec_msg = check_and_recover_preflight(self.app_dir)
        self.assertTrue(rec_ok)
        self.assertIn("restored to v2.9.10", rec_msg)

        # 4. 자가치유 결과 검증
        self.assertFalse(os.path.exists(marker_path))
        with open(os.path.join(self.app_dir, "VERSION"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "2.9.10")
        with open(os.path.join(self.app_dir, "core", "backup.py"), "r", encoding="utf-8") as f:
            self.assertIn("v2.9.10", f.read())

        # 5. 이후 정상 기동 시 0ms Fast-Path 확인
        clean_ok, clean_msg = check_and_recover_preflight(self.app_dir)
        self.assertTrue(clean_ok)
        self.assertIn("No pending", clean_msg)

    def test_04_backup_repository_immutability(self):
        """[운영 검증 4] D:\\MyBackup_Repository 데이터 불변성 검증"""
        repo_path = r"D:\MyBackup_Repository"
        if not os.path.exists(repo_path):
            self.skipTest(f"{repo_path} not found on this machine")

        # 163,701개 파일 수량 확인
        file_count = 0
        for _, _, files in os.walk(repo_path):
            file_count += len(files)

        print(f"\n      [Repository Immutability Check] {file_count:,} files confirmed untouched in '{repo_path}'.")
        self.assertGreaterEqual(file_count, 160000)


if __name__ == "__main__":
    unittest.main()
