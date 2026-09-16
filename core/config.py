import os
import json
import uuid
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
PROFILES_FILE = os.path.join(DATA_DIR, "profiles.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "app_settings.json")

DEFAULT_PROFILE = {
    "id": "prof_default",
    "name": "서버/시스템 메인 백업 프로필",
    "sources": [
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ],
    "repo_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backup_repository")),
    "exclude_patterns": [
        "*.tmp", "*.log", ".git", "__pycache__", "node_modules", "backup_repository"
    ],
    "schedule_type": "interval_hours",
    "schedule_value": "12",
    "auto_backup_enabled": False,
    "retention_count": 30,
    "retention_days": 60,
    "compression_level": 3,
    "min_free_disk_gb": 10,
    "enable_ransomware_protection": True,
    "last_run": None,
    "last_status": "never",
    "last_snapshot_id": None
}

DEFAULT_SETTINGS = {
    "server_port": 8765,
    "server_host": "0.0.0.0",
    "auto_open_browser": True,
    "dark_mode": True,
    "log_level": "INFO",
    "min_free_disk_gb": 10,
    "enable_ransomware_protection": True
}

class ConfigManager:
    @staticmethod
    def _ensure_dir():
        os.makedirs(DATA_DIR, exist_ok=True)

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        cls._ensure_dir()
        if not os.path.exists(SETTINGS_FILE):
            cls.save_settings(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                res = dict(DEFAULT_SETTINGS)
                res.update(data)
                return res
        except Exception:
            return dict(DEFAULT_SETTINGS)

    @classmethod
    def save_settings(cls, settings: Dict[str, Any]):
        cls._ensure_dir()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    @classmethod
    def get_profiles(cls) -> List[Dict[str, Any]]:
        cls._ensure_dir()
        if not os.path.exists(PROFILES_FILE):
            # 최초 1회만: profiles.json이 아예 없을 때만 기본값 생성
            default_p = dict(DEFAULT_PROFILE)
            cls.save_profiles([default_p])
            return [default_p]
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                profiles = json.load(f)
            # 빈 리스트([])는 사용자가 모든 프로필을 삭제한 정상 상태 → 덮어쓰지 않음
            if not isinstance(profiles, list):
                return []
            return profiles
        except Exception:
            # 파싱 실패 시: 손상된 파일을 .bak으로 보존하고 빈 리스트 반환
            # (기본값으로 덮어쓰지 않음 → 데이터 손실 방지)
            try:
                bak_path = PROFILES_FILE + ".bak"
                import shutil
                shutil.copy2(PROFILES_FILE, bak_path)
            except Exception:
                pass
            return []

    @classmethod
    def save_profiles(cls, profiles: List[Dict[str, Any]]):
        cls._ensure_dir()
        # 원자적 쓰기: temp 파일 → os.replace()로 교체 (중간 실패 시 기존 파일 보존)
        tmp_path = PROFILES_FILE + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
            if os.path.exists(PROFILES_FILE):
                os.replace(tmp_path, PROFILES_FILE)
            else:
                os.rename(tmp_path, PROFILES_FILE)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            raise


    @classmethod
    def get_profile(cls, profile_id: str) -> Optional[Dict[str, Any]]:
        profiles = cls.get_profiles()
        for p in profiles:
            if p.get("id") == profile_id:
                return p
        return None

    @classmethod
    def save_profile(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        profiles = cls.get_profiles()
        if not profile.get("id"):
            profile["id"] = f"prof_{uuid.uuid4().hex[:8]}"

        updated = False
        for i, p in enumerate(profiles):
            if p.get("id") == profile["id"]:
                profiles[i] = profile
                updated = True
                break

        if not updated:
            profiles.append(profile)

        cls.save_profiles(profiles)
        return profile

    @classmethod
    def delete_profile(cls, profile_id: str) -> bool:
        profiles = cls.get_profiles()
        initial_len = len(profiles)
        profiles = [p for p in profiles if p.get("id") != profile_id]
        if len(profiles) < initial_len:
            cls.save_profiles(profiles)
            return True
        return False
