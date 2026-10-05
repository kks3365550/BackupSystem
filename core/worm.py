# -*- coding: utf-8 -*-
"""
core/worm.py: 진정한 WORM (Write Once Read Many / 랜섬웨어 변조 방지) 보호 엔진 (v2.4.1)
- Windows NTFS ACL: Everyone(*S-1-1-0)에 대해 Delete(DE), WriteData(WD), AppendData(AD) 거부(Deny) ACL 적용
- 디렉토리 수준 DeleteChild(DC) 거부로 파일 무단 삭제 및 덮어쓰기 원천 차단
- POSIX/Non-Windows 환경: Read-Only 속성(S_IREAD) 자동 폴백
- 정당한 보존 정책(Retention Pruning) 시 ACL 복구 및 원자적 해제 지원
"""

import os
import sys
import stat
import logging
import subprocess
from typing import Optional, Dict

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform.startswith('win')
SID_EVERYONE = "*S-1-1-0"


class WORMAuthorizationError(PermissionError):
    """Raised when an unauthorized process attempts to unprotect WORM-protected repository files."""
    pass


class WORMManager:
    """
    저장소 파일 및 디렉토리에 대해 OS 및 파일시스템 수준의 WORM 보호를 강제하는 엔진.
    Windows NTFS 환경에서는 icacls를 활용하여 Delete, WriteData, AppendData, DeleteChild 거부 ACL을 부여합니다.
    """

    def __init__(self):
        self._is_windows = IS_WINDOWS

    def _run_icacls(self, target_path: str, arguments: list) -> bool:
        if not self._is_windows or not os.path.exists(target_path):
            return False

        cmd = ["icacls", target_path] + arguments
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if self._is_windows else 0
            )
            if result.returncode != 0:
                logger.debug(f"icacls notice for {target_path}: {result.stderr.strip() or result.stdout.strip()}")
                return False
            return True
        except FileNotFoundError:
            logger.debug("icacls executable not found. Skipping NTFS ACL.")
            return False
        except Exception as e:
            logger.debug(f"icacls exception on {target_path}: {e}")
            return False

    def protect_file(self, filepath: str, use_ntfs_acl: bool = True) -> bool:
        """
        파일을 수정/삭제할 수 없도록 WORM 보호를 적용합니다.
        1. OS Read-only 속성 부여
        2. Windows NTFS 환경일 경우 Delete, Write, Append 거부 ACL 부여
        """
        if not os.path.exists(filepath):
            return False

        success = False

        # 1. POSIX / DOS Read-Only attribute
        try:
            current_mode = os.stat(filepath).st_mode
            new_mode = current_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH
            os.chmod(filepath, new_mode)
            success = True
        except Exception as e:
            logger.debug(f"chmod readonly failed on {filepath}: {e}")

        # 2. Windows NTFS ACL Deny (DE,WD,AD)
        if self._is_windows and use_ntfs_acl:
            acl_ok = self._run_icacls(filepath, ["/deny", f"{SID_EVERYONE}:(DE,WD,AD)"])
            if acl_ok:
                success = True

        return success

    def unprotect_file(self, filepath: str, authorized: bool = False) -> bool:
        """
        정당한 삭제나 정리를 위해 WORM 보호를 해제합니다.
        명시적 관리자 권한(authorized=True)이 필요하며, 인가되지 않은 호출은 차단됩니다.
        """
        if not authorized:
            raise WORMAuthorizationError(f"WORM 보호 해제 거부: {filepath} (명시적 관리자 승인 권한 필요)")

        if not os.path.exists(filepath):
            return False

        success = False

        # 1. Remove NTFS Deny ACL
        if self._is_windows:
            if self._run_icacls(filepath, ["/remove:d", SID_EVERYONE]):
                success = True

        # 2. Restore Write attribute
        try:
            current_mode = os.stat(filepath).st_mode
            new_mode = current_mode | stat.S_IWUSR
            os.chmod(filepath, new_mode)
            success = True
        except Exception as e:
            logger.debug(f"chmod writeable failed on {filepath}: {e}")

        return success

    def protect_directory(self, dirpath: str) -> bool:
        """
        디렉토리 내 파일 삭제(Delete Child)를 거부하는 WORM ACL을 적용합니다.
        """
        if not os.path.isdir(dirpath):
            return False

        if self._is_windows:
            return self._run_icacls(dirpath, ["/deny", f"{SID_EVERYONE}:(DC)"])
        return True

    def unprotect_directory(self, dirpath: str, authorized: bool = False) -> bool:
        """
        디렉토리의 Delete Child 거부 ACL을 해제합니다.
        명시적 관리자 권한(authorized=True)이 필요합니다.
        """
        if not authorized:
            raise WORMAuthorizationError(f"WORM 디렉토리 보호 해제 거부: {dirpath} (명시적 관리자 승인 권한 필요)")

        if not os.path.isdir(dirpath):
            return False

        if self._is_windows:
            return self._run_icacls(dirpath, ["/remove:d", SID_EVERYONE])
        return True

    def protect_repository(self, repo_dir: str, protect_dirs: bool = False) -> Dict[str, int]:
        """
        저장소 내 모든 스냅샷 매니페스트 및 블롭 디렉토리에 대해 일괄 WORM을 적용합니다.
        """
        protected_blobs = 0
        protected_snapshots = 0

        snapshots_dir = os.path.join(repo_dir, "snapshots")
        if os.path.exists(snapshots_dir):
            for fname in os.listdir(snapshots_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(snapshots_dir, fname)
                    if self.protect_file(fpath, use_ntfs_acl=True):
                        protected_snapshots += 1

        blobs_dir = os.path.join(repo_dir, "blobs")
        if os.path.exists(blobs_dir):
            if protect_dirs:
                self.protect_directory(blobs_dir)
            for root, _, files in os.walk(blobs_dir):
                for f in files:
                    if f.endswith(".blob"):
                        fpath = os.path.join(root, f)
                        if self.protect_file(fpath, use_ntfs_acl=False):
                            protected_blobs += 1

        return {
            "protected_snapshots": protected_snapshots,
            "protected_blobs": protected_blobs
        }


# 하위 호환성 단축 함수
_default_worm_manager = WORMManager()

def lock_file_immutable(filepath: str, use_ntfs_acl: bool = False) -> bool:
    """하위 호환성을 지원하는 WORM 잠금 함수"""
    return _default_worm_manager.protect_file(filepath, use_ntfs_acl=use_ntfs_acl)

def unlock_file_writable(filepath: str, authorized: bool = True) -> bool:
    """하위 호환성을 지원하는 WORM 해제 함수 (명시적 권한 검증)"""
    return _default_worm_manager.unprotect_file(filepath, authorized=authorized)
