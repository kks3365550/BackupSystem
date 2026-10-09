# -*- coding: utf-8 -*-
"""
web/api_backup.py

백업, 복원, 무결성 검증, 작업 상태, 로그 및 스토리지 정리 APIRouter 모듈
"""
import os
import time
import threading
import tempfile
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

from web.paths import BASE_DIR
from web.state import (
    current_task,
    task_lock,
    append_task_log,
    snapshot_task_status,
    request_cancel,
)
from web.api_snapshots import _get_all_candidate_repos, _find_snapshot_repo
from core.config import ConfigManager
from core.snapshot import SnapshotEngine
from core.restore import RestoreEngine
from core.storage import BlobStorage
from core.app_scanner import get_installed_applications
from core.driver_backup import export_windows_drivers

# 백업이 거부될 때의 예외 타입.
#
# 예외 핸들러 안에서만 import 하면 같은 이름이 두 곳에 생긴다
# (선택 백업 핸들러 / 일반 백업 핸들러). 한쪽만 수정하면 조용히 어긋나고
# pyflakes 는 중복을 잡지 못한다. 모듈 상단에 한 번만 둔다.
from core.lock import BackupAlreadyRunningError
from core.storage import InsufficientDiskSpaceError
from core.vss_manager import VSSRequiredError
from core.verify import RestoreVerificationError

router = APIRouter()


# --- Backup Execution API ---
class RunBackupRequest(BaseModel):
    profile_id: Optional[str] = None
    repo_dir: Optional[str] = None
    sources: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    compression_level: Optional[int] = 6


class RunCustomSelectionBackupRequest(BaseModel):
    include_drivers: bool = True
    selected_projects: List[str] = []
    selected_apps: List[str] = []
    custom_folders: List[str] = []
    repo_dir: Optional[str] = None
    profile_name: Optional[str] = "선택 백업"
    save_as_profile: bool = True
    exclude_patterns: Optional[List[str]] = None


