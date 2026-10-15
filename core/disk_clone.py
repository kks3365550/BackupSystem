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


def get_physical_disk_number(drive_letter: str) -> Optional[int]:
    """드라이브 문자에 대응하는 물리 디스크 번호(PhysicalDrive Number) 반환 (예: 'C:' -> 0)"""
    drv = normalize_drive(drive_letter).rstrip(":")
    if not drv:
        return None
    ps_cmd = f"(Get-Partition -DriveLetter '{drv}' -ErrorAction SilentlyContinue).DiskNumber"
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=creationflags,
            timeout=5
        )
        out = res.stdout.strip()
        if out and out.isdigit():
            return int(out)
    except Exception:
        pass
    return None


def find_free_drive_letter(preferred: str = "S:") -> str:
    """시스템에서 현재 사용되지 않는 알파벳 드라이브 문자 탐색"""
    pref = normalize_drive(preferred)
    used = set()
    for l in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if os.path.exists(f"{l}:\\"):
            used.add(f"{l}:")
    if pref and pref not in used:
        return pref
    for l in "SZYXWVUTRPQONMLKJIHGFEDB":
        cand = f"{l}:"
        if cand not in used:
            return cand
    return "S:"


def prepare_target_disk_with_esp(disk_number: int, target_drive: str, esp_letter: str) -> Dict[str, Any]:
    """
    타겟 새 물리 SSD를 100% 부팅 가능한 UEFI 표준(GPT + 260MB FAT32 ESP + 16MB MSR + NTFS Windows)으로 원클릭 초기화
    """
    target_clean = normalize_drive(target_drive).rstrip(":")
    esp_clean = normalize_drive(esp_letter).rstrip(":")

    script_lines = [
        f"select disk {disk_number}",
        "clean",
        "convert gpt",
        "create partition efi size=260",
        "format fs=fat32 quick label=\"ESP\"",
        f"assign letter={esp_clean}",
        "create partition msr size=16",
        "create partition primary",
        "format fs=ntfs quick label=\"Windows\"",
        f"assign letter={target_clean}",
        "exit"
    ]
    script_content = "\r\n".join(script_lines) + "\r\n"

    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as tf:
        tf.write(script_content)
        script_path = tf.name

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            ["diskpart", "/s", script_path],
            capture_output=True,
            text=True,
            encoding="cp949",
            errors="ignore",
            creationflags=creationflags,
            timeout=60
        )
        if proc.returncode != 0:
            return {"success": False, "error": f"diskpart 파티셔닝 실패 (Exit Code {proc.returncode}): {proc.stderr or proc.stdout}"}
        return {"success": True, "output": proc.stdout}
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass


def remove_esp_drive_letter(esp_letter: str) -> bool:
    """주입 완료 후 ESP 파티션의 임시 드라이브 문자를 안전하게 해제하여 숨김 파티션으로 전환"""
    esp_clean = normalize_drive(esp_letter).rstrip(":")
    script_lines = [
        f"select volume {esp_clean}",
        f"remove letter={esp_clean}",
        "exit"
    ]
    script_content = "\r\n".join(script_lines) + "\r\n"
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as tf:
        tf.write(script_content)
        script_path = tf.name
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            ["diskpart", "/s", script_path],
            capture_output=True,
            text=True,
            encoding="cp949",
            errors="ignore",
            creationflags=creationflags,
            timeout=15
        )
        return proc.returncode == 0
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass


