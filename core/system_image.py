import os
import sys
import time
import json
import shutil
import ctypes
import subprocess
import datetime
import threading
from typing import Dict, Any, Optional, Callable, List

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
                    ps_cmd = f"Start-Process cmd -ArgumentList '/c chcp 65001 >nul && wbadmin start backup -backupTarget:{target_drive} -include:C: -allCritical -quiet > \"{log_file}\" 2>&1' -WindowStyle Hidden -Verb RunAs -Wait"
                    
                    p_flags = 0
                    if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
                        p_flags = subprocess.CREATE_NO_WINDOW
                    p = subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd], creationflags=p_flags)
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
                    popen_kwargs = {
                        "stdout": subprocess.PIPE,
                        "stderr": subprocess.STDOUT,
                        "text": True,
                        "encoding": "utf-8",
                        "errors": "replace"
                    }
                    if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
                        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                    p = subprocess.Popen(
                        ["wbadmin", "start", "backup", f"-backupTarget:{target_drive}", "-include:C:", "-allCritical", "-quiet"],
                        **popen_kwargs
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
                else:
                    cls.append_log(f"백업이 종료되었습니다 (코드: {ret_code}). 로그를 확인하세요.", level="WARNING")

            except Exception as e:
                cls.append_log(f"시스템 이미지 백업 중 오류 발생: {str(e)}", level="ERROR")
            finally:
                with cls._lock:
                    if cls._process and cls._process.poll() is None:
                        try:
                            cls._process.terminate()
                            cls._process.wait(timeout=5)
                        except Exception:
                            pass
                    cls._is_running = False
                    cls._process = None

        t = threading.Thread(target=_run_worker, daemon=True)
        t.start()
        return {"success": True, "message": "시스템 이미지 백업 작업이 시작되었습니다."}

    @classmethod
    def stop_backup(cls) -> Dict[str, Any]:
        cls.append_log("백업 중단 명령을 전송합니다...")
        try:
            kwargs = {"capture_output": True, "text": True}
            if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.run(["wbadmin", "stop", "job", "-quiet"], **kwargs)
            with cls._lock:
                if cls._process:
                    cls._process.terminate()
                    try:
                        cls._process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        cls._process.kill()
                        cls._process.wait()
                cls._is_running = False
            cls.append_log("백업 작업이 중단되었습니다.", level="WARNING")
            return {"success": True, "message": "백업 작업 중단 요청 완료"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def list_vhdx_images(cls, search_drive: str = "D:") -> List[Dict[str, Any]]:
        """
        지정 드라이브(기본 D:) 및 WindowsImageBackup 내의 VHDX 이미지들을 탐색하고
        각 파일의 마운트 상태와 볼륨 정보를 반환.
        """
        search_drive = search_drive.rstrip("\\/") + "\\"
        results = []
        target_dir = os.path.join(search_drive, "WindowsImageBackup")
        if not os.path.exists(target_dir):
            return results

        # 현재 마운트된 디스크 이미지 정보 수집
        mounted_map = cls._get_all_mounted_images()

        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith(".vhdx"):
                    full_path = os.path.join(root, file)
                    try:
                        sz = os.path.getsize(full_path)
                        mtime = os.path.getmtime(full_path)
                        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        
                        norm_path = os.path.normpath(full_path).lower()
                        mount_info = mounted_map.get(norm_path, None)

                        results.append({
                            "path": full_path,
                            "filename": file,
                            "size_bytes": sz,
                            "size_gb": round(sz / (1024 ** 3), 2),
                            "modified_at": mtime_str,
                            "is_mounted": bool(mount_info and mount_info.get("attached")),
                            "mount_drive": mount_info.get("drive_letter") if mount_info else None
                        })
                    except OSError:
                        continue

        # 최신 파일 순으로 정렬
        results.sort(key=lambda x: x["modified_at"], reverse=True)
        return results

    @classmethod
    def _get_all_mounted_images(cls) -> Dict[str, Dict[str, Any]]:
        """현재 시스템에 마운트된 모든 VHD/VHDX 이미지 맵 반환 (소문자 정규화 경로 -> 정보)"""
        if sys.platform != "win32":
            return {}

        ps_script = (
            "Get-DiskImage -ErrorAction SilentlyContinue | "
            "ForEach-Object { "
            "  $img = $_; "
            "  $vol = $img | Get-Volume -ErrorAction SilentlyContinue; "
            "  [PSCustomObject]@{ "
            "    ImagePath = $img.ImagePath; "
            "    Attached = $img.Attached; "
            "    DriveLetter = if ($vol) { $vol.DriveLetter } else { $null } "
            "  } "
            "} | ConvertTo-Json -Compress"
        )
        try:
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                creationflags=flags
            )
            if res.returncode != 0 or not res.stdout.strip():
                return {}
            data = json.loads(res.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            out = {}
            for item in data:
                ipath = item.get("ImagePath")
                if ipath:
                    norm = os.path.normpath(ipath).lower()
                    dl = item.get("DriveLetter")
                    out[norm] = {
                        "attached": item.get("Attached", False),
                        "drive_letter": f"{dl}:" if dl else None
                    }
            return out
        except Exception as e:
            cls.append_log(f"마운트된 디스크 이미지 조회 예외: {e}", level="WARNING")
            return {}

    @classmethod
    def mount_vhdx(cls, vhdx_path: str, read_only: bool = True) -> Dict[str, Any]:
        """
        VHDX 이미지를 읽기 전용으로 안전하게 가상 드라이브에 마운트.
        """
        if not os.path.exists(vhdx_path):
            return {"success": False, "error": f"VHDX 파일을 찾을 수 없습니다: {vhdx_path}"}

        access_opt = "-Access ReadOnly" if read_only else ""
        escaped_path = vhdx_path.replace("'", "''")
        ps_script = (
            f"$p = '{escaped_path}'; "
            f"$img = Mount-DiskImage -ImagePath $p {access_opt} -PassThru; "
            f"$vol = $img | Get-Volume -ErrorAction SilentlyContinue; "
            f"[PSCustomObject]@{{"
            f"  Attached = $img.Attached; "
            f"  DriveLetter = if ($vol) {{ $vol.DriveLetter }} else {{ $null }} "
            f"}} | ConvertTo-Json -Compress"
        )

        try:
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                creationflags=flags
            )
            if res.returncode != 0:
                return {"success": False, "error": f"VHDX 마운트 실패: {res.stderr.strip() or res.stdout.strip()}"}
            
            data = json.loads(res.stdout.strip())
            drive_letter = data.get("DriveLetter")
            drive_str = f"{drive_letter}:" if drive_letter else "마운트됨(문자 미할당)"
            cls.append_log(f"VHDX 마운트 성공 ({drive_str}): {vhdx_path}", level="SUCCESS")
            return {
                "success": True,
                "message": f"성공적으로 마운트되었습니다 ({drive_str}).",
                "drive_letter": drive_str,
                "attached": data.get("Attached", True)
            }
        except Exception as e:
            return {"success": False, "error": f"VHDX 마운트 중 오류 발생: {str(e)}"}

    @classmethod
    def dismount_vhdx(cls, vhdx_path: str) -> Dict[str, Any]:
        """
        마운트된 VHDX 이미지 안전 분리(언마운트).
        """
        if not os.path.exists(vhdx_path):
            return {"success": False, "error": f"VHDX 파일을 찾을 수 없습니다: {vhdx_path}"}

        escaped_path = vhdx_path.replace("'", "''")
        ps_script = f"Dismount-DiskImage -ImagePath '{escaped_path}'"

        try:
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                creationflags=flags
            )
            if res.returncode == 0:
                cls.append_log(f"VHDX 언마운트 완료: {vhdx_path}", level="INFO")
                return {"success": True, "message": "VHDX가 안전하게 언마운트되었습니다."}
            else:
                return {"success": False, "error": f"VHDX 언마운트 실패: {res.stderr.strip()}"}
        except Exception as e:
            return {"success": False, "error": f"VHDX 언마운트 중 오류: {str(e)}"}