def _background_custom_backup_task(params: Dict[str, Any]):
    try:
        include_drivers = params.get("include_drivers", True)
        selected_projects = params.get("selected_projects", [])
        selected_apps = params.get("selected_apps", [])
        custom_folders = params.get("custom_folders", [])
        repo_dir = params.get("repo_dir")
        if not repo_dir:
            for cand in _get_all_candidate_repos():
                if os.path.exists(os.path.join(cand, "snapshots")):
                    repo_dir = cand
                    break
        if not repo_dir:
            repo_dir = "D:\\MyBackup_Repository" if os.path.exists("D:\\") else os.path.join(os.path.expanduser("~"), "MyBackup_Repository")

        profile_name = params.get("profile_name", "내 맞춤형 선택 백업")
        excludes = params.get("exclude_patterns") or [
            "node_modules", "__pycache__", "*.pyc", ".venv", "venv", "*.tmp", "*.temp", "*.log", "backup_repository", "MyBackup_Repository"
        ]

        cancel_evt = current_task.get("cancel_event")
        all_sources = []

        # 저장소 드라이브 유효성 확인 및 자동 폴백
        repo_drive = os.path.splitdrive(repo_dir)[0]
        if repo_drive and not os.path.exists(repo_drive + "\\"):
            fallback_dir = os.path.join(os.path.expanduser("~"), "MyBackup_Repository")
            append_task_log(f"저장소 드라이브({repo_drive})가 없어 대체 경로({fallback_dir})를 사용합니다.", level="WARNING")
            repo_dir = fallback_dir
        os.makedirs(repo_dir, exist_ok=True)

        # 1. Driver Export if requested
        if include_drivers:
            driver_dir = os.path.join(os.path.expanduser("~"), "Windows_Drivers")
            with task_lock:
                current_task["progress"]["current_file"] = "윈도우 OEM 드라이버 수집 중..."
            append_task_log("윈도우 OEM 드라이버 추출을 시도합니다...")
            try:
                d_res = export_windows_drivers(driver_dir)
                if d_res.get("success"):
                    append_task_log(f"드라이버 {d_res.get('driver_count')}개 패키지 추출 완료 -> {driver_dir}")
                    all_sources.append(driver_dir)
                else:
                    append_task_log(f"드라이버 추출 건너뜀 (알림: {d_res.get('error', '권한 부족 또는 시간 초과')})", level="WARNING")
            except Exception as d_err:
                append_task_log(f"드라이버 추출 중 오류로 건너뜀: {d_err}", level="WARNING")

        # 2. Add projects
        for p in selected_projects:
            if os.path.exists(p) and p not in all_sources:
                all_sources.append(p)

        # 3. Add apps + their AppData + Start Menu Shortcuts + Full Registry Keys
        if selected_apps:
            reg_backup_dir = os.path.join(tempfile.gettempdir(), "Universal_Registry_Backup")
            os.makedirs(reg_backup_dir, exist_ok=True)

            try:
                from core.registry_backup import AppPackageCollector, collect_full_app_package
                collector = AppPackageCollector(reg_backup_dir)
                installed_apps_cache = get_installed_applications()

                for a in selected_apps:
                    if cancel_evt and cancel_evt.is_set():
                        raise InterruptedError("Cancelled by user")
                    
                    matched_app = next((item for item in installed_apps_cache if item.get("location") == a or item.get("name") == a), None)
                    app_name = matched_app["name"] if matched_app else os.path.basename(a)
                    publisher = matched_app.get("publisher", "") if matched_app else ""
                    location = a if os.path.exists(a) else (matched_app.get("location", "") if matched_app else "")

                    with task_lock:
                        current_task["progress"]["current_file"] = f"[{app_name}] 설정 및 레지스트리 수집 중..."

                    sources_to_add, reg_files = collect_full_app_package(app_name, publisher, location, reg_backup_dir, collector=collector)

                    for src in sources_to_add:
                        if src not in all_sources:
                            all_sources.append(src)

                    append_task_log(f"[{app_name}] 프로그램 본체 + 개인설정(AppData) + 바로가기 패키징 완료")

                if os.path.exists(reg_backup_dir) and os.listdir(reg_backup_dir) and reg_backup_dir not in all_sources:
                    all_sources.append(reg_backup_dir)
            except Exception as e_app:
                append_task_log(f"프로그램 패키징 중 알림: {e_app}", level="WARNING")

        # 4. Add custom folders
        for c in custom_folders:
            if os.path.exists(c) and c not in all_sources:
                all_sources.append(c)

        if not all_sources:
            append_task_log("백업할 유효한 대상 파일/폴더가 없습니다. 대상을 확인해 주세요.", level="ERROR")
            with task_lock:
                current_task["error"] = "선택된 백업 대상이 없습니다."
            return

        append_task_log(f"선택 백업 스캔 시작: 총 {len(all_sources)}개 대상 경로 -> 저장소: {repo_dir}")
        with task_lock:
            current_task["progress"]["current_file"] = "파일 목록 스캔 및 해시 분석 중..."

        # Save as profile if requested
        profile_id = "prof_custom_selected"
        if params.get("save_as_profile", True):
            is_desktop = False
            try:
                import socket
                hname = socket.gethostname().lower()
                if "desktop" in hname or "r2pfnfp" in hname:
                    is_desktop = True
            except Exception:
                pass

            # 기존 프로필 불러오기 (없으면 None)
            existing_prof = ConfigManager.get_profile(profile_id)

            if existing_prof:
                # 기존 프로필의 모든 설정을 보존하고, sources/repo_dir/exclude_patterns만 업데이트
                prof = dict(existing_prof)
                prof["sources"] = all_sources
                prof["repo_dir"] = repo_dir
                prof["exclude_patterns"] = excludes
                # 데스크탑인 경우 자동 백업 강제 비활성화
                if is_desktop:
                    prof["auto_backup_enabled"] = False
                    prof["schedule_type"] = "manual"
            else:
                # 최초 생성 시에만 기본값 사용
                auto_enable = False if is_desktop else params.get("auto_backup_enabled", False)
                sched_type = "manual" if is_desktop else params.get("schedule_type", "manual")

                prof = {
                    "id": profile_id,
                    "name": profile_name,
                    "sources": all_sources,
                    "repo_dir": repo_dir,
                    "exclude_patterns": excludes,
                    "schedule_type": sched_type,
                    "schedule_value": params.get("schedule_value", "12"),
                    "auto_backup_enabled": auto_enable,
                    "retention_count": params.get("retention_count", 30),
                    "retention_days": params.get("retention_days", 60),
                    "compression_level": params.get("compression_level", 3)
                }
            ConfigManager.save_profile(prof)
        else:
            # save_as_profile=False 이면 기존 프로필 설정만 참조
            prof = ConfigManager.get_profile(profile_id) or {}

        # 실제 백업에 사용할 압축 레벨: 프로필 설정 우선, 없으면 3
        effective_compress = prof.get("compression_level", 3) if prof else 3
        effective_retention_count = prof.get("retention_count", 30) if prof else 30
        effective_retention_days = prof.get("retention_days", 60) if prof else 60

        def on_progress(p_data):
            with task_lock:
                current_task["progress"] = p_data
            if p_data.get("processed_files", 0) % 50 == 0:
                append_task_log(f"진행 중: {p_data.get('percent')}% ({p_data.get('processed_files')}/{p_data.get('total_files')} 파일)")

        manifest = SnapshotEngine.create_snapshot(
            repo_dir=repo_dir,
            sources=all_sources,
            profile_id=profile_id,
            profile_name=profile_name,
            exclude_patterns=excludes,
            compress_level=effective_compress,
            progress_callback=on_progress,
            cancel_event=cancel_evt
        )

        pruned = SnapshotEngine.prune_snapshots(repo_dir, effective_retention_count, effective_retention_days, authorized=True)
        append_task_log(f"[보존 정책] 만료된 스냅샷 {len(pruned)}개 정리 완료")

        # Update profile
        prof = ConfigManager.get_profile(profile_id)
        if prof:
            prof["last_run"] = time.time()
            prof["last_status"] = "success"
            prof["last_snapshot_id"] = manifest["id"]
            ConfigManager.save_profile(prof)

        summary = manifest.get("summary", {})
        vss_mode = "VSS 볼륨 섀도 복사본(Crash-Consistent 일관성 보장)" if manifest.get("vss_enabled") else "일반 직접 읽기"
        append_task_log(
            f"선택 백업 완료! ID: {manifest['id']} | [{vss_mode}] | 파일: {summary.get('total_files')}개 "
            f"({round(summary.get('total_bytes', 0)/(1024*1024), 2)}MB) | "
            f"신규/수정: {summary.get('new_files', 0) + summary.get('modified_files', 0)}개 | "
            f"중복제거 절감: {round(summary.get('dedup_saved_bytes', 0)/(1024*1024), 2)}MB | "
            f"소요: {summary.get('duration_seconds')}초"
        )

        manifest_summary = {
            "id": manifest.get("id"),
            "created_at": manifest.get("created_at"),
            "type": manifest.get("type"),
            "profile_id": manifest.get("profile_id"),
            "profile_name": manifest.get("profile_name"),
            "repo_dir": manifest.get("repo_dir"),
            "vss_enabled": manifest.get("vss_enabled", False),
            "summary": manifest.get("summary")
        }
        del manifest
        import gc
        gc.collect()

        with task_lock:
            current_task["result"] = manifest_summary
            current_task["error"] = None
            if current_task.get("progress"):
                current_task["progress"]["percent"] = 100.0
                current_task["progress"]["current_file"] = "선택 백업 작업 완료"

    except InterruptedError:
        append_task_log("사용자에 의해 백업 작업이 취소되었습니다.", level="WARNING")
        with task_lock:
            current_task["error"] = "Cancelled by user"
            current_task["result"] = None
    except Exception as e:
        if isinstance(e, BackupAlreadyRunningError):
            append_task_log(f"선택 백업 거부: {str(e)}", level="WARNING")
        elif isinstance(e, InsufficientDiskSpaceError):
            append_task_log(f"[안전 보호(Fail-Closed) 작동] {str(e)}", level="ERROR")
        elif isinstance(e, VSSRequiredError):
            append_task_log(f"[VSS Strict 차단] {str(e)}", level="ERROR")
        elif isinstance(e, RestoreVerificationError):
            append_task_log(f"[복원 무결성 검증 실패(DEGRADED)] {str(e)}", level="ERROR")
        else:
            import traceback
            append_task_log(f"백업 중 오류 발생: {str(e)}", level="ERROR")
            append_task_log(traceback.format_exc(), level="ERROR")
        with task_lock:
            current_task["error"] = str(e)
            current_task["result"] = None
    finally:
        with task_lock:
            current_task["running"] = False


