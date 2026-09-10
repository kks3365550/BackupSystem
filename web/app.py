import os
import sys
import time
import json
import threading
import psutil
import datetime
import tempfile
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.config import ConfigManager
from core.snapshot import SnapshotEngine
from core.restore import RestoreEngine
from core.storage import BlobStorage
from core.scheduler import BackupScheduler
from core.app_scanner import get_installed_applications, get_project_items
from core.driver_backup import export_windows_drivers

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Fix #13: Background CPU monitor — samples every 0.5s so /api/system-info returns instantly
_cpu_percent_cache = [0.0]
def _cpu_monitor():
    while True:
        try:
            _cpu_percent_cache[0] = psutil.cpu_percent(interval=0.5)
        except Exception:
            time.sleep(0.5)
_cpu_monitor_thread = threading.Thread(target=_cpu_monitor, daemon=True)
_cpu_monitor_thread.start()

# Global execution state
current_task = {
    "type": None,  # "backup", "restore", "verify", None
    "running": False,
    "progress": {},
    "logs": [],
    "cancel_event": None,
    "start_time": None,
    "result": None,
    "error": None
}

task_lock = threading.Lock()
scheduler = BackupScheduler()

def append_task_log(msg: str, level: str = "INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] [{level}] {msg}"
    with task_lock:
        current_task["logs"].append(entry)
        if len(current_task["logs"]) > 500:
            current_task["logs"].pop(0)

scheduler.register_log_callback(append_task_log)

# Fix #15: Replace deprecated @app.on_event with modern lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    append_task_log("백업 스케줄러 서비스가 시작되었습니다.")
    yield
    scheduler.stop()

app = FastAPI(title="Server & System Backup Manager", version="2.1.4", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- Web UI Route ---
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# --- System & Storage API ---
@app.get("/api/system-info")
def get_system_info():
    # Collect drive information
    drives = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                drives.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except (PermissionError, OSError):
                pass
    except Exception:
        pass

    return {
        "cpu_percent": _cpu_percent_cache[0],  # Fix #13: use background-sampled value (no blocking)
        "memory": {
            "total": psutil.virtual_memory().total,
            "used": psutil.virtual_memory().used,
            "free": psutil.virtual_memory().free,
            "percent": psutil.virtual_memory().percent
        },
        "drives": drives
    }

@app.get("/api/storage-stats")
def get_storage_stats(repo_dir: Optional[str] = None):
    repos = [repo_dir] if repo_dir and os.path.exists(repo_dir) else _get_all_candidate_repos(repo_dir)

    total_blobs = 0
    stored_bytes = 0
    logical_bytes = 0
    total_snapshots = 0

    for r in repos:
        if os.path.exists(r):
            st = BlobStorage(r).get_storage_stats()
            total_blobs += st["total_blobs"]
            stored_bytes += st["stored_bytes"]
            logical_bytes += st["logical_bytes"]
            total_snapshots += st["total_snapshots"]

    saved_bytes = max(0, logical_bytes - stored_bytes)
    ratio = round((saved_bytes / logical_bytes * 100), 1) if logical_bytes > 0 else 0.0

    return {
        "total_blobs": total_blobs,
        "stored_bytes": stored_bytes,
        "logical_bytes": logical_bytes,
        "total_snapshots": total_snapshots,
        "dedup_saved_bytes": saved_bytes,
        "savings_percentage": ratio
    }

# --- Directory Browser API ---
class BrowseDirRequest(BaseModel):
    current_path: Optional[str] = None

@app.post("/api/browse-dir")
def browse_directory(req: BrowseDirRequest):
    path = req.current_path
    if not path or not os.path.exists(path):
        # Default to root drives on Windows or root /
        if sys.platform.startswith("win"):
            drives = []
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                d = f"{letter}:\\"
                if os.path.exists(d):
                    drives.append({"name": f"로컬 디스크 ({letter}:)", "path": d, "is_dir": True})
            return {
                "current_path": "",
                "parent_path": None,
                "items": drives
            }
        else:
            path = "/"

    path = os.path.abspath(path)
    parent_path = os.path.dirname(path) if os.path.dirname(path) != path else None

    items = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        items.append({
                            "name": entry.name,
                            "path": os.path.abspath(entry.path),
                            "is_dir": True
                        })
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass

    items.sort(key=lambda x: x["name"].lower())
    return {
        "current_path": path,
        "parent_path": parent_path,
        "items": items
    }

# --- Profiles API ---
@app.get("/api/profiles")
def list_profiles():
    return ConfigManager.get_profiles()

@app.post("/api/profiles")
def save_profile(profile: Dict[str, Any]):
    saved = ConfigManager.save_profile(profile)
    append_task_log(f"백업 프로필 '{saved.get('name')}'이 저장되었습니다.")
    return saved

@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str):
    success = ConfigManager.delete_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"success": True}