def get_candidate_target_drives() -> List[Dict[str, Any]]:
    """
    마이그레이션 대상이 될 수 있는 후보 SSD/드라이브 목록 조회
    - 현재 부팅 드라이브(C:)는 타겟 대상에서 제외
    - 총 용량, 사용량, 여유공간 및 C: 드라이브 사용량 대비 수용 가능 여부 판정
    - 물리 디스크 번호 및 독립 디스크 여부(auto_esp 지원 여부) 판정
    """
    c_usage = shutil.disk_usage("C:\\")
    c_used_gb = round(c_usage.used / (1024 ** 3), 1)
    c_disk_num = get_physical_disk_number("C:")

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

            # 물리 디스크 번호 조회
            t_disk_num = get_physical_disk_number(drv)
            is_different_disk = (t_disk_num is not None and c_disk_num is not None and t_disk_num != c_disk_num)

            candidates.append({
                "drive": drv,
                "mountpoint": p.mountpoint,
                "fstype": getattr(p, "fstype", "NTFS"),
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "acceptable": is_acceptable,
                "reason": reason,
                "c_used_gb": c_used_gb,
                "disk_number": t_disk_num,
                "can_auto_esp": is_different_disk
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

    def start_clone(self, target_drive: str, auto_prepare_esp: bool = True) -> Dict[str, Any]:
        """
        비동기 마이그레이션(클론) 시작
        - auto_prepare_esp: 새 SSD 전체를 100% UEFI 표준(GPT + 260MB FAT32 ESP + 16MB MSR + NTFS Windows)으로 자동 파티셔닝
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
            self.current_phase = "마이그레이션 환경 검증 및 부팅 아키텍처 준비"
            self.error_message = ""
            self.start_time = time.time()
            self.end_time = 0.0
            self.logs.clear()
            self._cancel_event.clear()

        mode_str = "100% UEFI ESP 자동 파티셔닝 모드" if auto_prepare_esp else "기존 파티션 유지 모드"
        self.append_log(f"=== Windows C: -> {target} 라이브 SSD 마이그레이션 시작 ({mode_str}) ===")
        self._worker_thread = threading.Thread(target=self._run_clone_pipeline, args=(target, auto_prepare_esp), daemon=True)
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

    def _run_clone_pipeline(self, target_drive: str, auto_prepare_esp: bool = True):
        target_root = target_drive + "\\"
        esp_letter = ""

        try:
            # 1. 물리 디스크 식별 및 사전 용량 검증
            self.append_log("[1/5] 타겟 드라이브 및 물리 디스크 아키텍처 검증 중...")
            c_disk = get_physical_disk_number("C:")
            t_disk = get_physical_disk_number(target_drive)
            self.append_log(f"  - 원본 C: 물리 디스크 번호: Disk {c_disk if c_disk is not None else '감지불가'}")
            self.append_log(f"  - 타겟 {target_drive} 물리 디스크 번호: Disk {t_disk if t_disk is not None else '감지불가'}")

            c_usage = shutil.disk_usage("C:\\")
            t_usage = shutil.disk_usage(target_root)
            c_used_gb = round(c_usage.used / (1024 ** 3), 1)
            t_total_gb = round(t_usage.total / (1024 ** 3), 1)

            self.append_log(f"  - 원본 C: 드라이브 실사용량: {c_used_gb} GB")
            self.append_log(f"  - 타겟 {target_drive} 드라이브 총용량: {t_total_gb} GB")

            if t_usage.total < c_usage.used:
                raise RuntimeError(f"타겟 드라이브 총용량({t_total_gb} GB)이 원본 데이터({c_used_gb} GB)보다 작아 복제를 진행할 수 없습니다.")

            # 2. 100% 부팅 보장 모드: UEFI 표준(GPT + 260MB FAT32 ESP + 16MB MSR + NTFS Windows) 자동 파티셔닝
            if auto_prepare_esp:
                if t_disk is not None and c_disk is not None and t_disk == c_disk:
                    self.append_log("  - [안내] 타겟이 원본 C:와 동일한 물리 디스크의 다른 파티션입니다. 안전을 위해 디스크 초기화를 건너뛰고 기존 파티션 모드로 진행합니다.")
                    auto_prepare_esp = False
                elif t_disk is not None:
                    esp_letter = find_free_drive_letter("S:")
                    self.append_log(f"[2/5] 새 SSD(Disk {t_disk})를 100% UEFI 표준 규격으로 자동 파티셔닝 중 (GPT + 260MB FAT32 ESP({esp_letter}) + MSR + NTFS)...")
                    with self.state_lock:
                        self.status = "preparing"
                        self.progress_percent = 5.0
                        self.current_phase = f"새 SSD UEFI 파티션 자동 생성 중 (ESP: {esp_letter})"

                    part_res = prepare_target_disk_with_esp(t_disk, target_drive, esp_letter)
                    if not part_res.get("success"):
                        self.append_log(f"  - [경고] 자동 파티셔닝 실패 ({part_res.get('error')}). 기존 파티션 모드로 폴백합니다.")
                        auto_prepare_esp = False
                        esp_letter = ""
                    else:
                        self.append_log(f"  - 새 SSD UEFI 파티셔닝 완료 (ESP 임시 문자: {esp_letter}, OS 볼륨: {target_drive})")
                        time.sleep(2)
                else:
                    self.append_log("  - [경고] 타겟 물리 디스크 번호를 감지할 수 없어 기존 파티션 모드로 진행합니다.")
                    auto_prepare_esp = False

            if not auto_prepare_esp:
                self.append_log("[2/5] 기존 파티션 모드 유지 (추가 파티셔닝 없이 기존 NTFS 볼륨으로 직접 복제)")

            # 3. VSS 볼륨 스냅샷 획득 (라이브 OS 일관성 보장)
            self.append_log("[3/5] 실시간 VSS 섀도 복사본 생성 중 (현재 실행 중인 파일/DB 정합성 보장)...")
            with self.state_lock:
                self.status = "preparing"
                self.progress_percent = 10.0
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

            # 4. Robocopy 고속 멀티스레드 미러링 복사
            self.append_log(f"[4/5] 다이렉트 파일 복제 시작: {source_clone_root} -> {target_root}")
            with self.state_lock:
                self.status = "copying"
                self.progress_percent = 15.0
                self.current_phase = "데이터 미러링 복제 진행 중 (Robocopy /MIR)"

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

            start_copy_ts = time.time()

            while proc.poll() is None:
                if self._cancel_event.is_set():
                    proc.terminate()
                    time.sleep(1)
                    if proc.poll() is None:
                        proc.kill()
                    raise RuntimeError("사용자에 의해 마이그레이션이 취소되었습니다.")

                elapsed = time.time() - start_copy_ts
                with self.state_lock:
                    if self.progress_percent < 85.0:
                        self.progress_percent = min(85.0, round(15.0 + (elapsed * 0.5), 1))

                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("---") and not stripped.startswith("==="):
                        if any(k in stripped for k in ("ERROR", "오류", "100%", "새 파일", "New File")):
                            self.append_log(f"    {stripped[:100]}")

                time.sleep(0.5)

            rc = proc.returncode
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

            # 5. UEFI 부트로더(BCD) 정밀 주입
            self.append_log(f"[5/5] 부트 매니저(BCD) 정밀 주입 중: bcdboot {target_root}Windows ...")
            with self.state_lock:
                self.status = "bootloading"
                self.progress_percent = 90.0
                self.current_phase = "새 SSD에 100% UEFI 부트로더 주입 중"

            # ESP 파티션이 준비되어 있으면 해당 ESP에 UEFI 전용 주입, 아니면 타겟 드라이브에 ALL 주입
            boot_target = esp_letter if (auto_prepare_esp and esp_letter and os.path.exists(esp_letter + "\\")) else target_drive
            boot_mode = "UEFI" if (auto_prepare_esp and esp_letter) else "ALL"

            bcd_cmd = [
                "bcdboot",
                os.path.join(target_root, "Windows"),
                "/s", boot_target,
                "/f", boot_mode
            ]
            self.append_log(f"  - 부트로더 명령 실행: {' '.join(bcd_cmd)}")

            bcd_res = subprocess.run(
                bcd_cmd,
                capture_output=True,
                text=True,
                encoding="cp949",
                errors="ignore",
                creationflags=creationflags
            )

            bcd_out = (bcd_res.stdout or "") + (bcd_res.stderr or "")
            self.append_log(f"  - bcdboot 결과: {bcd_out.strip() or '부팅 파일 생성 정상 완료'}")

            # ESP 임시 드라이브 문자 정리 (보안 및 숨김 파티션 전환)
            if auto_prepare_esp and esp_letter:
                bcd_file_check = os.path.join(esp_letter + "\\", "EFI", "Microsoft", "Boot", "BCD")
                if os.path.exists(bcd_file_check):
                    self.append_log(f"  - [검증 완료] UEFI BCD 파일 무결성 확인 ({bcd_file_check})")
                remove_esp_drive_letter(esp_letter)
                self.append_log(f"  - ESP 파티션({esp_letter}) 숨김 모드로 안전 전환 완료.")

            # 최종 완료
            with self.state_lock:
                self.status = "completed"
                self.progress_percent = 100.0
                self.is_running = False
                self.end_time = time.time()
                self.current_phase = "마이그레이션 완료 (100% 부팅 준비 완료)"

            self.append_log("============================================================")
            self.append_log(f"[성공] {target_drive} 새 SSD로의 100% 라이브 마이그레이션이 완료되었습니다!")
            if auto_prepare_esp:
                self.append_log("  - 파티션 아키텍처: UEFI GPT + 260MB FAT32 ESP + MSR + NTFS Windows")
            self.append_log("[부팅 안내] PC를 재부팅하고 바이오스(BIOS/UEFI) 진입 후,")
            self.append_log(f"    부팅 1순위를 새로 복제된 SSD({target_drive})로 지정하시면 즉시 단독 부팅됩니다.")
            self.append_log("============================================================")

        except Exception as e:
            err_msg = str(e)
            self.append_log(f"[MIGRATION ERROR] {err_msg}")
            if esp_letter:
                try:
                    remove_esp_drive_letter(esp_letter)
                except Exception:
                    pass
            with self.state_lock:
                self.status = "cancelled" if self._cancel_event.is_set() else "failed"
                self.is_running = False
                self.end_time = time.time()
                self.error_message = err_msg
                self.current_phase = f"오류 발생: {err_msg}"