@router.post("/api/backup/custom-selection")
def run_custom_selection_backup(req: RunCustomSelectionBackupRequest, background_tasks: BackgroundTasks):
    with task_lock:
        if current_task["running"]:
            raise HTTPException(status_code=409, detail="이미 다른 백업 또는 복원 작업이 실행 중입니다.")

        cancel_evt = threading.Event()
        current_task.update({
            "type": "backup",
            "running": True,
            "progress": {"percent": 0, "processed_files": 0, "total_files": 0, "current_file": "백업 준비 중..."},
            "cancel_event": cancel_evt,
            "start_time": time.time(),
            "result": None,
            "error": None
        })

    background_tasks.add_task(_background_custom_backup_task, req.dict())
    return {"status": "started"}


def _background_backup_task(params: Dict[str, Any]):
    try:
        profile_id = params.get("profile_id")
        profile = None
        if profile_id:
            profile = ConfigManager.get_profile(profile_id)

        if not profile:
            profiles = ConfigManager.get_profiles()
            # Find active profile with auto_backup_enabled == True, or first profile
            profile = next((p for p in profiles if p.get("auto_backup_enabled")), (profiles[0] if profiles else {}))
            profile_id = profile.get("id", "prof_default")
        
        repo_dir = params.get("repo_dir") or profile.get("repo_dir")
        if not repo_dir:
            for cand in _get_all_candidate_repos():
                if os.path.exists(os.path.join(cand, "snapshots")):
                    repo_dir = cand
                    break
        if not repo_dir:
            repo_dir = "D:\\MyBackup_Repository" if os.path.exists("D:\\") else os.path.join(BASE_DIR, "backup_repository")

        sources = params.get("sources") or profile.get("sources") or [BASE_DIR]
        excludes = params.get("exclude_patterns") or profile.get("exclude_patterns") or []
        compress = params.get("compression_level") or profile.get("compression_level") or 6
        profile_name = profile.get("name", "수동 백업")

        # 저장소 드라이브 유효성 확인 및 폴백
        repo_drive = os.path.splitdrive(repo_dir)[0]
        if repo_drive and not os.path.exists(repo_drive + "\\"):
            fallback_dir = os.path.join(os.path.expanduser("~"), "MyBackup_Repository")
            append_task_log(f"저장소 드라이브({repo_drive})가 없어 대체 경로({fallback_dir})를 사용합니다.", level="WARNING")
            repo_dir = fallback_dir
        os.makedirs(repo_dir, exist_ok=True)

        cancel_evt = current_task["cancel_event"]
        append_task_log(f"백업 작업 시작: '{profile_name}' (원본 {len(sources)}개 경로 -> 저장소: {repo_dir})")
        with task_lock:
            current_task["progress"]["current_file"] = "파일 목록 스캔 및 해시 분석 중..."

        def on_progress(p_data):
            with task_lock:
                current_task["progress"] = p_data
            if p_data.get("processed_files", 0) % 50 == 0:
                append_task_log(f"진행 중: {p_data.get('percent')}% ({p_data.get('processed_files')}/{p_data.get('total_files')} 파일)")

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

        # Retention check
        retention_count = profile.get("retention_count", 30)
        retention_days = profile.get("retention_days", 60)
        pruned = SnapshotEngine.prune_snapshots(repo_dir, retention_count, retention_days, authorized=True)

        if profile_id:
            profile["last_run"] = time.time()
            profile["last_status"] = "success"
            profile["last_snapshot_id"] = manifest["id"]
            ConfigManager.save_profile(profile)

        summary = manifest.get("summary", {})
        vss_mode = "VSS 볼륨 섀도 복사본(Crash-Consistent 일관성 보장)" if manifest.get("vss_enabled") else "일반 직접 읽기"
        append_task_log(
            f"백업 성공 완료! ID: {manifest['id']} | [{vss_mode}] | 파일: {summary.get('total_files')}개 "
            f"({round(summary.get('total_bytes', 0)/(1024*1024), 2)}MB) | "
            f"신규/수정: {summary.get('new_files', 0) + summary.get('modified_files', 0)}개 | "
            f"중복제거 절감: {round(summary.get('dedup_saved_bytes', 0)/(1024*1024), 2)}MB | "
            f"소요시간: {summary.get('duration_seconds')}초"
        )
        if pruned:
            append_task_log(f"오래된 백업 스냅샷 {len(pruned)}개를 보관 정책에 따라 자동 정리했습니다.")

        manifest_summary = {
            "id": manifest.get("id"),
            "created_at": manifest.get("created_at"),
            "type": manifest.get("type"),
            "profile_id": manifest.get("profile_id"),
            "profile_name": manifest.get("profile_name"),
            "repo_dir": manifest.get("repo_dir"),
            "vss_enabled": manifest.get("vss_enabled", False),
            "summary": manifest.get("summary")
        }
        del manifest
        import gc
        gc.collect()

        with task_lock:
            current_task["result"] = manifest_summary
            current_task["error"] = None

    except InterruptedError:
        append_task_log("사용자에 의해 백업 작업이 취소되었습니다.", level="WARNING")
        with task_lock:
            current_task["error"] = "Cancelled by user"
            current_task["result"] = None
    except Exception as e:
        if isinstance(e, BackupAlreadyRunningError):
            append_task_log(f"백업 거부: {str(e)}", level="WARNING")
        elif isinstance(e, InsufficientDiskSpaceError):
            append_task_log(f"[안전 보호(Fail-Closed) 작동] {str(e)}", level="ERROR")
        elif isinstance(e, VSSRequiredError):
            append_task_log(f"[VSS Strict 차단] {str(e)}", level="ERROR")
        elif isinstance(e, RestoreVerificationError):
            append_task_log(f"[복원 무결성 검증 실패(DEGRADED)] {str(e)}", level="ERROR")
        else:
            import traceback
            append_task_log(f"백업 중 오류 발생: {str(e)}", level="ERROR")
            append_task_log(traceback.format_exc(), level="ERROR")
        with task_lock:
            current_task["error"] = str(e)
            current_task["result"] = None
            if profile_id and profile:
                profile["last_status"] = "failed"
                ConfigManager.save_profile(profile)
    finally:
        with task_lock:
            current_task["running"] = False


