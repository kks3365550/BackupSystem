# -*- coding: utf-8 -*-
"""
core/replication.py - P1-1 Offsite CAS Blob Replication Module (v2.4.0)
- CAS(Content-Addressable Storage) 블롭 증분 복제 엔진
- 로컬 저장소에서 오프사이트 원격지(네트워크 드라이브/원격 복제소)로 블롭 및 매니페스트 동기화
- 원격지에 이미 존재하는 블롭은 전송을 100% 스킵(Zero-Copy Diff)
- 원자적 복사(Atomic File Replacement) 및 원격지 WORM(ReadOnly) 속성 부여
"""

import os
import json
import time
import shutil
import threading
from typing import Set, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.storage import (
    lock_file_immutable,
    unlock_file_writable,
    get_disk_free_gb,
    verify_disk_space_or_fail,
    InsufficientDiskSpaceError,
    DEFAULT_CHUNK_SIZE
)


class ReplicationManager:
    """
    로컬 CAS 저장소의 블롭과 스냅샷을 오프사이트 원격 저장소로 증분 복제하는 관리자.
    """

    MIN_REMOTE_FREE_GB = 5.0

    def __init__(self, local_repo_dir: str, remote_repo_dir: str):
        self.local_repo_dir = os.path.abspath(local_repo_dir)
        self.remote_repo_dir = os.path.abspath(remote_repo_dir)

        if not os.path.isdir(self.local_repo_dir):
            raise FileNotFoundError(f"Local repository does not exist: {self.local_repo_dir}")

        self.local_blobs_dir = os.path.join(self.local_repo_dir, "blobs")
        self.local_snapshots_dir = os.path.join(self.local_repo_dir, "snapshots")
        self.remote_blobs_dir = os.path.join(self.remote_repo_dir, "blobs")
        self.remote_snapshots_dir = os.path.join(self.remote_repo_dir, "snapshots")

        if not os.path.isdir(self.local_blobs_dir):
            raise FileNotFoundError(f"Local blobs directory missing: {self.local_blobs_dir}")
        if not os.path.isdir(self.local_snapshots_dir):
            raise FileNotFoundError(f"Local snapshots directory missing: {self.local_snapshots_dir}")

        self._ensure_remote_structure()
        self._lock = threading.Lock()

    def _ensure_remote_structure(self):
        """원격지에 필요한 디렉토리 구조 및 256개 접두사 디렉토리 생성."""
        os.makedirs(self.remote_blobs_dir, exist_ok=True)
        os.makedirs(self.remote_snapshots_dir, exist_ok=True)
        for i in range(256):
            prefix_dir = os.path.join(self.remote_blobs_dir, f"{i:02x}")
            os.makedirs(prefix_dir, exist_ok=True)

    def _get_blob_rel_path(self, blob_id: str) -> str:
        if not blob_id or len(blob_id) < 2:
            raise ValueError(f"Invalid blob ID: {blob_id!r}")
        prefix = blob_id[:2]
        return os.path.join(prefix, f"{blob_id}.blob")

    def _get_local_blob_path(self, blob_id: str) -> str:
        return os.path.join(self.local_blobs_dir, self._get_blob_rel_path(blob_id))

    def _get_remote_blob_path(self, blob_id: str) -> str:
        return os.path.join(self.remote_blobs_dir, self._get_blob_rel_path(blob_id))

    def get_missing_blobs(self, target_blob_ids: Set[str]) -> List[str]:
        """원격지에 아직 복제되지 않은 블롭 ID 목록 반환."""
        if not target_blob_ids:
            return []

        missing = []
        for blob_id in target_blob_ids:
            remote_path = self._get_remote_blob_path(blob_id)
            if not os.path.exists(remote_path):
                missing.append(blob_id)
        return missing

    def replicate_blob(self, blob_id: str) -> int:
        """단일 블롭을 원격지로 원자적 복사 및 WORM 잠금. 복사된 바이트 수 반환."""
        local_path = self._get_local_blob_path(blob_id)
        remote_path = self._get_remote_blob_path(blob_id)

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local blob not found: {local_path}")

        if os.path.exists(remote_path):
            return 0

        remote_prefix_dir = os.path.dirname(remote_path)
        os.makedirs(remote_prefix_dir, exist_ok=True)

        tmp_path = f"{remote_path}.tmp_{os.getpid()}_{threading.get_ident()}"
        bytes_copied = 0

        try:
            with open(local_path, 'rb') as fin, open(tmp_path, 'wb') as fout:
                while True:
                    chunk = fin.read(DEFAULT_CHUNK_SIZE)
                    if not chunk:
                        break
                    fout.write(chunk)
                    bytes_copied += len(chunk)

            os.replace(tmp_path, remote_path)
            lock_file_immutable(remote_path)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise

        return bytes_copied

    def _load_snapshot_manifest(self, snapshot_id: str) -> Dict[str, Any]:
        manifest_path = os.path.join(self.local_snapshots_dir, f"{snapshot_id}.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Snapshot manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _extract_blob_ids_from_manifest(self, manifest: Dict[str, Any]) -> Set[str]:
        blob_ids = set()

        if "entries" in manifest and isinstance(manifest["entries"], list):
            for entry in manifest["entries"]:
                if isinstance(entry, dict):
                    blob_id = entry.get("blob_id") or entry.get("sha256")
                    if blob_id:
                        blob_ids.add(blob_id)

        if "files" in manifest and isinstance(manifest["files"], list):
            for entry in manifest["files"]:
                if isinstance(entry, dict) and "sha256" in entry:
                    blob_id = entry["sha256"]
                    if blob_id:
                        blob_ids.add(blob_id)

        if "blobs" in manifest and isinstance(manifest["blobs"], list):
            for blob_id in manifest["blobs"]:
                if isinstance(blob_id, str) and blob_id:
                    blob_ids.add(blob_id)

        return blob_ids

    def _copy_snapshot_manifest(self, snapshot_id: str) -> bool:
        """스냅샷 manifest.json을 원격지로 원자적 복사."""
        local_manifest = os.path.join(self.local_snapshots_dir, f"{snapshot_id}.json")
        remote_manifest = os.path.join(self.remote_snapshots_dir, f"{snapshot_id}.json")

        if os.path.exists(remote_manifest):
            local_size = os.path.getsize(local_manifest)
            remote_size = os.path.getsize(remote_manifest)
            if local_size == remote_size:
                return False

        tmp_path = f"{remote_manifest}.tmp_{os.getpid()}_{threading.get_ident()}"
        try:
            with open(local_manifest, 'rb') as fin, open(tmp_path, 'wb') as fout:
                while True:
                    chunk = fin.read(DEFAULT_CHUNK_SIZE)
                    if not chunk:
                        break
                    fout.write(chunk)

            os.replace(tmp_path, remote_manifest)
            lock_file_immutable(remote_manifest)
            return True
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise

    def replicate_snapshot(self, snapshot_id: str, max_workers: int = 4) -> Dict[str, Any]:
        """특정 스냅샷에 필요한 누락된 블롭들만 증분 복제하고 매니페스트 동기화."""
        start_time = time.time()

        verify_disk_space_or_fail(self.remote_repo_dir, min_free_gb=self.MIN_REMOTE_FREE_GB)

        manifest = self._load_snapshot_manifest(snapshot_id)
        required_blobs = self._extract_blob_ids_from_manifest(manifest)

        if not required_blobs:
            duration = time.time() - start_time
            return {
                "snapshot_id": snapshot_id,
                "total_blobs": 0,
                "replicated_blobs": 0,
                "skipped_blobs": 0,
                "transferred_bytes": 0,
                "duration_seconds": round(duration, 3),
                "status": "success"
            }

        missing_blobs = self.get_missing_blobs(required_blobs)
        total_blobs = len(required_blobs)
        replicated_count = 0
        skipped_count = total_blobs - len(missing_blobs)
        total_bytes = 0
        errors = []

        if missing_blobs:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_blob = {
                    executor.submit(self.replicate_blob, b_id): b_id
                    for b_id in missing_blobs
                }

                for future in as_completed(future_to_blob):
                    b_id = future_to_blob[future]
                    try:
                        bytes_copied = future.result()
                        total_bytes += bytes_copied
                        replicated_count += 1
                    except Exception as e:
                        errors.append(f"블롭 {b_id} 복제 실패: {str(e)}")

        try:
            self._copy_snapshot_manifest(snapshot_id)
        except Exception as e:
            errors.append(f"매니페스트 복사 실패: {str(e)}")

        duration = time.time() - start_time
        status = "success" if not errors else "error"

        result = {
            "snapshot_id": snapshot_id,
            "total_blobs": total_blobs,
            "replicated_blobs": replicated_count,
            "skipped_blobs": skipped_count,
            "transferred_bytes": total_bytes,
            "duration_seconds": round(duration, 3),
            "status": status
        }
        if errors:
            result["errors"] = errors

        return result

    def replicate_all_missing(self, max_workers: int = 4) -> Dict[str, Any]:
        """로컬 저장소의 모든 스냅샷과 블롭을 원격지로 증분 동기화."""
        start_time = time.time()
        verify_disk_space_or_fail(self.remote_repo_dir, min_free_gb=self.MIN_REMOTE_FREE_GB)

        snapshot_ids = []
        for fname in os.listdir(self.local_snapshots_dir):
            if fname.endswith(".json"):
                snapshot_ids.append(fname[:-5])

        total_snaps = len(snapshot_ids)
        successful_snaps = 0
        failed_snaps = 0
        total_blobs_replicated = 0
        total_bytes_transferred = 0
        all_errors = []

        for sid in snapshot_ids:
            try:
                res = self.replicate_snapshot(sid, max_workers=max_workers)
                if res.get("status") == "success":
                    successful_snaps += 1
                else:
                    failed_snaps += 1
                    all_errors.extend(res.get("errors", []))
                total_blobs_replicated += res.get("replicated_blobs", 0)
                total_bytes_transferred += res.get("transferred_bytes", 0)
            except Exception as e:
                failed_snaps += 1
                all_errors.append(f"스냅샷 {sid} 복제 중 예외: {str(e)}")

        duration = time.time() - start_time
        status = "success" if failed_snaps == 0 else ("partial_failure" if successful_snaps > 0 else "error")

        return {
            "total_snapshots": total_snaps,
            "successful_snapshots": successful_snaps,
            "failed_snapshots": failed_snaps,
            "total_blobs_replicated": total_blobs_replicated,
            "total_transferred_bytes": total_bytes_transferred,
            "duration_seconds": round(duration, 3),
            "status": status,
            "errors": all_errors
        }
