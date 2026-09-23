import os
import sys
import time
import json
import base64
import shutil
import threading
import psutil
import datetime
import tempfile
from collections import deque
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from core.config import ConfigManager
from core.snapshot import SnapshotEngine
from core.restore import RestoreEngine
from core.storage import BlobStorage
from core.scheduler import BackupScheduler
from core.app_scanner import get_installed_applications, get_project_items
from core.driver_backup import export_windows_drivers
from core.auth import (
    is_auth_configured, get_auth_status, setup_master_password,
    verify_master_password, change_master_password, create_session,
    validate_session, revoke_session, set_localhost_bypass
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

def get_current_version() -> str:
    v_file = os.path.join(BASE_DIR, "VERSION")
    if os.path.exists(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    return v
        except Exception:
            pass
    try:
        from core import __version__
        return __version__
    except Exception:
        return "2.8.9"

VERSION = get_current_version()

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

# Global execution state (Optimization #3: deque maxlen=500 circular buffer for O(1) appending)
current_task = {
    "type": None,  # "backup", "restore", "verify", None
    "running": False,
    "progress": {},
    "logs": deque(maxlen=500),
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

scheduler.register_log_callback(append_task_log)

_cached_update_info = {"checked_at": 0, "data": None}

def _background_update_check():
    time.sleep(5)
    try:
        from core.updater import check_for_update
        info = check_for_update()
        _cached_update_info["checked_at"] = time.time()
        _cached_update_info["data"] = info
        if info and info.get("update_available"):
            append_task_log(f"[소프트웨어 업데이트] 새 버전 v{info['latest_version']} 배포가 감지되었습니다. (현재: v{info['current_version']})")
    except Exception as e_up:
        append_task_log(f"[소프트웨어 업데이트] 업데이트 확인 알림: {e_up}", level="WARN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    append_task_log("백업 스케줄러 서비스가 시작되었습니다.")
    # Durable Replication Queue: auto-resume interrupted tasks on startup
    try:
        from core.replication_queue import ReplicationQueueManager
        candidate_repos = _get_all_candidate_repos()
        for cand in candidate_repos:
            rq = ReplicationQueueManager(cand)
            resumed = rq.resume_all_interrupted()
            if resumed > 0:
                append_task_log(f"[Durable Queue] 미완료 오프사이트 복제 {resumed}건 자동 재개 (저장소: {os.path.basename(cand)})")
            rq.start_background_worker()
    except Exception as e_rq:
        append_task_log(f"[Durable Queue] 초기화 알림: {e_rq}", level="WARN")

    # Firebase Cloud Sync: 최신 백업 상태 클라우드 동기화
    try:
        from core.firebase_sync import upload_current_system_status
        threading.Thread(target=upload_current_system_status, daemon=True).start()
        append_task_log("[Firebase] 클라우드(sunhang-772e5) 실시간 백업 동기화가 활성화되었습니다.")
    except Exception as e_fb:
        append_task_log(f"[Firebase] 동기화 초기화 알림: {e_fb}", level="WARN")

    # Software Auto-Update Check
    try:
        threading.Thread(target=_background_update_check, daemon=True).start()
    except Exception:
        pass

    yield
    scheduler.stop()

app = FastAPI(title="Server & System Backup Manager", version="2.1.4", lifespan=lifespan)

# ==================== Auth Pydantic Models ====================
class AuthSetupRequest(BaseModel):
    password: str = Field(..., min_length=4, description="최소 4자 이상의 마스터 비밀번호")
    allow_localhost_bypass: bool = Field(default=True, description="로컬 루프백 접속 시 인증 우회 여부")

class AuthLoginRequest(BaseModel):
    password: str = Field(..., description="마스터 비밀번호")

class AuthChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=4, description="최소 4자 이상의 새 비밀번호")

class AuthBypassRequest(BaseModel):
    enabled: bool = Field(..., description="로컬 루프백 인증 우회 활성화 여부")


# ==================== Auth HTTP Middleware ====================
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    
    # 인증 불필요 경로 (정적 리소스, 인증 API, favicon, 원격 릴리즈 배포 API)
    if (
        path.startswith("/static") or
        path.startswith("/api/auth/") or
        path == "/favicon.ico" or
        path in ("/api/system/release-info", "/api/system/update-package")
    ):
        return await call_next(request)
    
    # 마스터 비밀번호 미설정 상태: 진입 허용 (UI에서 셋업 모달 표시)
    if not is_auth_configured():
        return await call_next(request)
    
    # 클라이언트 IP 기반 로컬 루프백 바이패스 검사
    client_ip = request.client.host if request.client else ""
    auth_st = get_auth_status(client_ip)
    if auth_st.get("bypassed"):
        return await call_next(request)
    
    # 세션 토큰 추출 (쿠키 우선, Bearer 헤더 보조)
    token = request.cookies.get("backup_session")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    
    # 유효한 세션인 경우 통과
    if token and validate_session(token):
        return await call_next(request)
    
    # API 요청인데 인증 실패 시 401 JSON 응답 반환
    if path.startswith("/api/"):
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": "인증이 필요합니다.",
                "auth_required": True
            }
        )
    
    # 대시보드 페이지(/) 등 일반 요청은 통과 (프론트엔드에서 로그인 모달 표시)
    return await call_next(request)


# ==================== Auth Endpoints ====================
@app.get("/api/auth/status")
async def auth_status(request: Request):
    client_ip = request.client.host if request.client else ""
    status = get_auth_status(client_ip)
    token = request.cookies.get("backup_session")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    status["authenticated"] = bool(token and validate_session(token))
    return JSONResponse(content={"success": True, "data": status})

@app.post("/api/auth/setup")
async def auth_setup(req: AuthSetupRequest):
    try:
        setup_master_password(req.password, req.allow_localhost_bypass)
        return JSONResponse(content={"success": True, "message": "마스터 비밀번호가 성공적으로 설정되었습니다."})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": f"설정 중 오류: {str(e)}"})

@app.post("/api/auth/login")
async def auth_login(req: AuthLoginRequest):
    if not verify_master_password(req.password):
        return JSONResponse(status_code=401, content={"success": False, "error": "비밀번호가 일치하지 않습니다."})
    token = create_session()
    resp = JSONResponse(content={"success": True, "token": token, "message": "로그인 성공"})
    resp.set_cookie(
        key="backup_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30,
        path="/"
    )
    return resp

@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    token = request.cookies.get("backup_session")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if token:
        revoke_session(token)
    resp = JSONResponse(content={"success": True, "message": "로그아웃 성공"})
    resp.delete_cookie("backup_session", path="/")
    return resp

@app.post("/api/auth/change-password")
async def auth_change_password(req: AuthChangePasswordRequest):
    try:
        change_master_password(req.old_password, req.new_password)
        return JSONResponse(content={"success": True, "message": "비밀번호가 성공적으로 변경되었습니다."})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": f"변경 중 오류: {str(e)}"})

@app.post("/api/auth/toggle-bypass")
async def auth_toggle_bypass(req: AuthBypassRequest):
    try:
        set_localhost_bypass(req.enabled)
        return JSONResponse(content={"success": True, "message": f"로컬 루프백 자동 우회 설정이 {'활성화' if req.enabled else '비활성화'}되었습니다."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": f"설정 변경 중 오류: {str(e)}"})

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- Web UI Route ---
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "v_ts": int(time.time())})

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
                s["is_local_protected"] = s.get("is_verified", True)

                # Query Durable Replication Queue status
                try:
                    from core.replication_queue import ReplicationQueueManager
                    rq = ReplicationQueueManager(r)
                    q_info = rq.get_status(sid)
                    if q_info:
                        s["offsite_status"] = q_info.get("state", "NONE")
                        s["is_offsite_protected"] = (q_info.get("state") == "COMMITTED")
                    else:
                        s["offsite_status"] = "NONE"
                        s["is_offsite_protected"] = False
                except Exception:
                    s["offsite_status"] = "NONE"
                    s["is_offsite_protected"] = False

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
def get_snapshot(snapshot_id: str, repo_dir: Optional[str] = None, include_entries: bool = False):
    r = _find_snapshot_repo(snapshot_id, repo_dir)
    if not r:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    data = SnapshotEngine.get_snapshot(r, snapshot_id)
    if not data:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    if not include_entries:
        # Strip massive entries array to send lightweight metadata (0.001s response, ~500 bytes)
        return {
            "id": data.get("id"),
            "created_at": data.get("created_at"),
            "iso_time": data.get("iso_time"),
            "profile_id": data.get("profile_id"),
            "profile_name": data.get("profile_name"),
            "backup_type": data.get("backup_type"),
            "base_snapshot_id": data.get("base_snapshot_id"),
            "sources": data.get("sources", []),
            "summary": data.get("summary", {})
        }
    return data

@app.get("/api/snapshots/{snapshot_id}/browse")
def browse_snapshot(snapshot_id: str, subpath: str = "", repo_dir: Optional[str] = None):
    r = _find_snapshot_repo(snapshot_id, repo_dir)
    if not r:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    try:
        return SnapshotEngine.browse_snapshot_directory(r, snapshot_id, subpath=subpath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    success = SnapshotEngine.delete_snapshot(r, snapshot_id, authorized=True)
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

        # Firebase Cloud Sync
        try:
            from core.firebase_sync import async_upload_backup_status
            async_upload_backup_status(manifest_summary=manifest_summary, status="success", repo_dir=repo_dir)
            append_task_log("[Firebase] 선택 백업 결과 클라우드 실시간 동기화 완료")
        except Exception as e_fb:
            append_task_log(f"[Firebase] 동기화 알림: {e_fb}", level="WARNING")

    except InterruptedError:
        append_task_log("사용자에 의해 백업 작업이 취소되었습니다.", level="WARNING")
        with task_lock:
            current_task["error"] = "Cancelled by user"
    except Exception as e:
        from core.lock import BackupAlreadyRunningError
        from core.storage import InsufficientDiskSpaceError
        from core.vss_manager import VSSRequiredError
        from core.verify import RestoreVerificationError
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
            "vss_enabled": manifest.get("vss_enabled", False),
            "summary": manifest.get("summary")
        }
        del manifest
        import gc
        gc.collect()

        with task_lock:
            current_task["result"] = manifest_summary
            current_task["error"] = None

        # Firebase Cloud Sync
        try:
            from core.firebase_sync import async_upload_backup_status
            async_upload_backup_status(manifest_summary=manifest_summary, status="success", repo_dir=repo_dir)
            append_task_log("[Firebase] 백업 결과 클라우드 실시간 동기화 완료")
        except Exception as e_fb:
            append_task_log(f"[Firebase] 동기화 알림: {e_fb}", level="WARNING")

    except InterruptedError:
        append_task_log("사용자에 의해 백업 작업이 취소되었습니다.", level="WARNING")
        with task_lock:
            current_task["error"] = "Cancelled by user"
    except Exception as e:
        from core.lock import BackupAlreadyRunningError
        from core.storage import InsufficientDiskSpaceError
        from core.vss_manager import VSSRequiredError
        from core.verify import RestoreVerificationError
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
            "logs": list(current_task["logs"])[-30:],
            "start_time": current_task["start_time"],
            "result": current_task["result"],
            "error": current_task["error"]
        }

