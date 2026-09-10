import time
import threading
import datetime
from typing import Dict, Any, Optional, Callable
from core.config import ConfigManager
from core.snapshot import SnapshotEngine

class BackupScheduler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BackupScheduler, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.log_callbacks: list = []
        self.stop_event = threading.Event()

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="BackupSchedulerThread")
        self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def register_log_callback(self, callback: Callable[[str, str], None]):
        self.log_callbacks.append(callback)

    def _log(self, profile_name: str, message: str, level: str = "INFO"):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{ts}] [{level}] [{profile_name}] {message}"
        for cb in self.log_callbacks:
            try:
                cb(formatted, level)
            except Exception:
                pass

    def _should_run_profile(self, profile: Dict[str, Any]) -> bool:
        if not profile.get("auto_backup_enabled", False):
            return False

        last_run = profile.get("last_run")
        sched_type = profile.get("schedule_type", "interval_hours")
        sched_val = profile.get("schedule_value", "12")

        if not last_run:
            return True

        now = time.time()
        elapsed_sec = now - last_run

        if sched_type == "interval_hours":
            try:
                interval_hours = float(sched_val)
                return elapsed_sec >= (interval_hours * 3600)
            except ValueError:
                return False

        elif sched_type == "daily":
            # Format: "HH:MM" e.g. "03:00"
            try:
                hour, minute = map(int, sched_val.split(":"))
                now_dt = datetime.datetime.now()
                target_today = now_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # Fix #12: Prevent re-trigger loop — require at least 1h since last run to avoid
                # re-triggering on the same day after a quick failure/retry within the same minute.
                if elapsed_sec < 3600:
                    return False

                # If target time today has passed, and last_run was before target time today
                if now_dt >= target_today:
                    target_ts = target_today.timestamp()
                    return last_run < target_ts
                return False
            except Exception:
                return False

        return False

    def _run_profile_backup(self, profile: Dict[str, Any]):
        profile_id = profile["id"]
        profile_name = profile.get("name", profile_id)

        if profile_id in self.active_jobs and self.active_jobs[profile_id].get("running"):
            return  # Already running

        cancel_evt = threading.Event()
        self.active_jobs[profile_id] = {
            "profile_name": profile_name,
            "running": True,
            "start_time": time.time(),
            "cancel_event": cancel_evt,
            "progress": {}
        }

        self._log(profile_name, "스케줄 자동 백업 작업을 시작합니다...")

        try:
            repo_dir = profile.get("repo_dir")
            sources = profile.get("sources", [])
            excludes = profile.get("exclude_patterns", [])
            compress = profile.get("compression_level", 6)
            retention_count = profile.get("retention_count", 30)
            retention_days = profile.get("retention_days", 60)

            def on_progress(p_data):
                if profile_id in self.active_jobs:
                    self.active_jobs[profile_id]["progress"] = p_data

            manifest = SnapshotEngine.create_snapshot(
                repo_dir=repo_dir,
                sources=sources,
                profile_id=profile_id,
                profile_name=profile_name,
                exclude_patterns=excludes,
                compress_level=compress,
                progress_callback=on_progress,
                cancel_event=cancel_evt
            )

            # Prune old snapshots
            pruned = SnapshotEngine.prune_snapshots(
                repo_dir=repo_dir,
                retention_count=retention_count,
                max_age_days=retention_days
            )

            # Update profile info
            profile["last_run"] = time.time()
            profile["last_status"] = "success"
            profile["last_snapshot_id"] = manifest["id"]
            ConfigManager.save_profile(profile)

            summary = manifest.get("summary", {})
            self._log(
                profile_name,
                f"백업 완료: {summary.get('total_files', 0)}개 파일 ({round(summary.get('total_bytes', 0)/(1024*1024), 2)}MB), "
                f"신규/수정 {summary.get('new_files', 0) + summary.get('modified_files', 0)}개, "
                f"중복제거 절감 {round(summary.get('dedup_saved_bytes', 0)/(1024*1024), 2)}MB (소요 {summary.get('duration_seconds', 0)}초)"
            )
            if pruned:
                self._log(profile_name, f"보관 주기 만료 스냅샷 {len(pruned)}개 정리 완료.")

            # Fix #4: Send KakaoTalk success notification for scheduled auto-backup
            try:
                from core.notifier import notify_backup_result
                notify_backup_result(manifest=manifest, profile_name=profile_name)
            except Exception:
                pass

        except Exception as e:
            self._log(profile_name, f"백업 중 오류 발생: {str(e)}", level="ERROR")
            profile["last_status"] = "failed"
            ConfigManager.save_profile(profile)
            # Fix #4: Send KakaoTalk failure notification for scheduled auto-backup
            try:
                from core.notifier import notify_backup_result
                notify_backup_result(error_msg=str(e), profile_name=profile_name)
            except Exception:
                pass

        finally:
            if profile_id in self.active_jobs:
                self.active_jobs[profile_id]["running"] = False
                self.active_jobs[profile_id]["end_time"] = time.time()

    def _run_loop(self):
        while not self.stop_event.is_set():
            try:
                profiles = ConfigManager.get_profiles()
                for prof in profiles:
                    if self._should_run_profile(prof):
                        # Run in worker thread
                        worker = threading.Thread(
                            target=self._run_profile_backup,
                            args=(prof,),
                            daemon=True
                        )
                        worker.start()
            except Exception as e:
                pass

            # Sleep 30 seconds before next check
            self.stop_event.wait(timeout=30)