def _get_all_candidate_repos(repo_dir: Optional[str] = None) -> List[str]:
    """Auto-discovers all active backup repositories across all drives and profiles."""
    candidates = set()
    if repo_dir:
        candidates.add(os.path.abspath(repo_dir))

    profiles = ConfigManager.get_profiles()
    for p in profiles:
        r = p.get("repo_dir")
        if r:
            candidates.add(os.path.abspath(r))

    # Standard default repository locations
    candidates.add(os.path.abspath(os.path.join(BASE_DIR, "backup_repository")))
    candidates.add(os.path.abspath(os.path.join(os.path.expanduser("~"), "MyBackup_Repository")))

    # Scan all valid mounted drive letters for drive root, MyBackup_Repository, or backup_repository
    mounted_roots = set()
    try:
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint:
                mounted_roots.add(part.mountpoint)
    except Exception:
        pass

    if not mounted_roots:
        # Fallback to standard drive letters if psutil query fails
        for letter in "CDEF":
            d = f"{letter}:\\"
            if os.path.exists(d):
                mounted_roots.add(d)

    for m_root in mounted_roots:
        for repo_cand in (m_root, os.path.join(m_root, "MyBackup_Repository"), os.path.join(m_root, "backup_repository")):
            try:
                if os.path.exists(os.path.join(repo_cand, "snapshots")) and os.path.exists(os.path.join(repo_cand, "blobs")):
                    candidates.add(os.path.abspath(repo_cand))
            except (PermissionError, OSError):
                pass

    valid = [r for r in candidates if os.path.exists(r)]

    def _latest_snap_time(r: str) -> float:
        s_dir = os.path.join(r, "snapshots")
        try:
            files = [os.path.join(s_dir, f) for f in os.listdir(s_dir) if f.endswith(".json")]
            return max([os.path.getmtime(f) for f in files]) if files else 0.0
        except Exception:
            return 0.0

    valid.sort(key=_latest_snap_time, reverse=True)
    return valid

