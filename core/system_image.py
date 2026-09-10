import os
import sys
import time
import shutil
import ctypes
import subprocess
import datetime
import threading
from typing import Dict, Any, Optional, Callable

class SystemImageManager:
    _lock = threading.Lock()
    _is_running = False
    _logs = []
    _process = None

    @classmethod
    def is_admin(cls) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @classmethod
    def get_status(cls, target_drive: str = "D:") -> Dict[str, Any]:
        target_drive = target_drive.rstrip("\\/")
        if not target_drive.endswith(":"):
            target_drive += ":"

        # 1. Disk usage
        try:
            c_total, c_used, c_free = shutil.disk_usage("C:\\")
        except Exception:
            c_total, c_used, c_free = 0, 0, 0

        try:
            d_total, d_used, d_free = shutil.disk_usage(target_drive + "\\")
        except Exception:
            d_total, d_used, d_free = 0, 0, 0

        # 2. Check WindowsImageBackup folder
        backup_folder = os.path.join(target_drive + "\\", "WindowsImageBackup")
        has_backup = os.path.exists(backup_folder)
        backup_size = 0
        last_modified = None

        if has_backup:
            try:
                # Fast calculation or folder mtime
                mtime = os.path.getmtime(backup_folder)
                last_modified = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                # Calculate size of top-level directory files
                total_sz = 0
                for root, dirs, files in os.walk(backup_folder):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            total_sz += os.path.getsize(fp)
                        except OSError:
                            pass
                backup_size = total_sz
            except Exception:
                pass

        return {
            "target_drive": target_drive,
            "is_admin": cls.is_admin(),
            "is_running": cls._is_running,
            "c_drive": {
                "total_bytes": c_total,
                "used_bytes": c_used,
                "free_bytes": c_free,
                "used_gb": round(c_used / (1024 ** 3), 1),
                "total_gb": round(c_total / (1024 ** 3), 1)
            },
            "target_drive_info": {
                "drive": target_drive,
                "total_bytes": d_total,
                "used_bytes": d_used,
                "free_bytes": d_free,
                "free_gb": round(d_free / (1024 ** 3), 1),
                "total_gb": round(d_total / (1024 ** 3), 1),
                "sufficient_space": d_free > (c_used * 0.7) # Image is compressed ~50-70%
            },
            "backup_info": {
                "exists": has_backup,
                "path": backup_folder,
                "last_modified": last_modified,
                "size_bytes": backup_size,
                "size_gb": round(backup_size / (1024 ** 3), 2)
            }
        }

    @classmethod
    def append_log(cls, msg: str, level: str = "INFO"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] [{level}] {msg}"
        with cls._lock:
            cls._logs.append(entry)
            if len(cls._logs) > 500:
                cls._logs.pop(0)

    @classmethod
    def get_logs(cls) -> Dict[str, Any]:
        with cls._lock:
            return {
                "is_running": cls._is_running,
                "logs": list(cls._logs)
            }

    @classmethod
    def start_backup(cls, target_drive: str = "D:", log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        with cls._lock:
            if cls._is_running:
                return {"success": False, "error": "이미 윈도우 시스템 이미지 백업이 진행 중입니다."}
            cls._is_running = True
            cls._logs.clear()

        target_drive = target_drive.rstrip("\\/")
        if not target_drive.endswith(":"):
            target_drive += ":"

        def _run_worker():
            t_start = time.time()
            try:
                cls.append_log(f"윈도우 베어메탈 시스템 이미지 백업을 시작합니다 (대상: {target_drive})...")
                cls.append_log("부팅(EFI) 파티션, 복구 파티션 및 C: 드라이브 전체 캡처를 준비합니다.")

                cmd = f"wbadmin start backup -backupTarget:{target_drive} -include:C: -allCritical -quiet"
                cls.append_log(f"실행 명령: {cmd}")

                # Check admin elevation
                if not cls.is_admin():
                    cls.append_log("관리자 권한 승격(UAC)을 요청하여 백업을 백그라운드에서 실행합니다...", level="WARNING")
                    # Run via elevated PowerShell script that redirects output to log file
                    log_file = os.path.join(target_drive + "\\", "system_image_backup.log")
                    ps_cmd = f"Start-Process cmd -ArgumentList '/c chcp 65001 >nul && wbadmin start backup -backupTarget:{target_drive} -include:C: -allCritical -quiet > \"{log_file}\" 2>&1' -Verb RunAs -Wait"
                    
                    p = subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd])
                    cls._process = p
                    
                    # Monitor log file while running
                    last_pos = 0
                    while p.poll() is None:
                        time.sleep(2)
                        if os.path.exists(log_file):
                            try:
                                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                                    f.seek(last_pos)
                                    new_lines = f.readlines()
                                    last_pos = f.tell()
                                    for line in new_lines:
                                        l = line.strip()
                                        if l:
                                            cls.append_log(l)
                                            if log_callback:
                                                log_callback(l)
                            except Exception:
                                pass

                    ret_code = p.returncode
                    cls.append_log(f"백업 작업 프로세스 종료 코드: {ret_code}")
                else:
                    # Run directly
                    p = subprocess.Popen(
                        ["wbadmin", "start", "backup", f"-backupTarget:{target_drive}", "-include:C:", "-allCritical", "-quiet"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace"
                    )
                    cls._process = p
                    for line in p.stdout:
                        line_str = line.strip()
                        if line_str:
                            cls.append_log(line_str)
                            if log_callback:
                                log_callback(line_str)

                    p.wait()
                    ret_code = p.returncode

                if ret_code == 0:
                    elapsed_min = round((time.time() - t_start) / 60, 1)
                    cls.append_log(f"🎉 윈도우 전체 베어메탈 시스템 이미지 백업이 성공적으로 완료되었습니다! (소요 시간: {elapsed_min}분)", level="SUCCESS")
                    try:
                        from core.notifier import send_kakao_message
                        msg = (
                            f"💻 [백업 시스템] Windows 베어메탈 이미지 백업 완료!\n"
                            f"━━━━━━━━━━━━━━━━━━━━━\n"
                            f"• 대상 드라이브: C: 전체 (EFI/복구 파티션 포함)\n"
                            f"• 백업 저장 위치: {target_drive}\\WindowsImageBackup\n"
                            f"• 상태: 정상 완료 ✅\n"
                            f"• 소요 시간: {elapsed_min}분\n"
                            f"• 완료 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━"
                        )
                        send_kakao_message(msg)
                    except Exception:
                        pass
                else:
                    cls.append_log(f"백업이 종료되었습니다 (코드: {ret_code}). 로그를 확인하세요.", level="WARNING")
                    try:
                        from core.notifier import send_kakao_message
                        msg = (
                            f"⚠️ [백업 시스템] Windows 시스템 이미지 백업 알림\n"
                            f"━━━━━━━━━━━━━━━━━━━━━\n"
                            f"• 상태: 비정상 종료 (코드: {ret_code}) ❌\n"
                            f"• 대상 드라이브: {target_drive}\n"
                            f"• 발생 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━"
                        )
                        send_kakao_message(msg)
                    except Exception:
                        pass

            except Exception as e:
                cls.append_log(f"시스템 이미지 백업 중 오류 발생: {str(e)}", level="ERROR")
                try:
                    from core.notifier import send_kakao_message
                    send_kakao_message(f"⚠️ [백업 시스템] 시스템 이미지 백업 오류 발생:\n{str(e)}")
                except Exception:
                    pass
            finally:
                with cls._lock:
                    cls._is_running = False
                    cls._process = None

        t = threading.Thread(target=_run_worker, daemon=True)
        t.start()
        return {"success": True, "message": "시스템 이미지 백업 작업이 시작되었습니다."}

    @classmethod
    def stop_backup(cls) -> Dict[str, Any]:
        cls.append_log("백업 중단 명령을 전송합니다...")
        try:
            subprocess.run(["wbadmin", "stop", "job", "-quiet"], capture_output=True, text=True)
            with cls._lock:
                if cls._process:
                    cls._process.terminate()
                cls._is_running = False
            cls.append_log("백업 작업이 중단되었습니다.", level="WARNING")
            return {"success": True, "message": "백업 작업 중단 요청 완료"}
        except Exception as e:
            return {"success": False, "error": str(e)}