@router.post("/api/backup/run")
def run_backup(req: RunBackupRequest, background_tasks: BackgroundTasks):
    with task_lock:
        if current_task["running"]:
            raise HTTPException(status_code=409, detail="이미 다른 백업 또는 복원 작업이 실행 중입니다.")

        cancel_evt = threading.Event()
        current_task.update({
            "type": "backup",
            "running": True,
            "progress": {"percent": 0, "processed_files": 0, "total_files": 0, "current_file": "스캔 준비 중..."},
            "cancel_event": cancel_evt,
            "start_time": time.time(),
            "result": None,
            "error": None
        })

    background_tasks.add_task(_background_backup_task, req.dict())
    return {"status": "started"}


@router.post("/api/backup/cancel")
def cancel_backup():
    if not request_cancel():
        return {"status": "not_running"}
    append_task_log("작업 취소 신호를 전송했습니다...", level="WARNING")
    return {"status": "cancelling"}


@router.get("/api/task/status")
def get_task_status():
    return snapshot_task_status()


@router.get("/api/backup/logs")
def get_backup_logs(limit: int = 200):
    """
    스케줄러 백업 로그를 반환한다.

    왜 이 엔드포인트가 필요한가:
        작업 스케줄러는 pythonw.exe 로 cli_backup.py 를 실행한다.
        표준출력이 없어 예전에는 어떤 정보도 남지 않았다.
        core/logging_setup.py 가 logs/backup.log 에 기록하지만,
        서버가 곧바로 읽을 수 있어야 현장에서 확인 가능하다.
    """
    try:
        from core.logging_setup import BACKUP_LOG
    except Exception as e:
        return {"success": False, "error": f"로깅 모듈 로드 실패: {e}"}

    result = {
        "success": True,
        "path": BACKUP_LOG,
        "lines": [],
        "exists": os.path.exists(BACKUP_LOG),
        "rotated": [],
    }

    # 회전된 이전 파일까지 함께 보여준다 (최근 실패 원인이 직전 회전에 있을 수 있음)
    targets = [BACKUP_LOG]
    for suffix in [".1", ".2"]:
        targets.append(BACKUP_LOG + suffix)

    for path in targets:
        try:
            if not os.path.exists(path):
                continue
            size_kb = round(os.path.getsize(path) / 1024, 1)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            if path == BACKUP_LOG:
                result["lines"] = lines[-max(1, min(limit, 2000)):]
                result["size_kb"] = size_kb
            else:
                result["rotated"].append({
                    "file": os.path.basename(path),
                    "size_kb": size_kb,
                    "lines": len(lines),
                })
        except Exception as e:
            result.setdefault("warnings", []).append(f"{os.path.basename(path)}: {e}")

    # 로그가 아예 없으면 왜인지 알려준다 (pythonw 문제 재발 시 대비)
    if not result["exists"] and not result["rotated"]:
        result["notice"] = (
            "백업 로그가 아직 없습니다. 첫 스케줄러 실행(기본 09:00) 이후에 생성됩니다."
        )

    return result


