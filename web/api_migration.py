# -*- coding: utf-8 -*-
"""
web/api_migration.py: 실시간 SSD 마이그레이션(클론 & 부트로더 주입) APIRouter
- C: 드라이브를 다른 물리 SSD로 라이브 캡처 및 클로닝 관리
- 후보 드라이브 조회, 마이그레이션 시작/중단, 상태/로그 조회 API 제공
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.disk_clone import DiskCloneManager, get_candidate_target_drives

router = APIRouter(prefix="/api/migration", tags=["migration"])


class StartMigrationRequest(BaseModel):
    target_drive: str


@router.get("/disks")
async def api_migration_disks():
    """마이그레이션 후보 타겟 SSD/드라이브 목록 조회"""
    try:
        drives = get_candidate_target_drives()
        return {"success": True, "drives": drives}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"후보 드라이브 조회 실패: {str(e)}")


@router.post("/start")
async def api_migration_start(req: StartMigrationRequest):
    """실시간 SSD 마이그레이션 작업 시작"""
    if not req.target_drive:
        raise HTTPException(status_code=400, detail="target_drive 필드는 필수입니다.")

    manager = DiskCloneManager.get_instance()
    res = manager.start_clone(req.target_drive)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "마이그레이션 시작 실패"))

    return {"success": True, "message": res.get("message"), "target_drive": req.target_drive}


@router.get("/status")
async def api_migration_status():
    """현재 마이그레이션 진행 상태 조회"""
    manager = DiskCloneManager.get_instance()
    status = manager.get_status()
    return {"success": True, "status": status}


@router.get("/logs")
async def api_migration_logs(limit: int = 100):
    """마이그레이션 실시간 로그 조회"""
    manager = DiskCloneManager.get_instance()
    logs = manager.get_logs(limit=limit)
    return {"success": True, "logs": logs}


@router.post("/stop")
async def api_migration_stop():
    """진행 중인 마이그레이션 작업 중단"""
    manager = DiskCloneManager.get_instance()
    res = manager.stop_clone()
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "마이그레이션 중단 실패"))
    return {"success": True, "message": res.get("message")}
