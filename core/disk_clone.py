# -*- coding: utf-8 -*-
"""
core/disk_clone.py: 라이브 SSD 마이그레이션 (Live Disk Clone & Bootable) 엔진
- Windows 현재 실행 중인 C: 드라이브(OS + 데이터)를 VSS(Volume Shadow Copy)로 실시간 캡처
- 대상 물리 SSD로 고속 다이렉트 미러링 (Robocopy 멀티스레드)
- 부트로더(bcdboot) 자동 주입으로 대상 SSD를 즉시 부팅 가능한(Bootable) 상태로 구축
- 비동기 백그라운드 실행 및 실시간 진행률/로그 스트리밍 지원
"""

import os
import re
import time
import shutil
import logging
import threading
import subprocess
from typing import Dict, List, Any, Optional

logger = logging.getLogger("BackupSystem.DiskClone")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from core.vss_manager import VSSContext
    VSS_AVAILABLE = True
except Exception:
    VSS_AVAILABLE = False
    VSSContext = None


# 스마트 제외 패턴 (마이그레이션 대상에서 제외할 불필요한 OS 가상메모리 및 임시 파일)
DEFAULT_CLONE_EXCLUDE_FILES = [
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
    "DumpStack.log",
    "DumpStack.log.tmp",
    "*.tmp"
]

DEFAULT_CLONE_EXCLUDE_DIRS = [
    "$RECYCLE.BIN",
    "$Recycle.Bin",
    "System Volume Information",
    "WindowsImageBackup",
    "MyBackup_Repository",
    "backup_repository",
    "Temp"
]


def normalize_drive(drive_str: str) -> str:
    """'c', 'C:', 'C:\\' 등을 'C:' 표준 형식으로 정규화"""
    if not drive_str:
        return ""
    d = drive_str.strip().replace("/", "\\")
    m = re.match(r"^([A-Za-z])(?::|\\|$)", d)
    if m:
        return m.group(1).upper() + ":"
    return d.upper()


def get_candidate_target_drives() -> List[Dict[str, Any]]:
    """
    마이그레이션 대상이 될 수 있는 후보 SSD/드라이브 목록 조회
    - 현재 부팅 드라이브(C:)는 타겟 대상에서 제외
    - 총 용량, 사용량, 여유공간 및 C: 드라이브 사용량 대비 수용 가능 여부 판정
    """
    c_usage = shutil.disk_usage("C:\\")
    c_used_gb = round(c_usage.used / (1024 ** 3), 1)

    candidates = []

    if PSUTIL_AVAILABLE:
        parts = psutil.disk_partitions(all=False)
    else:
        parts = []
        for l in "DEFGHIJKLMNOPQRSTUVWXYZ":
            root = f"{l}:\\"
            if os.path.exists(root):
                parts.append(type("Obj", (), {"mountpoint": root, "fstype": "NTFS", "device": f"{l}:"})())

    for p in parts:
        drv = normalize_drive(p.mountpoint)
        if not drv or drv == "C:":
            continue

        try:
            usage = shutil.disk_usage(p.mountpoint)
            total_gb = round(usage.total / (1024 ** 3), 1)
            used_gb = round(usage.used / (1024 ** 3), 1)
            free_gb = round(usage.free / (1024 ** 3), 1)

            # 수용 가능 여부: 타겟 총 용량이 C: 드라이브 실제 사용량보다 커야 함
            is_acceptable = usage.total >= (c_usage.used * 1.05)
            reason = "정상 선택 가능" if is_acceptable else f"용량 부족 (C: 사용량 {c_used_gb} GB 대비 타겟 총용량 {total_gb} GB)"

            candidates.append({
                "drive": drv,
                "mountpoint": p.mountpoint,
                "fstype": getattr(p, "fstype", "NTFS"),
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "acceptable": is_acceptable,
                "reason": reason,
                "c_used_gb": c_used_gb
            })
        except (PermissionError, OSError):
            continue

    return candidates