# --- Restore Execution API ---
class RunRestoreRequest(BaseModel):
    snapshot_id: str
    target_dir: Optional[str] = None
    repo_dir: Optional[str] = None
    selected_rel_paths: Optional[List[str]] = None
    overwrite: bool = True
    in_place: bool = False


def _background_restore_task(params: Dict[str, Any]):
    snap_id = params["snapshot_id"]
    target_dir = params.get("target_dir")
    selected = params.get("selected_rel_paths")
    overwrite = params.get("overwrite", True)
    in_place = params.get("in_place", False)
    cancel_evt = current_task["cancel_event"]

    # Fix #9: Use _find_snapshot_repo to auto-discover correct repo instead of blindly using first profile
    repo_dir = params.get("repo_dir")
    if not repo_dir or not os.path.exists(repo_dir):
        repo_dir = _find_snapshot_repo(snap_id, repo_dir)
    if not repo_dir:
        profiles = ConfigManager.get_profiles()
        repo_dir = profiles[0].get("repo_dir") if profiles else os.path.join(BASE_DIR, "backup_repository")

    dest_desc = "백업 당시 원래 위치(In-place 롤백)" if in_place else f"대상 경로 '{target_dir}'"
    append_task_log(f"복원 작업 시작: 스냅샷 '{snap_id}' -> {dest_desc}")

    def on_progress(p_data):
        with task_lock:
            current_task["progress"] = p_data

    try:
        result = RestoreEngine.restore_snapshot(
            repo_dir=repo_dir,
            snapshot_id=snap_id,
            target_dir=target_dir,
            selected_rel_paths=selected,
            overwrite=overwrite,
            in_place=in_place,
            progress_callback=on_progress,
            cancel_event=cancel_evt
        )

        append_task_log(
            f"복원 완료! 복원된 파일: {result['restored_files']}개 ({round(result['restored_bytes']/(1024*1024), 2)}MB), "
            f"건너뜀: {result['skipped_files']}개, 실패: {len(result['failed_files'])}개 (소요 {result['duration_seconds']}초)"
        )
        with task_lock:
            current_task["result"] = result
            current_task["error"] = None

    except InterruptedError:
        append_task_log("복원 작업이 사용자에 의해 취소되었습니다.", level="WARNING")
        with task_lock:
            current_task["error"] = "Cancelled by user"
            current_task["result"] = None
    except Exception as e:
        append_task_log(f"복원 중 오류 발생: {str(e)}", level="ERROR")
        with task_lock:
            current_task["error"] = str(e)
            current_task["result"] = None
    finally:
        with task_lock:
            current_task["running"] = False


