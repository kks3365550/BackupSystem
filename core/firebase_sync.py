# -*- coding: utf-8 -*-
"""
core/firebase_sync.py

Firebase Firestore REST API 연동 모듈.
외부 무거운 라이브러리(pip) 없이 Python 표준 라이브러리(urllib, json, socket)만으로
사내 Firebase(sunhang-772e5)에 백업 상태 및 이력을 실시간 업로드합니다.
"""

import os
import json
import socket
import logging
import datetime
import threading
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

FIREBASE_PROJECT_ID = "sunhang-772e5"
FIREBASE_API_KEY = "AIzaSyCe21skNfRno3PPo-xRYCqfwh3jtboo7Ls"
FIRESTORE_REST_BASE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"

logger = logging.getLogger("firebase_sync")

# 기기 IP 매핑
DEVICE_MAP = {
    "100.72.224.71": {
        "id": "minipc",
        "name": "내 미니피씨 (100.72.224.71)",
        "role": "원래 주기 유지 (매일 09:00 자동 백업)",
        "auto_backup": True
    },
    "100.90.20.59": {
        "id": "desktop",
        "name": "내 데스크탑 (100.90.20.59)",
        "role": "수동 백업 전용 (자동 백업 비활성화)",
        "auto_backup": False
    }
}


def get_all_local_ips() -> List[str]:
    """현재 머신의 모든 활성 IPv4 주소 목록 반환"""
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    try:
        # 외부 연결 테스트용 더미 소켓
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return list(ips)


def get_current_device_info() -> Dict[str, Any]:
    """현재 기기 정보 자동 식별"""
    local_ips = get_all_local_ips()
    for ip, info in DEVICE_MAP.items():
        if ip in local_ips:
            res = dict(info)
            res["current_ip"] = ip
            return res

    # Tailscale IP 대역 매칭 또는 호스트명 폴백
    hname = socket.gethostname().lower()
    if "desktop" in hname or "r2pfnfp" in hname:
        res = dict(DEVICE_MAP["100.90.20.59"])
        res["current_ip"] = "100.90.20.59 (추정)"
        return res

    # 기본값: 미니피씨
    res = dict(DEVICE_MAP["100.72.224.71"])
    res["current_ip"] = local_ips[0] if local_ips else "100.72.224.71"
    return res


def _to_firestore_value(val: Any) -> Dict[str, Any]:
    """Python 원시 타입을 Firestore REST API Value 스키마로 변환"""
    if val is None:
        return {"nullValue": None}
    elif isinstance(val, bool):
        return {"booleanValue": val}
    elif isinstance(val, int):
        return {"integerValue": str(val)}
    elif isinstance(val, float):
        return {"doubleValue": float(val)}
    elif isinstance(val, str):
        return {"stringValue": str(val)}
    elif isinstance(val, list):
        return {"arrayValue": {"values": [_to_firestore_value(v) for v in val]}}
    elif isinstance(val, dict):
        return {"mapValue": {"fields": {k: _to_firestore_value(v) for k, v in val.items()}}}
    else:
        return {"stringValue": str(val)}


