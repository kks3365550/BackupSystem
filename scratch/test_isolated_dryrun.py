# -*- coding: utf-8 -*-
"""
scratch/test_isolated_dryrun.py
Sprint 2: 완전 격리 임시 저장소를 통한 Backup -> Restore -> Hash 무결성 Dry-Run 검증
"""

import os
import sys
import shutil
import hashlib
import tempfile
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from core.snapshot import SnapshotEngine
from core.restore import RestoreEngine

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== [Sprint 2: Isolated Dry-Run 시작] ===")
    
    # 1. 완전 격리된 임시 폴더 생성
    temp_base = tempfile.mkdtemp(prefix="bkp_dryrun_")
    src_dir = os.path.join(temp_base, "src")
    repo_dir = os.path.join(temp_base, "repo")
    restore_dir = os.path.join(temp_base, "restore")
    
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(repo_dir, exist_ok=True)
    os.makedirs(restore_dir, exist_ok=True)
    
    print(f"[*] 임시 소스 경로: {src_dir}")
    print(f"[*] 격리 테스트 저장소: {repo_dir}")
    print(f"[*] 복원 대상 경로: {restore_dir}")
    
    try:
        # 2. 테스트 데이터 생성
        test_file = os.path.join(src_dir, "sample_document.txt")
        test_content = b"BackupSystem v2.9.20 Production Ready Verification Test Content 2026-09-30\n" * 100
        with open(test_file, "wb") as f:
            f.write(test_content)
        
        orig_hash = compute_sha256(test_file)
        print(f"[1] 원본 파일 생성 완료 (SHA-256: {orig_hash[:16]}...)")
        
        # 3. 스냅샷 백업 수행
        manifest = SnapshotEngine.create_snapshot(
            repo_dir=repo_dir,
            sources=[src_dir],
            profile_id="prof_dryrun_test",
            profile_name="Dry-Run Test Profile",
            exclude_patterns=["*.tmp"],
            compress_level=3
        )
        snapshot_id = manifest["id"]
        total_files = manifest["summary"]["total_files"]
        is_verified = manifest.get("is_verified", False)
        print(f"[2] 스냅샷 백업 완료 (Snapshot ID: {snapshot_id}, Files: {total_files}, Automated Verified: {is_verified})")
        
        # 4. 복원 수행
        restore_result = RestoreEngine.restore_snapshot(
            repo_dir=repo_dir,
            snapshot_id=snapshot_id,
            target_dir=restore_dir,
            overwrite=True,
            verify_hash=True
        )
        print(f"[3] 복원 완료 (Restored: {restore_result.get('restored_files', 0)} files)")
        
        # 5. 무결성 해시 비교
        restored_file = None
        for root, dirs, files in os.walk(restore_dir):
            if "sample_document.txt" in files:
                restored_file = os.path.join(root, "sample_document.txt")
                break
                
        assert restored_file and os.path.exists(restored_file), f"복원된 파일이 존재하지 않음: {restore_dir}"
        restored_hash = compute_sha256(restored_file)
        print(f"[4] 복원 파일 해시: {restored_hash[:16]}...")
        
        if orig_hash == restored_hash:
            print(">>> [PASS] SHA-256 무결성 100% 일치 확인!")
        else:
            print(f">>> [FAIL] 해시 불일치: {orig_hash} != {restored_hash}")
            sys.exit(1)
            
    finally:
        # 6. 임시 격리 디렉토리 완전 청소
        shutil.rmtree(temp_base, ignore_errors=True)
        print(f"[*] 임시 디렉토리 클린업 완료: {temp_base}")
        print("=== [Sprint 2: Isolated Dry-Run 정상 종료] ===")

if __name__ == "__main__":
    main()
