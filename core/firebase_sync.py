# -*- coding: utf-8 -*-
"""
core/firebase_sync.py

Firebase Firestore REST API 연동 모듈 (v2.9.0).
- last_backup_success와 last_backup_attempt 명확 분리
- 기기별(미니PC vs 데스크탑) 차등 다단계 Stale 감지
- 백업 실패(FAILED) 이벤트도 원인 메시지와 함께 backup_history에 영구 보존
- 클라우드 백업 이력 조회(fetch_backup_history) 지원
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

# 기기별 Stale 임계치 정책
STALE_POLICIES = {
    "minipc": {
        "normal_days": 2.0,
        "critical_days": 4.0
    },
    "desktop": {
        "normal_days": 3.0,
        "prepare_days": 7.0,
        "warning_days": 14.0
    }
}


def calculate_stale_status(device_id: str, last_success_ts: Optional[float]) -> Dict[str, Any]:
    """마지막 성공 백업 기준 경과일 및 다단계 Stale 상태 계산"""
    if not last_success_ts or last_success_ts <= 0:
        return {
            "level": "unknown",
            "badge_color": "slate",
            "label": "백업 이력 없음",
            "days_elapsed": -1
        }

    now = datetime.datetime.now().timestamp()
    days = max(0.0, round((now - last_success_ts) / 86400.0, 1))

    if device_id == "minipc":
        if days <= 2.0:
            return {"level": "normal", "badge_color": "emerald", "label": f"정상 가동 ({days}일 경과)", "days_elapsed": days}
        elif days <= 4.0:
            return {"level": "warning", "badge_color": "amber", "label": f"자동 백업 지연 ({days}일 경과)", "days_elapsed": days}
        else:
            return {"level": "critical", "badge_color": "red", "label": f"시스템 점검 필요 ({days}일 경과)", "days_elapsed": days}
    else:  # desktop
        if days <= 3.0:
            return {"level": "normal", "badge_color": "emerald", "label": f"정상 ({days}일 전)", "days_elapsed": days}
        elif days <= 7.0:
            return {"level": "prepare", "badge_color": "blue", "label": f"백업 준비 권장 ({days}일 경과)", "days_elapsed": days}
        elif days <= 14.0:
            return {"level": "warning", "badge_color": "amber", "label": f"⚠️ 백업 권장 ({days}일 경과)", "days_elapsed": days}
        else:
            return {"level": "critical", "badge_color": "red", "label": f"🔴 장기 미백업 ({days}일 경과)", "days_elapsed": days}


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

    hname = socket.gethostname().lower()
    if "desktop" in hname or "r2pfnfp" in hname:
        res = dict(DEVICE_MAP["100.90.20.59"])
        res["current_ip"] = "100.90.20.59 (추정)"
        return res

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
    성공/실패 이벤트를 `backup_history`에 영구 기록합니다.
    (마지막 성공 백업과 마지막 백업 시도를 엄격히 분리)
    """
    dev = get_current_device_info()
    device_id = dev["id"]
    now_dt = datetime.datetime.now()
    now_iso = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_ts = now_dt.timestamp()

    # 디스크 잔여 용량 계산
    free_gb = 0.0
    try:
        import shutil
        target_dir = repo_dir or ("D:\\" if os.path.exists("D:\\") else "C:\\")
        usage = shutil.disk_usage(target_dir)
        free_gb = round(usage.free / (1024 ** 3), 1)
    except Exception:
        pass

    # 1. 마지막 백업 시도(Attempt) 정보
    attempt_info = {
        "time": now_iso,
        "status": status,  # "success" | "failed" | "running"
        "error_message": str(error_message or "")
    }

    # 2. 마지막 성공(Success) 정보
    success_ts = None
    success_info = {}
    if status == "success" and manifest_summary:
        summary = manifest_summary.get("summary") or {}
        created_val = manifest_summary.get("created_at")
        if isinstance(created_val, (int, float)):
            success_ts = float(created_val)
            success_time_str = datetime.datetime.fromtimestamp(success_ts).strftime("%Y-%m-%d %H:%M:%S")
        else:
            success_time_str = str(created_val or now_iso)
            success_ts = now_ts

        success_info = {
            "snapshot_id": manifest_summary.get("id", ""),
            "time": success_time_str,
            "timestamp": success_ts,
            "profile_name": manifest_summary.get("profile_name", ""),
            "total_files": summary.get("total_files", 0),
            "total_bytes": summary.get("total_bytes", 0),
            "new_files": summary.get("new_files", 0) + summary.get("modified_files", 0),
            "dedup_saved_bytes": summary.get("dedup_saved_bytes", 0),
            "duration_seconds": summary.get("duration_seconds", 0),
            "vss_enabled": manifest_summary.get("vss_enabled", False)
        }

    # Stale 계산
    stale_eval = calculate_stale_status(device_id, success_ts or now_ts)

    # 전체 디바이스 페이로드 구성
    device_payload = {
        "device_id": device_id,
        "device_name": dev["name"],
        "role": dev["role"],
        "auto_backup_enabled": dev["auto_backup"],
        "last_status": status,
        "last_updated": now_iso,
        "free_disk_gb": free_gb,
        "ip": dev.get("current_ip", ""),
        "last_attempt": attempt_info,
        "stale_status": stale_eval
    }

    # 성공 시 기존 성공 필드도 갱신
    if success_info:
        device_payload["last_success"] = success_info
        # 호환성을 위한 최상위 축약 필드
        device_payload["last_snapshot_id"] = success_info["snapshot_id"]
        device_payload["last_backup_time"] = success_info["time"]
        device_payload["total_files"] = success_info["total_files"]
        device_payload["total_bytes"] = success_info["total_bytes"]

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

    # 2. backup_history 컬렉션에 이력 영구 기록 (성공 / 실패 모두 기록)
    hist_id = (
        manifest_summary.get("id") if (status == "success" and manifest_summary)
        else f"fail_{device_id}_{now_dt.strftime('%Y%m%d_%H%M%S')}"
    )
    hist_url = f"{FIRESTORE_REST_BASE}/backup_history/{hist_id}?key={FIREBASE_API_KEY}"
    
    hist_payload = {
        "history_id": hist_id,
        "device_id": device_id,
        "device_name": dev["name"],
        "status": status,  # "success" | "failed"
        "timestamp": now_iso,
        "epoch_time": now_ts,
        "error_message": str(error_message or "")
    }

    if status == "success" and success_info:
        hist_payload.update(success_info)

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