# --- Restore Execution API ---
class RunRestoreRequest(BaseModel):
    snapshot_id: str
    target_dir: Optional[str] = None
    repo_dir: Optional[str] = None
    selected_rel_paths: Optional[List[str]] = None
    overwrite: bool = True
    in_place: bool = False

def _background_restore_task(params: Dict[str, Any]):
    global current_task
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

# --- Remote Self-Update API (P0 Security: Ed25519 Signature Verification & Anti-Zip-Slip) ---
@app.post("/api/system/self-update")
async def self_update(request: Request = None, custom_body: bytes = None, custom_signature: str = ""):
    """
    Receives raw zip binary of latest code, verifies Ed25519 cryptographic signature,
    extracts it safely over BASE_DIR with Zip-Slip protection, and restarts the service.
    """
    if custom_body is not None:
        body = custom_body
    elif request:
        body = await request.body()
    else:
        body = b""

    if not body:
        raise HTTPException(status_code=400, detail="업데이트 페이로드가 비어 있습니다.")

    # 1. Ed25519 Signature Verification
    signature_raw = custom_signature.strip() if custom_signature else (request.headers.get("X-Package-Signature", "").strip() if request else "")
    if not signature_raw:
        raise HTTPException(
            status_code=403,
            detail="업데이트 패키지 서명 누락: X-Package-Signature 헤더가 필요합니다."
        )

    # Convert Base64 or Hex to Hex format for verify_bytes_ed25519
    signature_hex = signature_raw
    if len(signature_raw) == 88 or signature_raw.endswith("="):
        try:
            signature_hex = base64.b64decode(signature_raw).hex()
        except Exception:
            raise HTTPException(status_code=403, detail="서명 인코딩 형식 오류")

    pub_key_path = os.path.join(BASE_DIR, "keys", "release_ed25519.pub")
    if not os.path.exists(pub_key_path):
        raise HTTPException(
            status_code=403,
            detail="업데이트 거부: 서버에 Ed25519 릴리즈 공개키(release_ed25519.pub)가 등록되지 않았습니다."
        )

    try:
        from core.crypto_sign import verify_bytes_ed25519
        if not verify_bytes_ed25519(body, signature_hex, pub_key_path):
            raise HTTPException(
                status_code=403,
                detail="패키지 전자서명 검증 실패: 유효하지 않거나 변조된 업데이트 패키지입니다."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=f"전자서명 검증 중 오류 발생: {str(e)}"
        )

    import io
    import zipfile
    import subprocess

    # 2. Safe Zip Extraction with Path Traversal (Zip-Slip) Protection
    base_dir_abs = os.path.abspath(BASE_DIR)
    try:
        with zipfile.ZipFile(io.BytesIO(body), "r") as zf:
            file_names = zf.namelist()
            if not any("core" in fn or "web" in fn or "run.py" in fn for fn in file_names):
                raise HTTPException(status_code=400, detail="유효하지 않은 업데이트 패키지: 핵심 구성요소가 누락되었습니다.")

            for member in zf.infolist():
                dest_path = os.path.abspath(os.path.join(base_dir_abs, member.filename))
                if not (dest_path == base_dir_abs or dest_path.startswith(base_dir_abs + os.sep)):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Zip-Slip 보안 위협 탐지: 허용되지 않은 경로 탈출 ({member.filename})"
                    )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"압축 패키지 검증 오류: {str(e)}")

    temp_zip = os.path.join(tempfile.gettempdir(), f"backup_update_{int(time.time())}.zip")
    with open(temp_zip, "wb") as f:
        f.write(body)

    updater_bat = os.path.join(tempfile.gettempdir(), f"run_updater_{int(time.time())}.bat")
    pyw_candidate = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    launch_py = pyw_candidate if os.path.exists(pyw_candidate) else sys.executable

    # Windows CRLF & Ghost/Silent compliant batch script
    bat_content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "ping 127.0.0.1 -n 2 >nul\r\n"
        f"tar -xf \"{temp_zip}\" -C \"{BASE_DIR}\"\r\n"
        f"cd /d \"{BASE_DIR}\"\r\n"
        f"start \"\" \"{launch_py}\" run.py\r\n"
        f"del \"{temp_zip}\" >nul 2>&1\r\n"
        "del \"%~f0\" >nul 2>&1\r\n"
        "exit /b 0\r\n"
    )
    with open(updater_bat, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(bat_content)

    def _trigger_update_and_restart():
        time.sleep(0.8)
        flags = 0x00000200
        if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags |= subprocess.CREATE_NO_WINDOW
        else:
            flags |= 0x00000008
        subprocess.Popen(
            ["cmd.exe", "/c", updater_bat],
            creationflags=flags,
            close_fds=True
        )
        time.sleep(0.2)
        os._exit(0)

    threading.Thread(target=_trigger_update_and_restart, daemon=True).start()
    return {
        "success": True,
        "message": f"Ed25519 서명 검증 통과! 최신 패키지({len(body):,} 바이트)를 안전하게 수신했습니다. 1초 후 자동으로 적용되고 재시작됩니다."
    }


# =========================================================================
# Remote Master Release Origin & One-Click Sync Endpoints
# =========================================================================

@app.get("/api/system/release-info")
def get_release_info():
    """
    Returns latest release package metadata and Ed25519 signature for remote clients.
    """
    dist_dir = os.path.join(BASE_DIR, "dist")
    zip_path = os.path.join(dist_dir, f"release_v{VERSION}.zip")
    sig_path = zip_path + ".sig"

    has_pkg = os.path.exists(zip_path)
    pkg_size = os.path.getsize(zip_path) if has_pkg else 0
    signature = ""
    if os.path.exists(sig_path):
        try:
            with open(sig_path, "r", encoding="utf-8") as f:
                signature = f.read().strip()
        except Exception:
            pass

    return {
        "success": True,
        "data": {
            "version": VERSION,
            "has_package": has_pkg,
            "package_name": f"release_v{VERSION}.zip",
            "package_size": pkg_size,
            "signature": signature,
            "updated_at": os.path.getmtime(zip_path) if has_pkg else time.time()
        }
    }


@app.get("/api/system/update-package")
def download_update_package():
    """
    Streams the signed release zip package to client machines.
    """
    dist_dir = os.path.join(BASE_DIR, "dist")
    zip_path = os.path.join(dist_dir, f"release_v{VERSION}.zip")
    sig_path = zip_path + ".sig"

    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail=f"릴리즈 패키지(v{VERSION})가 준비되지 않았습니다.")

    signature = ""
    if os.path.exists(sig_path):
        try:
            with open(sig_path, "r", encoding="utf-8") as f:
                signature = f.read().strip()
        except Exception:
            pass

    return FileResponse(
        zip_path,
        media_type="application/octet-stream",
        filename=f"release_v{VERSION}.zip",
        headers={"X-Package-Signature": signature}
    )


