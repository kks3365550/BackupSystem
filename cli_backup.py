import os
import sys
import time
import argparse
import datetime
from core.config import ConfigManager
from core.snapshot import SnapshotEngine
from core.driver_backup import export_windows_drivers
from core.registry_backup import collect_full_app_package

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

def run_cli_backup(profile_id: str = None):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === 스마트 원샷 백업 시작 ===")

    # 1. Load profile
    profile = None
    if profile_id:
        profile = ConfigManager.get_profile(profile_id)
    
    if not profile:
        profiles = ConfigManager.get_profiles()
        # Find active profile with auto_backup_enabled == True, or first profile
        profile = next((p for p in profiles if p.get("auto_backup_enabled")), (profiles[0] if profiles else None))

    if not profile:
        print("[ERROR] 백업할 프로필을 찾을 수 없습니다.")
        sys.exit(1)

    prof_id = profile.get("id", "prof_custom_selected")
    profile_name = profile.get("name", "자동 스케줄 백업")
    repo_dir = profile.get("repo_dir") or os.path.join(BASE_DIR, "backup_repository")
    sources = profile.get("sources") or [BASE_DIR]
    excludes = profile.get("exclude_patterns") or []
    compress = profile.get("compression_level", 6)
    retention_count = profile.get("retention_count", 30)
    retention_days = profile.get("retention_days", 60)

    print(f" -> 프로필: {profile_name} ({prof_id})")
    print(f" -> 대상 경로 수: {len(sources)}개")
    print(f" -> 백업 저장소: {repo_dir}")

    # 2. Run backup
    t0 = time.time()
    try:
        manifest = SnapshotEngine.create_snapshot(
            repo_dir=repo_dir,
            sources=sources,
            profile_id=prof_id,
            profile_name=profile_name,
            exclude_patterns=excludes,
            compress_level=compress
        )
        t1 = time.time()

        # 3. Prune old snapshots
        pruned = SnapshotEngine.prune_snapshots(repo_dir, retention_count, retention_days, authorized=True)

        # 4. Update profile last run time
        profile["last_run"] = time.time()
        profile["last_status"] = "success"
        profile["last_snapshot_id"] = manifest["id"]
        ConfigManager.save_profile(profile)

        # 5. Send KakaoTalk / Push Notification
        try:
            from core.notifier import notify_backup_result
            notify_backup_result(manifest=manifest, profile_name=profile_name)
        except Exception as e_notif:
            print(f"[WARNING] 알림 전송 실패: {e_notif}")

        # 6. Firebase Cloud Sync
        try:
            from core.firebase_sync import upload_backup_status
            upload_backup_status(manifest_summary=manifest, status="success", repo_dir=repo_dir)
            print("[Firebase] 클라우드(sunhang-772e5) 실시간 동기화 완료")
        except Exception as e_fb:
            print(f"[Firebase] 클라우드 동기화 건너뜀: {e_fb}")

        print("=== 백업 프로세스 정상 종료 (메모리 완전 회수) ===")
        sys.exit(0)

    except Exception as e:
        print(f"[ERROR] 백업 실행 실패: {e}")
        profile["last_status"] = "failed"
        ConfigManager.save_profile(profile)
        try:
            from core.notifier import notify_backup_result
            notify_backup_result(error_msg=str(e), profile_name=profile_name)
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="백업 매니저 원샷 CLI 실행기")
    parser.add_argument("--profile", "-p", help="실행할 프로필 ID", default=None)
    args = parser.parse_args()
    run_cli_backup(args.profile)