def fetch_cloud_backup_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Firestore backup_history 컬렉션에서 전체 기기의 백업 이력 조회"""
    url = f"{FIRESTORE_REST_BASE}/backup_history?pageSize={limit}&key={FIREBASE_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            docs = data.get("documents", [])
            history = []
            for doc in docs:
                fields = doc.get("fields", {})
                item = {}
                for k, v in fields.items():
                    if "stringValue" in v:
                        item[k] = v["stringValue"]
                    elif "integerValue" in v:
                        item[k] = int(v["integerValue"])
                    elif "doubleValue" in v:
                        item[k] = float(v["doubleValue"])
                    elif "booleanValue" in v:
                        item[k] = v["booleanValue"]
                    elif "mapValue" in v:
                        item[k] = v["mapValue"].get("fields", {})
                history.append(item)

            def _extract_sort_ts(x):
                ep = x.get("epoch_time")
                if isinstance(ep, (int, float)):
                    return float(ep)
                ts_str = str(x.get("timestamp") or x.get("time") or "")
                try:
                    return datetime.datetime.fromisoformat(ts_str.replace(" ", "T")).timestamp()
                except Exception:
                    return 0.0

            history.sort(key=_extract_sort_ts, reverse=True)
            return history
    except Exception as e:
        logger.warning(f"fetch_cloud_backup_history 실패: {e}")
        return []