@app.get("/api/system/check-remote-release")
def check_remote_release(master_url: str = "http://100.72.224.71:8765"):
    """
    Queries the master release origin (K12) to detect if an updated release is available.
    """
    master_url = master_url.rstrip("/")
    if master_url.startswith("http://127.0.0.1") or master_url.startswith("http://localhost"):
        return {"success": True, "data": {"update_available": False, "is_self": True, "current_version": VERSION}}

    try:
        req = urllib.request.Request(f"{master_url}/api/system/release-info", headers={"User-Agent": "BackupSystem-Client"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("success"):
            return {"success": False, "error": "마스터 서버 응답 오류"}

        r_info = data.get("data", {})
        r_ver = r_info.get("version", "")

        def _parse_v(v_str):
            try:
                return tuple(int(x) for x in v_str.replace("v", "").split(".")[:3])
            except Exception:
                return (0, 0, 0)

        cur_v = _parse_v(VERSION)
        rem_v = _parse_v(r_ver)

        update_available = rem_v > cur_v

        return {
            "success": True,
            "data": {
                "update_available": update_available,
                "current_version": VERSION,
                "remote_version": r_ver,
                "remote_url": master_url,
                "package_size": r_info.get("package_size", 0),
                "signature": r_info.get("signature", "")
            }
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "update_available": False,
                "current_version": VERSION,
                "master_online": False,
                "error": str(e)
            }
        }


@app.post("/api/system/sync-remote-release")
async def sync_remote_release(request: Request):
    """
    Downloads signed release from master server and applies self-update automatically.
    """
    try:
        body_json = await request.json()
    except Exception:
        body_json = {}

    master_url = body_json.get("master_url", "http://100.72.224.71:8765").rstrip("/")

    # 1. Fetch package from master server
    try:
        req = urllib.request.Request(f"{master_url}/api/system/update-package", headers={"User-Agent": "BackupSystem-Client"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            sig_header = resp.headers.get("X-Package-Signature", "")
            pkg_bytes = resp.read()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"마스터 서버 패키지 다운로드 실패: {str(e)}")

    if not pkg_bytes:
        raise HTTPException(status_code=502, detail="다운로드된 패키지가 비어있습니다.")

    # 2. Invoke self_update pipeline directly
    return await self_update(request, custom_body=pkg_bytes, custom_signature=sig_header)


# --- Real-time Global Alert Summary API (Red Alert System) ---
@app.get("/api/alerts/summary")
def get_alerts_summary():
    """
    Aggregates recent backup failures, active repository free disk space,
    and replication queue backlogs to compute real-time alert status for UI banner.
    """
    alerts = []
    status = "ok"

    # 1. Check Backup History (Last 24h)
    try:
        profiles = ConfigManager.get_profiles()
        now_ts = time.time()
        for profile in profiles:
            last_status = profile.get("last_status")
            last_run = profile.get("last_run", 0)
            p_name = profile.get("name", "기본 프로필")

            if last_status == "failed" and (now_ts - last_run < 86400):
                alerts.append({
                    "type": "backup_failure",
                    "severity": "critical",
                    "title": "백업 실패 감지",
                    "message": f"프로필 '{p_name}'의 최근 백업이 실패했습니다. 저장소 상태 및 로그를 확인하세요."
                })
                status = "critical"
    except Exception as e:
        alerts.append({
            "type": "config_error",
            "severity": "warning",
            "title": "설정 조회 오류",
            "message": f"프로필 상태 점검 중 오류: {str(e)}"
        })
        if status != "critical":
            status = "warning"

    # 2. Check Active Repository Disk Space
    active_repo = None
    disk_info = {"total_gb": 0.0, "free_gb": 0.0, "free_percent": 100.0}
    try:
        profiles = ConfigManager.get_profiles()
        if profiles:
            active_repo = profiles[0].get("repo_dir")
            if active_repo and os.path.exists(active_repo):
                drive = os.path.splitdrive(active_repo)[0]
                if not drive:
                    drive = os.path.splitdrive(os.path.abspath(active_repo))[0]
                if drive:
                    total, used, free = shutil.disk_usage(drive)
                    total_gb = round(total / (1024 ** 3), 1)
                    free_gb = round(free / (1024 ** 3), 1)
                    free_pct = round((free / total) * 100, 1) if total > 0 else 0.0
                    disk_info = {"total_gb": total_gb, "free_gb": free_gb, "free_percent": free_pct}

                    if free_pct < 5.0:
                        alerts.append({
                            "type": "disk_critical",
                            "severity": "critical",
                            "title": "디스크 용량 고갈 위험",
                            "message": f"저장소 드라이브({drive}) 여유 공간이 5% 미만({free_pct}%, 잔여 {free_gb} GB)입니다."
                        })
                        status = "critical"
                    elif free_pct < 10.0:
                        alerts.append({
                            "type": "disk_warning",
                            "severity": "warning",
                            "title": "디스크 용량 부족 경고",
                            "message": f"저장소 드라이브({drive}) 여유 공간이 10% 미만({free_pct}%, 잔여 {free_gb} GB)입니다."
                        })
                        if status != "critical":
                            status = "warning"
    except Exception:
        pass

    # 3. Check Replication Queue
    try:
        from core.replication_queue import ReplicationQueueManager
        candidate_repos = _get_all_candidate_repos()
        total_interrupted = 0
        total_pending = 0
        for cand in candidate_repos:
            rq = ReplicationQueueManager(cand)
            status_map = rq.get_status_summary()
            total_pending += status_map.get("pending", 0)
            total_interrupted += status_map.get("interrupted", 0)

        if total_interrupted > 0:
            alerts.append({
                "type": "replication_interrupted",
                "severity": "warning",
                "title": "오프사이트 복제 지연",
                "message": f"네트워크 단절로 중단된 복제 작업이 {total_interrupted}건 있습니다. 대기열에서 자동 재시도됩니다."
            })
            if status != "critical":
                status = "warning"
    except Exception:
        pass

    return {
        "success": True,
        "data": {
            "status": status,
            "badge_color": "red" if status == "critical" else ("yellow" if status == "warning" else "green"),
            "alerts": alerts,
            "disk": disk_info
        }
    }


# ==================== Firebase Cloud Sync API ====================
@app.get("/api/firebase/status")
def get_firebase_sync_status():
    """현재 기기 식별 정보 및 Firebase 연동 설정 반환"""
    from core.firebase_sync import get_current_device_info, FIREBASE_PROJECT_ID, FIREBASE_API_KEY
    dev = get_current_device_info()
    return {
        "success": True,
        "firebase_project_id": FIREBASE_PROJECT_ID,
        "device": dev,
        "enabled": True
    }


@app.post("/api/firebase/sync")
def trigger_firebase_sync(background_tasks: BackgroundTasks):
    """현재 백업 상태를 Firebase Firestore에 즉시 수동 동기화"""
    from core.firebase_sync import upload_current_system_status
    try:
        res = upload_current_system_status()
        append_task_log("[Firebase] 수동 클라우드 동기화 완료")
        return {"success": True, "result": res}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/firebase/history")
def get_firebase_cloud_history(limit: int = 50):
    """Firestore backup_history 컬렉션에서 전체 기기의 백업 이력 반환"""
    from core.firebase_sync import fetch_cloud_backup_history
    try:
        items = fetch_cloud_backup_history(limit=limit)
        return {"success": True, "count": len(items), "history": items}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ==================== Software Auto-Update API ====================
@app.get("/api/update/status")
def get_software_update_status(force_check: bool = False):
    """최신 소프트웨어 릴리즈 업데이트 상태 반환"""
    from core.updater import check_for_update, get_current_installed_version
    now = time.time()
    # Cache for 10 minutes unless force_check is requested
    if force_check or _cached_update_info["data"] is None or (now - _cached_update_info["checked_at"] > 600):
        info = check_for_update()
        _cached_update_info["checked_at"] = now
        _cached_update_info["data"] = info
    else:
        info = _cached_update_info["data"]

    cur_ver = get_current_installed_version()
    if info and info.get("update_available"):
        return {
            "success": True,
            "update_available": True,
            "current_version": cur_ver,
            "latest_version": info.get("latest_version"),
            "mandatory": info.get("mandatory", False),
            "changelog": info.get("changelog", ""),
            "download_url": info.get("download_url", "")
        }
    return {
        "success": True,
        "update_available": False,
        "current_version": cur_ver,
        "latest_version": cur_ver,
        "message": "최신 버전을 사용 중입니다."
    }


@app.post("/api/update/apply")
def trigger_software_update(background_tasks: BackgroundTasks):
    """클라우드에서 최신 패키지를 다운로드/검증 후 백그라운드 안전 설치"""
    from core.updater import perform_full_update_pipeline
    def _run_pipeline():
        append_task_log("[소프트웨어 업데이트] 최신 버전 다운로드 및 무결성 검증 착수...")
        res = perform_full_update_pipeline()
        append_task_log(f"[소프트웨어 업데이트] 결과: {res.get('message', res.get('status'))}")

    background_tasks.add_task(_run_pipeline)
    return {
        "success": True,
        "message": "자동 업데이트 프로세스가 백그라운드에서 시작되었습니다."
    }


