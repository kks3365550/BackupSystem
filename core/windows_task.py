import os
import sys
import subprocess
from typing import Dict, Any, Optional

TASK_NAME = "BackupSystem_AutoBackup"

def get_python_executable() -> str:
    # Prefer pythonw if available so no black window appears at all
    py_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(py_dir, "pythonw.exe")
    if os.path.exists(pythonw):
        return pythonw
    return sys.executable

def register_windows_scheduled_task(profile_id: Optional[str] = None, schedule_type: str = "daily", schedule_value: str = "03:00") -> Dict[str, Any]:
    """
    Registers or updates a scheduled task in Windows Task Scheduler (schtasks.exe).
    This allows Windows OS to wake up and run the backup without needing Python to run in the background 24/7!
    """
    if not sys.platform.startswith("win"):
        return {"success": False, "error": "Windows OS is required for Task Scheduler."}

    py_exe = get_python_executable()
    cli_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cli_backup.py"))
    
    task_run_cmd = f'"{py_exe}" "{cli_py}"'
    if profile_id:
        task_run_cmd += f' --profile "{profile_id}"'

    cmd = ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", task_run_cmd, "/F"]

    if schedule_type == "daily":
        # schedule_value is HH:MM e.g. "03:00"
        time_str = schedule_value.strip() if ":" in schedule_value else f"{int(schedule_value):02d}:00"
        cmd.extend(["/SC", "DAILY", "/ST", time_str])
    elif schedule_type == "interval_hours":
        try:
            hours = int(float(schedule_value))
            if hours >= 24:
                cmd.extend(["/SC", "DAILY", "/ST", "03:00"])
            else:
                cmd.extend(["/SC", "HOURLY", "/MO", str(hours)])
        except ValueError:
            cmd.extend(["/SC", "DAILY", "/ST", "03:00"])
    else:
        cmd.extend(["/SC", "DAILY", "/ST", "03:00"])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode == 0:
            return {
                "success": True,
                "task_name": TASK_NAME,
                "command": task_run_cmd,
                "schedule_type": schedule_type,
                "schedule_value": schedule_value,
                "message": f"Windows 작업 스케줄러에 등록 완료 ({schedule_type} {schedule_value})"
            }
        else:
            return {
                "success": False,
                "error": proc.stderr.strip() or proc.stdout.strip()
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def unregister_windows_scheduled_task() -> Dict[str, Any]:
    """
    Deletes the task from Windows Task Scheduler.
    """
    if not sys.platform.startswith("win"):
        return {"success": False, "error": "Windows OS required."}

    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return {
            "success": proc.returncode == 0,
            "message": "Windows 작업 스케줄러에서 등록 해제되었습니다."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_windows_scheduled_task_status() -> Dict[str, Any]:
    """
    Queries current task status from Windows Task Scheduler.
    """
    if not sys.platform.startswith("win"):
        return {"registered": False, "status": "Not Windows"}

    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            lines = proc.stdout.splitlines()
            info = {}
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    info[parts[0].strip()] = parts[1].strip()
            
            return {
                "registered": True,
                "task_name": TASK_NAME,
                "status": info.get("작업 상태", info.get("Status", "등록됨")),
                "next_run": info.get("다음 실행 시간", info.get("Next Run Time", "-")),
                "last_run": info.get("마지막 실행 시간", info.get("Last Run Time", "-")),
                "last_result": info.get("마지막 결과", info.get("Last Result", "-")),
                "raw": info
            }
        else:
            return {"registered": False, "status": "미등록"}
    except Exception as e:
        return {"registered": False, "error": str(e)}
