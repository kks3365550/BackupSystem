# -*- coding: utf-8 -*-
"""
core/vss_manager.py: Windows Volume Shadow Copy (VSS) 스냅샷 관리자
- Windows 환경에서 볼륨 섀도 복사본(Shadow Copy) 생성 및 라이프사이클 관리
- 실행 중인 파일(Outlook PST, SQLite, 잠긴 오피스 파일 등)의 안전한 Crash-Consistent 백업 지원
- 컨텍스트 매니저 기반 자동 리소스 해제(Cleanup)로 섀도 복사본 누수 원천 차단
- 관리자 권한 미부여 또는 VSS 미지원 드라이브 대상 Graceful Fallback (직접 접근 모드) 지원
"""

import os
import re
import sys
import ctypes
import logging
import subprocess
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("BackupSystem.VSS")


def is_admin() -> bool:
    """현재 프로세스가 Windows 관리자 권한으로 실행 중인지 확인."""
    try:
        if sys.platform == "win32":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return False
    except Exception:
        return False


def extract_drive_letter(path: str) -> Optional[str]:
    """
    경로에서 드라이브 문자(예: 'C:')를 추출.
    UNC 경로, 상대 경로 또는 비-Windows 형식은 None 반환.
    """
    if not path or not isinstance(path, str):
        return None
    p = path.replace('/', '\\')
    m = re.match(r'^([A-Za-z]):', p)
    if m:
        return m.group(1).upper() + ':'
    return None


class ShadowCopyRecord:
    """단일 드라이브에 대한 VSS 섀도 복사본 정보 레코드"""
    __slots__ = ('drive', 'shadow_id', 'device_path')

    def __init__(self, drive: str, shadow_id: str, device_path: str):
        self.drive = drive
        self.shadow_id = shadow_id
        self.device_path = device_path

    def __repr__(self) -> str:
        return f"<ShadowCopy drive={self.drive} id={self.shadow_id} device={self.device_path}>"


class VSSCreationError(Exception):
    """VSS 섀도 복사본 생성 실패 시 내부적으로 발생하는 예외."""
    pass