class DiskCloneManager:
    """
    실시간 SSD 마이그레이션(클론) 생명주기 관리자
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DiskCloneManager, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    @classmethod
    def get_instance(cls) -> "DiskCloneManager":
        """싱글톤 인스턴스 반환"""
        return cls()

    def _init_state(self):
        self.state_lock = threading.Lock()
        self.is_running = False
        self.target_drive = ""
        self.status = "idle"  # idle, preparing, copying, bootloading, completed, failed, cancelled
        self.progress_percent = 0.0
        self.current_phase = ""
        self.error_message = ""
        self.start_time = 0.0
        self.end_time = 0.0
        self.logs: List[str] = []
        self._cancel_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

    def append_log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        with self.state_lock:
            self.logs.append(entry)
            if len(self.logs) > 500:
                self.logs.pop(0)
        try:
            logger.info(entry)
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        with self.state_lock:
            duration = round(time.time() - self.start_time, 1) if self.is_running else round(self.end_time - self.start_time, 1) if self.end_time else 0.0
            return {
                "is_running": self.is_running,
                "target_drive": self.target_drive,
                "status": self.status,
                "progress_percent": self.progress_percent,
                "current_phase": self.current_phase,
                "error_message": self.error_message,
                "duration_seconds": max(0.0, duration),
                "log_count": len(self.logs)
            }

    def get_logs(self, limit: int = 100) -> List[str]:
        with self.state_lock:
            return list(self.logs[-limit:])

    def start_clone(self, target_drive: str) -> Dict[str, Any]:
        """
        비동기 마이그레이션(클론) 시작
        """
        target = normalize_drive(target_drive)
        if not target or target == "C:":
            return {"success": False, "error": "타겟 드라이브는 C: 가 아닌 유효한 다른 드라이브여야 합니다."}

        target_root = target + "\\"
        if not os.path.exists(target_root):
            return {"success": False, "error": f"타겟 드라이브 경로({target_root})를 찾을 수 없습니다."}

        with self.state_lock:
            if self.is_running:
                return {"success": False, "error": "이미 다른 마이그레이션 또는 클론 작업이 실행 중입니다."}
            self.is_running = True
            self.target_drive = target
            self.status = "preparing"
            self.progress_percent = 1.0
            self.current_phase = "마이그레이션 준비 및 환경 검증"
            self.error_message = ""
            self.start_time = time.time()
            self.end_time = 0.0
            self.logs.clear()
            self._cancel_event.clear()

        self.append_log(f"=== Windows C: -> {target} 라이브 SSD 마이그레이션 시작 ===")
        self._worker_thread = threading.Thread(target=self._run_clone_pipeline, args=(target,), daemon=True)
        self._worker_thread.start()

        return {"success": True, "message": f"{target} 드라이브로의 마이그레이션 작업이 백그라운드에서 시작되었습니다."}

    def stop_clone(self) -> Dict[str, Any]:
        with self.state_lock:
            if not self.is_running:
                return {"success": False, "error": "현재 실행 중인 마이그레이션 작업이 없습니다."}
            self._cancel_event.set()
            self.current_phase = "작업 취소 요청 중..."

        self.append_log("[USER_CANCEL] 사용자에 의해 마이그레이션 중단이 요청되었습니다.")
        return {"success": True, "message": "마이그레이션 중단 요청이 접수되었습니다."}

    def _run_clone_pipeline(self, target_drive: str):
        target_root = target_drive + "\\"

        try:
            # 1. 사전 용량 및 쓰기 가능 여부 점검
            self.append_log("[1/4] 타겟 드라이브 용량 및 쓰기 권한 검증 중...")
            c_usage = shutil.disk_usage("C:\\")
            t_usage = shutil.disk_usage(target_root)
            c_used_gb = round(c_usage.used / (1024 ** 3), 1)
            t_total_gb = round(t_usage.total / (1024 ** 3), 1)

            self.append_log(f"  - 원본 C: 드라이브 사용량: {c_used_gb} GB")
            self.append_log(f"  - 타겟 {target_drive} 드라이브 총용량: {t_total_gb} GB")

            if t_usage.total < c_usage.used:
                raise RuntimeError(f"타겟 드라이브 용량({t_total_gb} GB)이 원본 데이터({c_used_gb} GB)보다 작아 복제를 진행할 수 없습니다.")

            # 2. VSS 볼륨 스냅샷 획득 (라이브 OS 일관성 보장)
            self.append_log("[2/4] 실시간 VSS 섀도 복사본 생성 중 (현재 실행 중인 파일/DB 정합성 보장)...")
            with self.state_lock:
                self.status = "preparing"
                self.progress_percent = 5.0
                self.current_phase = "실시간 VSS 섀도 볼륨 생성 중"

            vss_ctx = None
            source_clone_root = "C:\\"

            if VSS_AVAILABLE and VSSContext:
                try:
                    vss_ctx = VSSContext(source_paths=["C:\\"], enabled=True, strict=False)
                    vss_ctx.__enter__()
                    if vss_ctx.vss_active:
                        shadow_path = vss_ctx.get_shadow_path("C:\\")
                        if shadow_path and os.path.exists(shadow_path):
                            source_clone_root = shadow_path.rstrip("\\") + "\\"
                            self.append_log(f"  - VSS 섀도 볼륨 바인딩 성공: {source_clone_root}")
                except Exception as e_vss:
                    self.append_log(f"  - [주의] VSS 섀도 생성 실패 ({e_vss}). 직접 볼륨 읽기로 진행합니다.")
                    vss_ctx = None

            # 3. Robocopy 고속 멀티스레드 미러링 복사
            self.append_log(f"[3/4] 다이렉트 파일 복제 시작: {source_clone_root} -> {target_root}")
            with self.state_lock:
                self.status = "copying"
                self.progress_percent = 10.0
                self.current_phase = "데이터 미러링 복제 진행 중 (Robocopy /MIR)"

            # Robocopy 명령어 조립
            cmd = [
                "robocopy",
                source_clone_root,
                target_root,
                "/MIR",              # 미러링 (원본과 100% 동일 동기화)
                "/COPY:DAT",         # 데이터, 속성, 타임스탬프 복제
                "/DCOPY:DAT",        # 디렉토리 타임스탬프 복제
                "/R:1",              # 재시도 1회
                "/W:1",              # 대기 1초
                "/XJ",               # 심볼릭/정션 루프 방지
                "/SL",               # 심볼릭 링크 자체 복사
                "/MT:8",             # 8코어 멀티스레드 고속 복사
                "/NP",               # 콘솔 진행률 스팸 억제
                "/NDL"               # 디렉토리명 출력 억제
            ]

            # 제외 파일 및 디렉토리 플래그 추가
            if DEFAULT_CLONE_EXCLUDE_FILES:
                cmd.append("/XF")
                cmd.extend(DEFAULT_CLONE_EXCLUDE_FILES)
            if DEFAULT_CLONE_EXCLUDE_DIRS:
                cmd.append("/XD")
                cmd.extend(DEFAULT_CLONE_EXCLUDE_DIRS)

            self.append_log(f"  - Robocopy 실행: {' '.join(cmd[:6])} ...")

            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="cp949",
                errors="ignore",
                creationflags=creationflags
            )

            # 진행률 추정 및 로그 스트리밍
            start_copy_ts = time.time()

            while proc.poll() is None:
                if self._cancel_event.is_set():
                    proc.terminate()
                    time.sleep(1)
                    if proc.poll() is None:
                        proc.kill()
                    raise RuntimeError("사용자에 의해 마이그레이션이 취소되었습니다.")

                # 주기적 상태 갱신
                elapsed = time.time() - start_copy_ts
                with self.state_lock:
                    # 복사 단계 진행률: 10% ~ 85% 구간 점진적 진행
                    if self.progress_percent < 85.0:
                        self.progress_percent = min(85.0, round(10.0 + (elapsed * 0.5), 1))

                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("---") and not stripped.startswith("==="):
                        # 중요 로그 라인만 캡처
                        if any(k in stripped for k in ("ERROR", "오류", "100%", "새 파일", "New File")):
                            self.append_log(f"    {stripped[:100]}")

                time.sleep(0.5)

            rc = proc.returncode
            # Robocopy 리턴코드 규칙: 0~7은 성공(파일 복사됨/일부 동일), 8 이상은 치명적 실패
            if rc is not None and rc >= 8:
                raise RuntimeError(f"Robocopy 복제 실패 (Exit Code: {rc}).")
            self.append_log(f"  - Robocopy 복제 성공 완료 (Exit Code: {rc})")

            # VSS Fast-Release 해제
            if vss_ctx:
                try:
                    vss_ctx.__exit__(None, None, None)
                    self.append_log("  - VSS 섀도 볼륨 안전 해제 완료.")
                except Exception as e_vss_close:
                    self.append_log(f"  - VSS 해제 알림: {e_vss_close}")

            # 4. 부트로더 자동 주입 (bcdboot)
            self.append_log(f"[4/4] 부트 매니저(BCD) 주입 중: bcdboot {target_root}Windows ...")
            with self.state_lock:
                self.status = "bootloading"
                self.progress_percent = 90.0
                self.current_phase = "새 SSD에 UEFI/BIOS 부트로더 주입 중"

            bcd_cmd = [
                "bcdboot",
                os.path.join(target_root, "Windows"),
                "/s", target_drive,
                "/f", "ALL"
            ]
            self.append_log(f"  - 실행: {' '.join(bcd_cmd)}")

            bcd_res = subprocess.run(
                bcd_cmd,
                capture_output=True,
                text=True,
                encoding="cp949",
                errors="ignore",
                creationflags=creationflags
            )

            bcd_out = (bcd_res.stdout or "") + (bcd_res.stderr or "")
            self.append_log(f"  - bcdboot 결과: {bcd_out.strip() or '정상 완료'}")

            # 5. 최종 완료
            with self.state_lock:
                self.status = "completed"
                self.progress_percent = 100.0
                self.is_running = False
                self.end_time = time.time()
                self.current_phase = "마이그레이션 완료 (부팅 준비 완료)"

            self.append_log("============================================================")
            self.append_log(f"[성공] {target_drive} 드라이브로의 SSD 마이그레이션이 성공적으로 완료되었습니다!")
            self.append_log("[부팅 안내] PC를 재부팅하고 바이오스(BIOS/UEFI) 진입 후,")
            self.append_log(f"    부팅 1순위를 새로 복제된 SSD({target_drive})로 지정하시면 즉시 부팅됩니다.")
            self.append_log("============================================================")

        except Exception as e:
            err_msg = str(e)
            self.append_log(f"[MIGRATION ERROR] {err_msg}")
            with self.state_lock:
                self.status = "cancelled" if self._cancel_event.is_set() else "failed"
                self.is_running = False
                self.end_time = time.time()
                self.error_message = err_msg
                self.current_phase = f"오류 발생: {err_msg}"