def _dict_to_firestore_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Python dict를 Firestore REST fields 구조로 변환"""
    return {k: _to_firestore_value(v) for k, v in data.items()}


def upload_backup_status(
    manifest_summary: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    repo_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    백업 상태를 Firestore `backup_devices/{device_id}`에 업로드하고,
    스냅샷 요약이 있으면 `backup_history`에도 이력을 기록합니다.
    """
    dev = get_current_device_info()
    device_id = dev["id"]
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 디스크 잔여 용량 계산
    free_gb = 0.0
    try:
        import shutil
        target_dir = repo_dir or "D:\\" if os.path.exists("D:\\") else "C:\\"
        usage = shutil.disk_usage(target_dir)
        free_gb = round(usage.free / (1024 ** 3), 1)
    except Exception:
        pass

    # 디바이스 현황 데이터 구성
    device_payload = {
        "device_id": device_id,
        "device_name": dev["name"],
        "role": dev["role"],
        "auto_backup_enabled": dev["auto_backup"],
        "last_status": status,
        "last_updated": now_iso,
        "free_disk_gb": free_gb,
        "ip": dev.get("current_ip", "")
    }

    if error_message:
        device_payload["last_error"] = str(error_message)

    if manifest_summary:
        summary = manifest_summary.get("summary") or {}
        device_payload.update({
            "last_snapshot_id": manifest_summary.get("id", ""),
            "last_backup_time": manifest_summary.get("created_at") or now_iso,
            "profile_name": manifest_summary.get("profile_name", ""),
            "total_files": summary.get("total_files", 0),
            "total_bytes": summary.get("total_bytes", 0),
            "new_files": summary.get("new_files", 0) + summary.get("modified_files", 0),
            "dedup_saved_bytes": summary.get("dedup_saved_bytes", 0),
            "duration_seconds": summary.get("duration_seconds", 0),
            "vss_enabled": manifest_summary.get("vss_enabled", False)
        })

    # 1. backup_devices/{device_id} 업데이트 (PATCH)
    dev_url = f"{FIRESTORE_REST_BASE}/backup_devices/{device_id}?key={FIREBASE_API_KEY}"
    body = json.dumps({"fields": _dict_to_firestore_fields(device_payload)}).encode("utf-8")
    
    result = {"success": False, "device_id": device_id}
    try:
        req = urllib.request.Request(
            dev_url,
            data=body,
            method="PATCH",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status in (200, 201):
                result["success"] = True
                result["device_updated"] = True
    except Exception as e:
        logger.warning(f"Firestore backup_devices 업로드 실패: {e}")
        result["device_error"] = str(e)

    # 2. 백업 이력이 있고 성공인 경우 backup_history 컬렉션에 새 문서 생성 또는 갱신 (PATCH)
    if manifest_summary and status == "success":
        hist_id = manifest_summary.get("id") or f"hist_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        hist_url = f"{FIRESTORE_REST_BASE}/backup_history/{hist_id}?key={FIREBASE_API_KEY}"
        hist_payload = dict(device_payload)
        hist_payload["history_id"] = hist_id
        hist_body = json.dumps({"fields": _dict_to_firestore_fields(hist_payload)}).encode("utf-8")
        try:
            req_h = urllib.request.Request(
                hist_url,
                data=hist_body,
                method="PATCH",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req_h, timeout=8) as resp_h:
                if resp_h.status in (200, 201):
                    result["history_created"] = True
        except Exception as e_h:
            logger.warning(f"Firestore backup_history 기록 실패: {e_h}")
            result["history_error"] = str(e_h)

    return result


def async_upload_backup_status(
    manifest_summary: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    repo_dir: Optional[str] = None
):
    """메인 프로세스를 블로킹하지 않도록 데몬 스레드로 백그라운드 업로드"""
    t = threading.Thread(
        target=upload_backup_status,
        kwargs={
            "manifest_summary": manifest_summary,
            "status": status,
            "error_message": error_message,
            "repo_dir": repo_dir
        },
        daemon=True
    )
    t.start()


def upload_current_system_status() -> Dict[str, Any]:
    """시스템 시작 시 또는 수동 동기화 시 최신 스냅샷 요약 정보를 Firestore에 동기화"""
    try:
        from core.snapshot import SnapshotEngine
        from core.config import ConfigManager

        # 최신 스냅샷 탐색
        candidates = ["D:\\MyBackup_Repository", "C:\\MyBackup_Repository", os.path.join(os.path.expanduser("~"), "MyBackup_Repository")]
        profiles = ConfigManager.get_profiles()
        for p in profiles:
            r = p.get("repo_dir")
            if r and r not in candidates:
                candidates.insert(0, r)

        latest_snap = None
        target_repo = None
        for cand in candidates:
            if os.path.exists(cand):
                snaps = SnapshotEngine.list_snapshots(cand)
                if snaps:
                    latest_snap = snaps[0]
                    target_repo = cand
                    break

        return upload_backup_status(
            manifest_summary=latest_snap,
            status="success",
            repo_dir=target_repo
        )
    except Exception as e:
        logger.warning(f"upload_current_system_status 실패: {e}")
        return {"success": False, "error": str(e)}
