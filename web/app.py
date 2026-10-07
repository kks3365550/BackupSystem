import os
import sys
import time
import shutil
import threading
import psutil
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.config import ConfigManager
from core.storage import BlobStorage
from core.scheduler import BackupScheduler
from core.app_scanner import get_installed_applications, get_project_items
# 인증 미들웨어에서 필요한 심볼만 남긴다.
# 나머지(설정/로그인/변경/우회 토글)는 web/api_auth.py 로 분리되었다.
from core.auth import is_auth_configured, is_auth_corrupted, get_auth_status, validate_session

# 전역 실행 상태는 web/state.py 가 유일한 소유자다.
# 라우터들이 상태를 공유해야 하므로 app.py 가 직접 들지 않는다.
from web.state import current_task, task_lock, append_task_log

from web.paths import STATIC_DIR, TEMPLATES_DIR
from web.version import get_current_version, VERSION
from web.api_snapshots import (
    router as snapshots_router,
    _get_all_candidate_repos,
)
from web.api_update import (
    router as update_router,
    _background_update_check,
)

__all__ = ["app", "current_task", "task_lock"]


# 모듈 로거 (예외 경로에서 사용)
logger = logging.getLogger("BackupSystem")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

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

# 전역 실행 상태(current_task, task_lock, append_task_log)는 web/state.py 에 있다.
# 라우터 분리 시 상태가 갈라지지 않도록 한 곳에서만 소유한다.
scheduler = BackupScheduler()

scheduler.register_log_callback(append_task_log)

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

    # Software Auto-Update Check
    try:
        threading.Thread(target=_background_update_check, daemon=True).start()
    except Exception:
        pass

    yield
    scheduler.stop()

# version 은 VERSION 파일에서 읽는다 (web/version.py).
# 여기서 하드코딩하면 릴리즈마다 OpenAPI 문서와 실제 버전이 어긋난다.
# v2.13.7 까지 "2.9.22" 로 굳어 있었다.
app = FastAPI(title="Server & System Backup Manager", version=VERSION, lifespan=lifespan)


# ==================== Auth HTTP Middleware ====================
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    
    # 0. 인증 설정 파일 손상 상태 검사 (Fail-Closed: 모든 API 요청 차단)
    if is_auth_corrupted():
        if not (path.startswith("/static") or path == "/favicon.ico" or path == "/api/auth/status"):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "보안 경고(Fail-Closed): auth_config.json 설정 파일이 손상되었습니다. 시스템 보호를 위해 모든 API 요청이 차단되었습니다.",
                    "corrupted": True
                }
            )

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

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 분리된 라우터 등록
# 경로 계약(/api/*)은 app.py 내부 라우터와 동일하게 유지된다.
from web.api_auth import router as auth_router
app.include_router(auth_router)
app.include_router(snapshots_router)
app.include_router(update_router)
from web.api_backup import router as backup_router
app.include_router(backup_router)

# --- Web UI Route ---
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "v_ts": int(time.time()), "version": get_current_version()})

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
    total_chunks = 0
    chunked_files_count = 0
    chunk_strategies = {}

    for r in repos:
        if os.path.exists(r):
            st = BlobStorage(r).get_storage_stats()
            total_blobs += st["total_blobs"]
            stored_bytes += st["stored_bytes"]
            logical_bytes += st["logical_bytes"]
            total_snapshots += st["total_snapshots"]
            total_chunks += st.get("total_chunks", 0)
            chunked_files_count += st.get("chunked_files_count", 0)
            for strat, count in st.get("chunk_strategies", {}).items():
                chunk_strategies[strat] = chunk_strategies.get(strat, 0) + count

    saved_bytes = max(0, logical_bytes - stored_bytes)
    ratio = round((saved_bytes / logical_bytes * 100), 1) if logical_bytes > 0 else 0.0

    return {
        "total_blobs": total_blobs,
        "stored_bytes": stored_bytes,
        "logical_bytes": logical_bytes,
        "total_snapshots": total_snapshots,
        "dedup_saved_bytes": saved_bytes,
        "savings_percentage": ratio,
        "total_chunks": total_chunks,
        "chunked_files_count": chunked_files_count,
        "chunk_strategies": chunk_strategies
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

# --- Installed Applications & Projects Discovery API ---
@app.get("/api/apps/installed")
def list_installed_apps(refresh: bool = False):
    return get_installed_applications(force_refresh=refresh)

@app.get("/api/projects/list")
def list_project_items():
    return get_project_items()

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
    # ReplicationQueueManager 는 이 함수 스코프에서 import 한다.
    # (lifespan 안의 같은 이름 import 는 다른 함수 스코프라 충돌이 아니다)
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