# --- Snapshots API ---
@app.get("/api/snapshots")
def list_snapshots(repo_dir: Optional[str] = None):
    repos = [repo_dir] if repo_dir and os.path.exists(repo_dir) else _get_all_candidate_repos(repo_dir)
    all_snaps = []
    seen_ids = set()

    for r in repos:
        snaps = SnapshotEngine.list_snapshots(r)
        for s in snaps:
            sid = s.get("id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                s["repo_dir"] = r
                all_snaps.append(s)

    all_snaps.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return all_snaps

def _find_snapshot_repo(snapshot_id: str, repo_dir: Optional[str] = None) -> Optional[str]:
    if repo_dir and os.path.exists(repo_dir):
        return repo_dir
    repos = _get_all_candidate_repos(repo_dir)
    for r in repos:
        snap_file = os.path.join(r, "snapshots", f"{snapshot_id}.json")
        if os.path.exists(snap_file):
            return r
    return None

@app.get("/api/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: str, repo_dir: Optional[str] = None):
    r = _find_snapshot_repo(snapshot_id, repo_dir)
    if not r:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    data = SnapshotEngine.get_snapshot(r, snapshot_id)
    if not data:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return data

@app.get("/api/snapshots/{snapshot_id}/tree")
def get_snapshot_tree(snapshot_id: str, repo_dir: Optional[str] = None):
    r = _find_snapshot_repo(snapshot_id, repo_dir)
    if not r:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    data = SnapshotEngine.get_snapshot(r, snapshot_id)
    if not data:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return SnapshotEngine.build_snapshot_tree(data)

@app.delete("/api/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: str, repo_dir: Optional[str] = None):
    r = _find_snapshot_repo(snapshot_id, repo_dir)
    if not r:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    success = SnapshotEngine.delete_snapshot(r, snapshot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    append_task_log(f"스냅샷 '{snapshot_id}'이 삭제되었습니다.")
    return {"success": True}

# --- Installed Applications & Projects Discovery API ---
@app.get("/api/apps/installed")
def list_installed_apps(refresh: bool = False):
    return get_installed_applications(force_refresh=refresh)

@app.get("/api/projects/list")
def list_project_items():
    return get_project_items()

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
    global current_task
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
            prof = {
                "id": profile_id,
                "name": profile_name,
                "sources": all_sources,
                "repo_dir": repo_dir,
                "exclude_patterns": excludes,
                "schedule_type": "interval_hours",
                "schedule_value": "12",
                "auto_backup_enabled": True,
                "retention_count": 30,
                "retention_days": 60,
                "compression_level": 3
            }
            ConfigManager.save_profile(prof)

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
            compress_level=3,
            progress_callback=on_progress,
            cancel_event=cancel_evt
        )

        pruned = SnapshotEngine.prune_snapshots(repo_dir, 30, 60)

        # Update profile
        prof = ConfigManager.get_profile(profile_id)
        if prof:
            prof["last_run"] = time.time()
            prof["last_status"] = "success"
            prof["last_snapshot_id"] = manifest["id"]
            ConfigManager.save_profile(prof)

        summary = manifest.get("summary", {})
        append_task_log(
            f"선택 백업 완료! ID: {manifest['id']} | 파일: {summary.get('total_files')}개 "
            f"({round(summary.get('total_bytes', 0)/(1024*1024), 2)}MB) | "
            f"신규/수정: {summary.get('new_files', 0) + summary.get('modified_files', 0)}개 | "
            f"중복제거 절감: {round(summary.get('dedup_saved_bytes', 0)/(1024*1024), 2)}MB | "
            f"소요: {summary.get('duration_seconds')}초"
        )
        # Fix #1: Send KakaoTalk notification for custom selection backup
        try:
            from core.notifier import notify_backup_result
            notify_backup_result(manifest=manifest, profile_name=profile_name)
        except Exception as e_notif:
            append_task_log(f"카카오톡 알림 전송 실패: {e_notif}", level="WARNING")

        manifest_summary = {
            "id": manifest.get("id"),
            "created_at": manifest.get("created_at"),
            "type": manifest.get("type"),
            "profile_id": manifest.get("profile_id"),
            "profile_name": manifest.get("profile_name"),
            "repo_dir": manifest.get("repo_dir"),
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
    except Exception as e:
        import traceback
        append_task_log(f"백업 중 오류 발생: {str(e)}", level="ERROR")
        append_task_log(traceback.format_exc(), level="ERROR")
        try:
            from core.notifier import notify_backup_result
            notify_backup_result(error_msg=str(e), profile_name=profile_name)
        except Exception:
            pass
        with task_lock:
            current_task["error"] = str(e)
    finally:
        with task_lock:
            current_task["running"] = False

@app.post("/api/backup/custom-selection")
def run_custom_selection_backup(req: RunCustomSelectionBackupRequest, background_tasks: BackgroundTasks):
    global current_task
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
    global current_task
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
        pruned = SnapshotEngine.prune_snapshots(repo_dir, retention_count, retention_days)

        if profile_id:
            profile["last_run"] = time.time()
            profile["last_status"] = "success"
            profile["last_snapshot_id"] = manifest["id"]
            ConfigManager.save_profile(profile)

        summary = manifest.get("summary", {})
        append_task_log(
            f"백업 성공 완료! ID: {manifest['id']} | 파일: {summary.get('total_files')}개 "
            f"({round(summary.get('total_bytes', 0)/(1024*1024), 2)}MB) | "
            f"신규/수정: {summary.get('new_files', 0) + summary.get('modified_files', 0)}개 | "
            f"중복제거 절감: {round(summary.get('dedup_saved_bytes', 0)/(1024*1024), 2)}MB | "
            f"소요시간: {summary.get('duration_seconds')}초"
        )
        if pruned:
            append_task_log(f"오래된 백업 스냅샷 {len(pruned)}개를 보관 정책에 따라 자동 정리했습니다.")

        # Send KakaoTalk notification
        try:
            from core.notifier import notify_backup_result
            notify_backup_result(manifest=manifest, profile_name=profile_name)
        except Exception as e_notif:
            append_task_log(f"카카오톡 알림 전송 실패: {e_notif}", level="WARNING")

        manifest_summary = {
            "id": manifest.get("id"),
            "created_at": manifest.get("created_at"),
            "type": manifest.get("type"),
            "profile_id": manifest.get("profile_id"),
            "profile_name": manifest.get("profile_name"),
            "repo_dir": manifest.get("repo_dir"),
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
    except Exception as e:
        import traceback
        append_task_log(f"백업 중 오류 발생: {str(e)}", level="ERROR")
        append_task_log(traceback.format_exc(), level="ERROR")
        try:
            from core.notifier import notify_backup_result
            notify_backup_result(error_msg=str(e), profile_name=profile_name)
        except Exception:
            pass
        with task_lock:
            current_task["error"] = str(e)
            if profile_id and profile:
                profile["last_status"] = "failed"
                ConfigManager.save_profile(profile)
    finally:
        with task_lock:
            current_task["running"] = False

@app.post("/api/backup/run")
def run_backup(req: RunBackupRequest, background_tasks: BackgroundTasks):
    global current_task
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

@app.post("/api/backup/cancel")
def cancel_backup():
    with task_lock:
        if not current_task["running"] or not current_task["cancel_event"]:
            return {"status": "not_running"}
        current_task["cancel_event"].set()
        append_task_log("작업 취소 신호를 전송했습니다...", level="WARNING")
        return {"status": "cancelling"}

@app.get("/api/task/status")
def get_task_status():
    with task_lock:
        return {
            "type": current_task["type"],
            "running": current_task["running"],
            "progress": current_task["progress"],
            "logs": current_task["logs"][-30:],
            "start_time": current_task["start_time"],
            "result": current_task["result"],
            "error": current_task["error"]
        }

# --- Restore Execution API ---
class RunRestoreRequest(BaseModel):
    snapshot_id: str
    target_dir: str
    repo_dir: Optional[str] = None
    selected_rel_paths: Optional[List[str]] = None
    overwrite: bool = True

def _background_restore_task(params: Dict[str, Any]):
    global current_task
    snap_id = params["snapshot_id"]
    target_dir = params["target_dir"]
    selected = params.get("selected_rel_paths")
    overwrite = params.get("overwrite", True)
    cancel_evt = current_task["cancel_event"]

    # Fix #9: Use _find_snapshot_repo to auto-discover correct repo instead of blindly using first profile
    repo_dir = params.get("repo_dir")
    if not repo_dir or not os.path.exists(repo_dir):
        repo_dir = _find_snapshot_repo(snap_id, repo_dir)
    if not repo_dir:
        profiles = ConfigManager.get_profiles()
        repo_dir = profiles[0].get("repo_dir") if profiles else os.path.join(BASE_DIR, "backup_repository")

    append_task_log(f"복원 작업 시작: 스냅샷 '{snap_id}' -> 대상 경로: '{target_dir}'")

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
    except Exception as e:
        append_task_log(f"복원 중 오류 발생: {str(e)}", level="ERROR")
        with task_lock:
            current_task["error"] = str(e)
    finally:
        with task_lock:
            current_task["running"] = False

@app.post("/api/restore/run")
def run_restore(req: RunRestoreRequest, background_tasks: BackgroundTasks):
    global current_task
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

@app.post("/api/verify/run")
def run_verify(req: RunVerifyRequest):
    repo_dir = req.repo_dir
    if not repo_dir:
        profiles = ConfigManager.get_profiles()
        repo_dir = profiles[0].get("repo_dir") if profiles else os.path.join(BASE_DIR, "backup_repository")

    append_task_log(f"스냅샷 '{req.snapshot_id}' 무결성 검증을 시작합니다...")
    res = RestoreEngine.verify_snapshot_integrity(repo_dir, req.snapshot_id)
    if res["is_valid"]:
        append_task_log(f"무결성 검증 통과! {res['total_files']}개 모든 파일의 해시 및 블롭이 완벽합니다.")
    else:
        append_task_log(f"무결성 검증 실패! 누락: {len(res['missing_blobs'])}, 손상: {len(res['corrupted_blobs'])}", level="ERROR")
    return res

# --- Maintenance & Prune API ---
@app.post("/api/maintenance/prune")
def prune_storage(repo_dir: Optional[str] = None):
    if not repo_dir:
        profiles = ConfigManager.get_profiles()
        repo_dir = profiles[0].get("repo_dir") if profiles else os.path.join(BASE_DIR, "backup_repository")

    res = SnapshotEngine.prune_storage(repo_dir)
    freed_mb = round(res['freed_bytes'] / (1024 * 1024), 2)
    append_task_log(f"가비지 컬렉션 완료: 참조되지 않는 고아 블롭 {res['deleted_blobs']}개 삭제, {freed_mb}MB 용량 회수")
    return res

# --- Windows Task Scheduler API (On/Off Smart Execution) ---
from core.windows_task import register_windows_scheduled_task, unregister_windows_scheduled_task, get_windows_scheduled_task_status

class WindowsTaskRegisterRequest(BaseModel):
    profile_id: Optional[str] = None
    schedule_type: str = "daily"
    schedule_value: str = "03:00"

@app.get("/api/windows-task/status")
def get_windows_task_status():
    return get_windows_scheduled_task_status()

@app.post("/api/windows-task/register")
def register_windows_task(req: WindowsTaskRegisterRequest):
    res = register_windows_scheduled_task(req.profile_id, req.schedule_type, req.schedule_value)
    if res.get("success"):
        append_task_log(f"Windows 작업 스케줄러 등록 완료: {res.get('message')}")
    else:
        append_task_log(f"Windows 작업 스케줄러 등록 실패: {res.get('error')}", level="ERROR")
    return res

@app.post("/api/windows-task/unregister")
def unregister_windows_task():
    res = unregister_windows_scheduled_task()
    append_task_log("Windows 작업 스케줄러에서 등록 해제되었습니다.")
    return res

# --- Windows System Image (Bare-Metal) API ---
from core.system_image import SystemImageManager

class SystemImageStartRequest(BaseModel):
    target_drive: str = "D:"

@app.get("/api/system-image/status")
def get_system_image_status(target_drive: str = "D:"):
    return SystemImageManager.get_status(target_drive)

@app.post("/api/system-image/start")
def start_system_image(req: SystemImageStartRequest):
    res = SystemImageManager.start_backup(
        req.target_drive,
        log_callback=lambda msg: append_task_log(f"[시스템이미지] {msg}")
    )
    return res

@app.get("/api/system-image/logs")
def get_system_image_logs():
    return SystemImageManager.get_logs()

@app.post("/api/system-image/stop")
def stop_system_image():
    return SystemImageManager.stop_backup()

# --- System Shutdown API ---
@app.post("/api/system/shutdown")
def shutdown_system():
    def _kill():
        time.sleep(0.4)
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
    return {"success": True, "message": "백업 시스템 서비스가 완전히 종료됩니다."}

# --- Remote Self-Update API ---
@app.post("/api/system/self-update")
async def self_update(request: Request):
    """
    Receives raw zip binary of latest code, extracts it over BASE_DIR, and restarts the service.
    Enables true zero-touch remote updating from another machine.
    """
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty update payload")

    import io
    import zipfile
    import subprocess

    try:
        with zipfile.ZipFile(io.BytesIO(body), "r") as zf:
            file_names = zf.namelist()
            if not any("core" in fn or "web" in fn or "run.py" in fn for fn in file_names):
                raise HTTPException(status_code=400, detail="Invalid update package: missing core/web components")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid zip payload: {str(e)}")

    temp_zip = os.path.join(tempfile.gettempdir(), f"backup_update_{int(time.time())}.zip")
    with open(temp_zip, "wb") as f:
        f.write(body)

    updater_bat = os.path.join(tempfile.gettempdir(), f"run_updater_{int(time.time())}.bat")
    py_exe = sys.executable

    bat_content = f"""@echo off
timeout /t 1 >nul
tar -xf "{temp_zip}" -C "{BASE_DIR}"
cd /d "{BASE_DIR}"
start "" "{py_exe}" run.py
del "{temp_zip}" >nul 2>&1
del "%~f0" >nul 2>&1
"""
    with open(updater_bat, "w", encoding="utf-8") as f:
        f.write(bat_content)

    def _trigger_update_and_restart():
        time.sleep(0.8)
        subprocess.Popen(
            ["cmd.exe", "/c", updater_bat],
            creationflags=0x00000008 | 0x00000200,
            close_fds=True
        )
        time.sleep(0.2)
        os._exit(0)

    threading.Thread(target=_trigger_update_and_restart, daemon=True).start()
    return {
        "success": True,
        "message": f"업데이트 패키지({len(body)} 바이트)를 수신했습니다. 1초 후 자동으로 덮어쓰고 최신 엔진으로 재시작됩니다."
    }