class VSSContext:
    """
    백업 세션 동안 볼륨 섀도 복사본(VSS)을 생성하고 작업 완료/예외 시 안전하게 해제하는 컨텍스트 매니저.

    사용법:
        with VSSContext(source_paths) as vss:
            if vss.vss_active:
                # 섀도 복사본 장치 경로로 파일 스트리밍
                read_path = vss.get_shadow_path(original_file)
            ...
    """

    def __init__(self, source_paths: List[str], enabled: bool = True):
        self.source_paths = list(source_paths) if source_paths else []
        self.enabled = enabled
        self.vss_active: bool = False
        self.shadows: Dict[str, ShadowCopyRecord] = {}  # 'C:' -> ShadowCopyRecord
        self.warnings: List[str] = []
        self._cleanup_done: bool = False

    def __enter__(self) -> 'VSSContext':
        if not self.enabled:
            self.warnings.append("VSS가 비활성화되었습니다.")
            return self

        if sys.platform != "win32":
            self.warnings.append("VSS는 Windows 환경에서만 지원됩니다.")
            return self

        self._setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False  # 예외는 상위로 정상 전파

    def _setup(self):
        """백업 소스 경로들이 속한 모든 고유 볼륨에 대해 VSS 섀도 복사본 생성."""
        # 1. 고유 드라이브 볼륨 식별
        unique_drives = set()
        for p in self.source_paths:
            drv = extract_drive_letter(p)
            if drv:
                unique_drives.add(drv)

        if not unique_drives:
            self.warnings.append("유효한 Windows 드라이브 경로가 없어 VSS를 건너뜁니다.")
            return

        # 2. 관리자 권한 확인
        if not is_admin():
            msg = "관리자 권한이 없어 VSS 볼륨 스냅샷을 생성할 수 없습니다. 일반 파일 직접 읽기 모드로 백업을 진행합니다."
            self.warnings.append(msg)
            logger.info(msg)
            return

        # 3. 드라이브별 섀도 복사본 생성
        for drv in sorted(unique_drives):
            try:
                sc = self._create_shadow(drv)
                if sc:
                    self.shadows[drv] = sc
                    logger.info("VSS 섀도 복사본 생성 완료: %s -> %s (ID: %s)", drv, sc.device_path, sc.shadow_id)
            except Exception as e:
                msg = f"{drv} 볼륨 VSS 스냅샷 생성 실패: {e}. 해당 볼륨은 일반 직접 읽기 모드로 폴백합니다."
                self.warnings.append(msg)
                logger.warning(msg)

        if self.shadows:
            self.vss_active = True
        else:
            self.warnings.append("모든 드라이브의 VSS 생성이 실패하여 일반 직접 읽기 모드로 동작합니다.")

    @staticmethod
    def _run_cmd(cmd: List[str], timeout: int = 90) -> Tuple[int, str, str]:
        """subprocess 안전 실행 및 윈도우 인코딩(cp949/utf-8) 다중 디코딩"""
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=creationflags
        )
        def decode_bytes(b: bytes) -> str:
            for enc in ('cp949', 'utf-8', 'euc-kr', 'latin1'):
                try:
                    return b.decode(enc)
                except UnicodeDecodeError:
                    pass
            return b.decode('utf-8', errors='replace')

        stdout = decode_bytes(proc.stdout)
        stderr = decode_bytes(proc.stderr)
        return proc.returncode, stdout, stderr

    @classmethod
    def _create_shadow(cls, drive: str) -> ShadowCopyRecord:
        """
        vssadmin create shadow /for=C: 를 호출하여 섀도 복사본 생성.
        성공 시 ShadowCopyRecord 반환.
        """
        vol_path = drive + '\\' if not drive.endswith('\\') else drive
        cmd = ['vssadmin', 'create', 'shadow', f'/for={vol_path}']

        rc, stdout, stderr = cls._run_cmd(cmd, timeout=120)
        combined_output = stdout + "\n" + stderr

        if rc != 0:
            raise VSSCreationError(f"vssadmin 종료 코드 {rc}: {combined_output.strip()}")

        # Shadow ID (GUID) 추출: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
        shadow_id = None
        id_match = re.search(
            r'\{([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\}',
            combined_output
        )
        if id_match:
            shadow_id = '{' + id_match.group(1) + '}'

        # Device Path 추출: \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopyX
        device_path = None
        dev_match = re.search(
            r'(\\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy\d+)',
            combined_output,
            re.IGNORECASE
        )
        if dev_match:
            device_path = dev_match.group(1)

        if not shadow_id or not device_path:
            raise VSSCreationError(f"vssadmin 출력에서 섀도 복사본 정보(ID 또는 디바이스 경로)를 파싱할 수 없습니다:\n{combined_output}")

        return ShadowCopyRecord(drive=drive, shadow_id=shadow_id, device_path=device_path)

    @classmethod
    def _delete_shadow(cls, shadow_id: str) -> bool:
        """vssadmin delete shadows /shadow={id} /quiet 호출로 특정 섀도 복사본 삭제."""
        cmd = ['vssadmin', 'delete', 'shadows', f'/shadow={shadow_id}', '/quiet']
        try:
            rc, stdout, stderr = cls._run_cmd(cmd, timeout=60)
            return rc == 0
        except Exception as e:
            logger.error("VSS 섀도 복사본 %s 삭제 중 예외: %s", shadow_id, e)
            return False

    def cleanup(self):
        """생성된 모든 섀도 복사본을 100% 누수 없이 해제."""
        if self._cleanup_done:
            return
        self._cleanup_done = True

        for drv, sc in list(self.shadows.items()):
            try:
                success = self._delete_shadow(sc.shadow_id)
                if success:
                    logger.info("VSS 섀도 복사본 해제 완료: %s (ID: %s)", drv, sc.shadow_id)
                else:
                    logger.warning("VSS 섀도 복사본 해제 실패: %s (ID: %s)", drv, sc.shadow_id)
            except Exception as e:
                logger.error("VSS 클린업 예외 (%s): %s", drv, e)

        self.shadows.clear()
        self.vss_active = False

    def get_shadow_path(self, original_path: str) -> str:
        """
        원본 파일 경로(예: C:\\Users\\user\\file.txt)를
        섀도 복사본 디바이스 경로(예: \\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy1\\Users\\user\\file.txt)로 변환.
        해당 드라이브에 활성 VSS가 없는 경우 원본 경로를 그대로 반환.
        """
        if not self.vss_active or not self.shadows:
            return original_path

        drv = extract_drive_letter(original_path)
        if not drv or drv not in self.shadows:
            return original_path

        sc = self.shadows[drv]
        norm = original_path.replace('/', '\\')
        # 'C:' 또는 'C:\' 접두사 제거
        rel = re.sub(r'^[A-Za-z]:\\?', '', norm).lstrip('\\')
        shadow_root = sc.device_path.rstrip('\\')

        if rel:
            return f"{shadow_root}\\{rel}"
        return shadow_root