@router.post("/api/restore/run")
def run_restore(req: RunRestoreRequest, background_tasks: BackgroundTasks):
    with task_lock:
        if current_task["running"]:
            raise HTTPException(status_code=409, detail="이미 다른 백업 또는 복원 작업이 실행 중입니다.")

        cancel_evt = threading.Event()
        current_task.update({
            "type": "restore",
            "running": True,
            "progress": {"percent": 0, "restored_files": 0, "total_files": 0, "current_file": "복원 준비 중..."},
            "cancel_event": cancel_evt,
            "start_time": time.time(),
            "result": None,
            "error": None
        })

    background_tasks.add_task(_background_restore_task, req.dict())
    return {"status": "started"}


# --- Verify API ---
class RunVerifyRequest(BaseModel):
    snapshot_id: str
    repo_dir: Optional[str] = None


@router.post("/api/verify/run")
def run_verify(req: RunVerifyRequest):
    repo_dir = req.repo_dir
    if not repo_dir:
        repo_dir = _find_snapshot_repo(req.snapshot_id)
    if not repo_dir:
        profiles = ConfigManager.get_profiles()
        repo_dir = profiles[0].get("repo_dir") if profiles else os.path.join(BASE_DIR, "backup_repository")

    append_task_log(f"스냅샷 '{req.snapshot_id}' 물리적 무결성(Health Check) 검증을 시작합니다...")
    manifest = SnapshotEngine.get_snapshot(repo_dir, req.snapshot_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="스냅샷을 찾을 수 없습니다.")

    from core.verify import IntegrityVerifier
    verifier = IntegrityVerifier(repo_dir)
    res = verifier.verify_snapshot(manifest, sample_ratio=0.2, max_samples=200, verify_all_new=True)

    # SQLite DB 및 메타데이터 업데이트
    storage = BlobStorage(repo_dir)
    storage.db.update_snapshot_verification(
        snapshot_id=req.snapshot_id,
        is_verified=res.get("success", False),
        error_count=res.get("error_count", 0)
    )

    if res["success"]:
        append_task_log(f"무결성 검증 100% 통과! {res['verified_count']}개 블롭 검사 완료 (오류 0개)")
    else:
        append_task_log(f"무결성 검증 실패! 손상된 블롭 발견: {res['error_count']}개", level="ERROR")
    return res


# --- Maintenance & Prune API ---
@router.post("/api/maintenance/prune")
def prune_storage(repo_dir: Optional[str] = None):
    if not repo_dir:
        profiles = ConfigManager.get_profiles()
        repo_dir = profiles[0].get("repo_dir") if profiles else os.path.join(BASE_DIR, "backup_repository")

    try:
        res = SnapshotEngine.prune_storage(repo_dir)
        freed_mb = round(res['freed_bytes'] / (1024 * 1024), 2)
        append_task_log(f"가비지 컬렉션 완료: 참조되지 않는 고아 블롭 {res['deleted_blobs']}개 삭제, {freed_mb}MB 용량 회수")
        return res
    except Exception as e:
        append_task_log(f"가비지 컬렉션 실패/중단: {e}", level="ERROR")
        raise HTTPException(status_code=409 if "실행 중" in str(e) or "잠겨 있습니다" in str(e) else 500, detail=str(e))
