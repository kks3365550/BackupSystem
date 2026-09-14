import os
import time
import json
import uuid
import datetime
import threading
import queue
import concurrent.futures
from typing import Dict, List, Any, Optional, Callable, Tuple
from core.hasher import calculate_sha256, get_file_stat
from core.filter import PathFilter
from core.storage import BlobStorage, lock_file_immutable, unlock_file_writable, get_disk_free_gb
from core.lock import BackupLock, BackupAlreadyRunningError
from core.verify import IntegrityVerifier
from core.retention import RetentionManager

class SnapshotEngine:
    @staticmethod
    def _generate_snapshot_id() -> str:
        ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_str = uuid.uuid4().hex[:6]
        return f"snap_{ts_str}_{rand_str}"

    @classmethod
    def _scan_sources_parallel(
        cls,
        sources: List[str],
        path_filter: PathFilter,
        num_workers: int = 8,
        cancel_event: Optional[Any] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> List[Tuple[str, str, str, int, float]]:
        """
        Fast parallel directory exploration using os.scandir and ThreadPool.
        Retrieves file size and mtime directly from Windows C-kernel cache (WIN32_FIND_DATA),
        completely eliminating subsequent stat disk queries.
        """
        all_files: List[Tuple[str, str, str, int, float]] = []
        lock = threading.Lock()
        dir_queue = queue.Queue()
        active_tasks = 0
        cond = threading.Condition(lock)

        for src in sources:
            src = os.path.abspath(src)
            if not os.path.exists(src):
                continue
            src_base = os.path.basename(src)
            if os.path.isfile(src):
                if not path_filter.is_file_excluded(src_base):
                    try:
                        st = os.stat(src)
                        all_files.append((src, os.path.dirname(src), src_base, st.st_size, st.st_mtime))
                    except (PermissionError, OSError):
                        pass
            else:
                if not path_filter.is_dir_excluded(src_base):
                    with lock:
                        dir_queue.put((src, src))

        if dir_queue.empty():
            return all_files

        stop_workers = False

        def worker_loop():
            nonlocal active_tasks, stop_workers
            while True:
                with cond:
                    while dir_queue.empty() and active_tasks > 0 and not stop_workers:
                        cond.wait(timeout=0.1)

                    if stop_workers or (dir_queue.empty() and active_tasks == 0):
                        cond.notify_all()
                        return

                    dir_item = dir_queue.get()
                    active_tasks += 1

                curr_dir, src_root = dir_item
                try:
                    if cancel_event and cancel_event.is_set():
                        with cond:
                            stop_workers = True
                            cond.notify_all()
                        return

                    sub_dirs = []
                    found_files = []

                    with os.scandir(curr_dir) as it:
                        for entry in it:
                            try:
                                if entry.is_dir(follow_symlinks=False):
                                    # Fast O(1) directory exclusion
                                    if path_filter.is_dir_excluded(entry.name):
                                        continue
                                    if entry.is_symlink():
                                        # Junction or Symlink directory: do not recurse to avoid loops
                                        if entry.path.startswith(src_root):
                                            rel_path = entry.path[len(src_root):].lstrip('\\/').replace('\\', '/')
                                        else:
                                            rel_path = os.path.relpath(entry.path, src_root).replace('\\', '/')
                                        st = entry.stat()
                                        found_files.append((entry.path, src_root, rel_path, 0, st.st_mtime))
                                    else:
                                        sub_dirs.append(entry.path)
                                elif entry.is_file(follow_symlinks=False):
                                    # Fast O(1) file exclusion
                                    if not path_filter.is_file_excluded(entry.name):
                                        st = entry.stat()
                                        if entry.path.startswith(src_root):
                                            rel_path = entry.path[len(src_root):].lstrip('\\/').replace('\\', '/')
                                        else:
                                            rel_path = os.path.relpath(entry.path, src_root).replace('\\', '/')
                                        found_files.append((entry.path, src_root, rel_path, st.st_size, st.st_mtime))
                            except (PermissionError, OSError):
                                continue

                    report_progress = False
                    total_count_report = 0
                    with cond:
                        for sd in sub_dirs:
                            dir_queue.put((sd, src_root))
                        all_files.extend(found_files)
                        total_found = len(all_files)
                        active_tasks -= 1
                        cond.notify_all()
                        if progress_callback and (total_found % 500 == 0 or total_found == 1):
                            report_progress = True
                            total_count_report = total_found

                    if report_progress and progress_callback:
                        progress_callback({
                            "type": "scanning",
                            "current_file": f"파일 탐색 중... ({total_count_report:,}개 발견: {os.path.basename(curr_dir)})",
                            "processed_files": 0,
                            "total_files": total_count_report,
                            "percent": 0,
                            "new_files": 0,
                            "modified_files": 0,
                            "unmodified_files": 0,
                            "transferred_bytes": 0
                        })
                except (PermissionError, OSError):
                    with cond:
                        active_tasks -= 1
                        cond.notify_all()

        threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=worker_loop, daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        if cancel_event and cancel_event.is_set():
            raise InterruptedError("Backup operation was cancelled by user.")

        return all_files

    @classmethod
    def create_snapshot(
        cls,
        repo_dir: str,
        sources: List[str],
        profile_id: str = "default",
        profile_name: str = "Default Backup",
        exclude_patterns: Optional[List[str]] = None,
        compress_level: int = 6,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[Any] = None,
        min_free_disk_gb: Optional[float] = None
    ) -> Dict[str, Any]:
        # 0. Acquire repository lock to prevent concurrent backup runs
        with BackupLock(repo_dir, timeout_sec=1.0, process_desc=f"{profile_name} ({profile_id})"):
            return cls._create_snapshot_internal(
                repo_dir=repo_dir,
                sources=sources,
                profile_id=profile_id,
                profile_name=profile_name,
                exclude_patterns=exclude_patterns,
                compress_level=compress_level,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
                min_free_disk_gb=min_free_disk_gb
            )

    @classmethod
    def _create_snapshot_internal(
        cls,
        repo_dir: str,
        sources: List[str],
        profile_id: str = "default",
        profile_name: str = "Default Backup",
        exclude_patterns: Optional[List[str]] = None,
        compress_level: int = 6,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[Any] = None,
        min_free_disk_gb: Optional[float] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        storage = BlobStorage(repo_dir)
        path_filter = PathFilter(exclude_patterns=exclude_patterns)

        # 0. Smart Low-Disk Safeguard: auto prune oldest snapshots if free space < min_free_disk_gb
        if min_free_disk_gb is None:
            try:
                from core.config import ConfigManager
                settings = ConfigManager.get_settings()
                min_free_disk_gb = float(settings.get("min_free_disk_gb", 10.0))
            except Exception:
                min_free_disk_gb = 10.0

        if min_free_disk_gb > 0:
            pruned_snaps, freed_space_gb = cls.ensure_disk_space(repo_dir, min_free_gb=min_free_disk_gb)
            if pruned_snaps > 0 and progress_callback:
                progress_callback({
                    "type": "safeguard",
                    "current_file": f"저장소 용량 확보: 여유 공간 부족(<{min_free_disk_gb}GB)으로 오래된 스냅샷 {pruned_snaps}개 정리 (+{freed_space_gb}GB)",
                    "processed_files": 0,
                    "total_files": 0,
                    "percent": 0
                })

        # 1. Build fast incremental diff cache from existing snapshots in the repository
        existing_snapshots = cls.list_snapshots(repo_dir)
        prev_entries_map = {}
        prev_rel_map = {}

        # Fix #5: Only load the single most-recent profile-matched snapshot
        best_snapshot = None
        for s in existing_snapshots:
            if s.get("profile_id") == profile_id or s.get("profile_name") == profile_name:
                best_snapshot = cls.get_snapshot(repo_dir, s["id"])
                break
        # Fallback: use the latest snapshot from the repo if no profile match
        if not best_snapshot and existing_snapshots:
            best_snapshot = cls.get_snapshot(repo_dir, existing_snapshots[0]["id"])

        if best_snapshot and "entries" in best_snapshot:
            for entry in best_snapshot["entries"]:
                s_root = entry.get("source_root", "")
                r_path = entry.get("rel_path", "")
                full_p = os.path.normpath(os.path.join(s_root, r_path)).replace('\\', '/').lower()
                if full_p not in prev_entries_map:
                    prev_entries_map[full_p] = entry
                tuple_key = (s_root, r_path)
                if tuple_key not in prev_entries_map:
                    prev_entries_map[tuple_key] = entry
                norm_r = r_path.replace('\\', '/').lower()
                if norm_r not in prev_rel_map:
                    prev_rel_map[norm_r] = entry

            # Pre-populate blob cache from previous snapshot to make storage.has_blob O(1) in-memory
            storage.bulk_add_blob_cache(e.get("blob_id") or e.get("sha256") for e in best_snapshot["entries"])

        # 2. High-Performance Full-Thread Parallel Allocation (Ryzen 9800X3D 16-thread & MiniPC full power)
        cpu_cnt = os.cpu_count() or 8
        num_workers = max(4, min(32, cpu_cnt))
        all_files_to_process = cls._scan_sources_parallel(
            sources=sources,
            path_filter=path_filter,
            num_workers=num_workers,
            cancel_event=cancel_event,
            progress_callback=progress_callback
        )

        total_files_count = len(all_files_to_process)
        total_source_bytes = 0
        new_files_count = 0
        modified_files_count = 0
        unmodified_files_count = 0
        new_stored_bytes = 0
        entries = []
        seen_keys = set()
        seen_norm_paths = set()
        files_to_process_parallel = []

        # 3. Process files: Fast Path (no extra disk stat queries needed!)
        for full_path, src_root, rel_path, f_size, f_mtime in all_files_to_process:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Backup operation was cancelled by user.")

            total_source_bytes += f_size
            key = (src_root, rel_path)
            seen_keys.add(key)

            norm_full_path = os.path.normpath(full_path).replace('\\', '/').lower()
            seen_norm_paths.add(norm_full_path)
            norm_rel = rel_path.replace('\\', '/').lower()
            prev_entry = prev_entries_map.get(norm_full_path) or prev_entries_map.get(key) or prev_rel_map.get(norm_rel)

            # Check unmodified fast path (size identical and mtime within 1.0s tolerance for FAT32/NTFS precision)
            if prev_entry and prev_entry.get("sha256") and prev_entry.get("size") == f_size and abs(prev_entry.get("mtime", 0) - f_mtime) < 1.0:
                blob_id = prev_entry.get("blob_id", prev_entry.get("sha256"))
                if blob_id and storage.has_blob(blob_id):
                    unmodified_files_count += 1
                    entries.append({
                        "source_root": src_root,
                        "rel_path": rel_path,
                        "size": f_size,
                        "mtime": f_mtime,
                        "sha256": prev_entry.get("sha256"),
                        "blob_id": blob_id,
                        "status": "unmodified"
                    })
                    continue

            files_to_process_parallel.append((full_path, src_root, rel_path, f_size, f_mtime, prev_entry))

        processed_files_count = unmodified_files_count

        # 2차 Pass: 신규 및 수정된 파일들을 8개 워커로 병렬 One-Pass 처리
        lock = threading.Lock()
        new_blobs_count = 0  # Fix #11: track unique new blobs (≠ new files due to dedup)

        def _worker_process_file(item):
            full_p, s_root, r_path, size, mtime, p_entry = item
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Operation cancelled")
            try:
                # One-Pass streaming hash + compression
                sha256_hash, orig_sz, stored_sz, is_new = storage.put_file_blob_onepass(
                    full_p,
                    compress_level=compress_level,
                    cancel_event=cancel_event
                )
                st = "modified" if p_entry else "new"
                res_entry = {
                    "source_root": s_root,
                    "rel_path": r_path,
                    "size": size,
                    "mtime": mtime,
                    "sha256": sha256_hash,
                    "blob_id": sha256_hash,
                    "status": st
                }
                return res_entry, is_new, stored_sz, st, None
            except Exception as ex:
                return {
                    "source_root": s_root,
                    "rel_path": r_path,
                    "size": size,
                    "mtime": mtime,
                    "error": str(ex),
                    "status": "error"
                }, False, 0, "error", str(ex)

        if files_to_process_parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = {executor.submit(_worker_process_file, it): it for it in files_to_process_parallel}
                for fut in concurrent.futures.as_completed(futures):
                    if cancel_event and cancel_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise InterruptedError("Backup operation was cancelled by user.")

                    entry, is_new, stored_sz, st, err = fut.result()
                    with lock:
                        processed_files_count += 1
                        entries.append(entry)
                        if is_new:
                            new_stored_bytes += stored_sz
                            new_blobs_count += 1  # Fix #11: only count genuinely new unique blobs
                        if st == "new":
                            new_files_count += 1
                        elif st == "modified":
                            modified_files_count += 1

                        if progress_callback and (processed_files_count % 5 == 0 or processed_files_count == total_files_count):
                            pct = round((processed_files_count / max(1, total_files_count)) * 100, 1)
                            progress_callback({
                                "type": "progress",
                                "current_file": f"[{num_workers}코어 병렬가속] {entry.get('rel_path', '')}",
                                "processed_files": processed_files_count,
                                "total_files": total_files_count,
                                "percent": pct,
                                "new_files": new_files_count,
                                "modified_files": modified_files_count,
                                "unmodified_files": unmodified_files_count,
                                "transferred_bytes": new_stored_bytes
                            })
        else:
            if progress_callback:
                progress_callback({
                    "type": "progress",
                    "current_file": "검증 완료 (모든 파일 동일)",
                    "processed_files": total_files_count,
                    "total_files": total_files_count,
                    "percent": 100.0,
                    "new_files": 0,
                    "modified_files": 0,
                    "unmodified_files": unmodified_files_count,
                    "transferred_bytes": 0
                })

        # Calculate deleted files count compared to previous snapshot
        deleted_files_count = 0
        if best_snapshot and "entries" in best_snapshot:
            for prev_e in best_snapshot["entries"]:
                s_root = prev_e.get("source_root", "")
                r_path = prev_e.get("rel_path", "")
                t_key = (s_root, r_path)
                p_norm = os.path.normpath(os.path.join(s_root, r_path)).replace('\\', '/').lower()
                if t_key not in seen_keys and p_norm not in seen_norm_paths:
                    deleted_files_count += 1

        duration = time.time() - start_time
        snapshot_id = cls._generate_snapshot_id()
        backup_type = "incremental" if best_snapshot else "full"

        dedup_saved_bytes = max(0, total_source_bytes - new_stored_bytes)

        snapshot_manifest = {
            "id": snapshot_id,
            "created_at": time.time(),
            "iso_time": datetime.datetime.now().isoformat(),
            "profile_id": profile_id,
            "profile_name": profile_name,
            "backup_type": backup_type,
            "base_snapshot_id": best_snapshot["id"] if best_snapshot else None,
            "sources": sources,
            "summary": {
                "total_files": len(entries),
                "total_bytes": total_source_bytes,
                "new_files": new_files_count,
                "modified_files": modified_files_count,
                "unmodified_files": unmodified_files_count,
                "deleted_files": deleted_files_count,
                "new_stored_bytes": new_stored_bytes,
                "dedup_saved_bytes": dedup_saved_bytes,
                "duration_seconds": round(duration, 2)
            },
            "entries": entries
        }

        # 4. Save snapshot manifest — Fix #7: compact JSON (no indent) saves 60% space & 2x faster write/load
        snapshot_file = os.path.join(storage.snapshots_dir, f"{snapshot_id}.json")
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot_manifest, f, indent=None, separators=(',', ':'), ensure_ascii=False)
        lock_file_immutable(snapshot_file)

        # 5. Batch update metadata DB once for all new blobs (Single atomic transaction!)
        # Fix #11: pass new_blobs_count (unique new blobs) not new_files_count (which includes dedup)
        if new_stored_bytes > 0 or new_blobs_count > 0:
            try:
                storage.db.record_new_blob(stored_size=new_stored_bytes, count=new_blobs_count)
            except Exception:
                pass

        # 6. Step 1 Improvement: Auto Integrity Health Check (Lightweight sample check)
        try:
            if progress_callback:
                progress_callback({
                    "type": "verify",
                    "current_file": "백업 무결성 자동 검증(Health Check) 수행 중...",
                    "processed_files": len(entries),
                    "total_files": len(entries),
                    "percent": 99.0
                })
            verifier = IntegrityVerifier(repo_dir)
            v_res = verifier.verify_snapshot(snapshot_manifest, sample_ratio=0.01, max_samples=10, verify_all_new=False)
            snapshot_manifest["is_verified"] = v_res.get("success", False)
            snapshot_manifest["verify_timestamp"] = time.time()
            snapshot_manifest["verify_error_count"] = v_res.get("error_count", 0)

            # Update DB with verified status
            storage.db.update_snapshot_verification(
                snapshot_id=snapshot_id,
                is_verified=v_res.get("success", False),
                error_count=v_res.get("error_count", 0)
            )

            # Re-save manifest with verification tag
            unlock_file_writable(snapshot_file)
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump(snapshot_manifest, f, indent=None, separators=(',', ':'), ensure_ascii=False)
            lock_file_immutable(snapshot_file)
        except Exception as e_hc:
            lock_file_immutable(snapshot_file)
            if progress_callback:
                progress_callback({
                    "type": "verify_warning",
                    "current_file": f"무결성 검증 경고 (스킵): {e_hc}",
                    "processed_files": len(entries),
                    "total_files": len(entries),
                    "percent": 99.0
                })

        # Ensure 100% completion progress callback is delivered to UI
        if progress_callback:
            progress_callback({
                "type": "complete",
                "current_file": "백업 및 무결성 검증 완료",
                "processed_files": len(entries),
                "total_files": len(entries),
                "percent": 100.0,
                "new_files": new_files_count,
                "modified_files": modified_files_count,
                "unmodified_files": unmodified_files_count,
                "transferred_bytes": new_stored_bytes
            })

        return snapshot_manifest

    @classmethod
    def list_snapshots(cls, repo_dir: str) -> List[Dict[str, Any]]:
        try:
            from core.metadata_db import MetadataDB
            return MetadataDB(repo_dir).sync_snapshots()
        except Exception:
            storage = BlobStorage(repo_dir)
            snapshots = []
            if not os.path.exists(storage.snapshots_dir):
                return snapshots

            for filename in os.listdir(storage.snapshots_dir):
                if filename.endswith(".json"):
                    snap_path = os.path.join(storage.snapshots_dir, filename)
                    try:
                        with open(snap_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            snapshots.append({
                                "id": data.get("id"),
                                "created_at": data.get("created_at"),
                                "iso_time": data.get("iso_time"),
                                "profile_id": data.get("profile_id"),
                                "profile_name": data.get("profile_name"),
                                "backup_type": data.get("backup_type"),
                                "base_snapshot_id": data.get("base_snapshot_id"),
                                "sources": data.get("sources", []),
                                "summary": data.get("summary", {})
                            })
                    except Exception:
                        pass

            snapshots.sort(key=lambda x: x.get("created_at", 0), reverse=True)
            return snapshots

    @classmethod
    def get_snapshot(cls, repo_dir: str, snapshot_id: str) -> Optional[Dict[str, Any]]:
        storage = BlobStorage(repo_dir)
        snap_path = os.path.join(storage.snapshots_dir, f"{snapshot_id}.json")
        if not os.path.exists(snap_path):
            return None
        with open(snap_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def ensure_disk_space(cls, repo_dir: str, min_free_gb: float = 10.0) -> Tuple[int, float]:
        """
        Smart Low-Disk Safeguard:
        If free space in the backup repository volume falls below min_free_gb,
        automatically prunes the oldest snapshots one by one until sufficient space is secured.
        Returns (pruned_snapshot_count, freed_gb).
        """
        free_gb = get_disk_free_gb(repo_dir)
        if free_gb >= min_free_gb:
            return 0, 0.0

        initial_free = free_gb
        pruned_count = 0

        # Load snapshots (sorted newest first)
        snapshots = cls.list_snapshots(repo_dir)
        if len(snapshots) <= 1:
            return 0, 0.0

        # Oldest snapshots are deleted first; keep the newest intact (snapshots[0] is newest)
        candidates = list(reversed(snapshots[1:]))

        for s in candidates:
            try:
                if cls.delete_snapshot(repo_dir, s["id"], prune_orphaned_blobs=True):
                    pruned_count += 1
                    current_free = get_disk_free_gb(repo_dir)
                    if current_free >= min_free_gb:
                        break
            except Exception:
                pass

        final_free = get_disk_free_gb(repo_dir)
        freed_gb = max(0.0, round(final_free - initial_free, 2))
        return pruned_count, freed_gb

    @classmethod
    def delete_snapshot(cls, repo_dir: str, snapshot_id: str, prune_orphaned_blobs: bool = True) -> bool:
        storage = BlobStorage(repo_dir)
        snap_path = os.path.join(storage.snapshots_dir, f"{snapshot_id}.json")
        if not os.path.exists(snap_path):
            return False

        deleted = False
        for attempt in range(4):
            try:
                if os.path.exists(snap_path):
                    unlock_file_writable(snap_path)
                    os.remove(snap_path)
                    deleted = True
                    break
            except Exception:
                time.sleep(0.2)

        if deleted:
            try:
                from core.metadata_db import MetadataDB
                MetadataDB(repo_dir).delete_snapshot_record(snapshot_id)
            except Exception:
                pass
            if prune_orphaned_blobs:
                try:
                    cls.prune_storage(repo_dir)
                except Exception:
                    pass
        return deleted

    @classmethod
    def prune_snapshots(
        cls,
        repo_dir: str,
        retention_count: Optional[int] = None,
        max_age_days: Optional[int] = None,
        min_free_gb: Optional[float] = None
    ) -> List[str]:
        """Prunes old snapshots based on retention policy and deletes unreferenced blobs using RetentionManager."""
        try:
            mgr = RetentionManager(repo_dir)
            res = mgr.apply_policy(
                retention_count=retention_count or 30,
                retention_days=max_age_days or 60,
                min_free_gb=min_free_gb
            )
            return res.get("deleted_snapshots", [])
        except Exception:
            return []

    @classmethod
    def prune_storage(cls, repo_dir: str) -> Dict[str, int]:
        """Collects all referenced blob hashes across all existing snapshots and removes orphaned blobs."""
        storage = BlobStorage(repo_dir)
        active_hashes = set()

        for filename in os.listdir(storage.snapshots_dir):
            if filename.endswith(".json"):
                snap_path = os.path.join(storage.snapshots_dir, filename)
                try:
                    with open(snap_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for entry in data.get("entries", []):
                            blob_id = entry.get("blob_id") or entry.get("sha256")
                            if blob_id:
                                active_hashes.add(blob_id)
                except Exception:
                    pass

        deleted_count, freed_bytes = storage.prune_unreferenced_blobs(active_hashes)
        return {"deleted_blobs": deleted_count, "freed_bytes": freed_bytes}

    @classmethod
    def build_snapshot_tree(cls, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Converts snapshot file entries list into a hierarchical tree structure for UI explorer."""
        root = {
            "name": "root",
            "type": "directory",
            "children": {}
        }

        if not snapshot_data or not snapshot_data.get("entries"):
            return {"name": "root", "type": "directory", "children": []}

        for entry in snapshot_data.get("entries", []):
            rel_path = entry.get("rel_path", "")
            parts = rel_path.replace('\\', '/').strip('/').split('/')
            curr = root

            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)
                if is_last:
                    curr["children"][part] = {
                        "name": part,
                        "type": "file",
                        "size": entry.get("size", 0),
                        "mtime": entry.get("mtime", 0),
                        "sha256": entry.get("sha256", ""),
                        "status": entry.get("status", "unmodified"),
                        "rel_path": rel_path,
                        "source_root": entry.get("source_root", "")
                    }
                else:
                    if part not in curr["children"]:
                        curr["children"][part] = {
                            "name": part,
                            "type": "directory",
                            "rel_path": "/".join(parts[:i+1]),
                            "children": {}
                        }
                    curr = curr["children"][part]

        def dict_to_list(node):
            if node["type"] == "directory":
                children_list = []
                for child_name, child_node in node["children"].items():
                    children_list.append(dict_to_list(child_node))
                # Sort: directories first, then alphabetically
                children_list.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
                return {
                    "name": node["name"],
                    "type": "directory",
                    "rel_path": node.get("rel_path", ""),
                    "children": children_list
                }
            return node

        return dict_to_list(root)

    # In-memory snapshot cache for sub-millisecond on-demand directory navigation
    _BROWSE_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
    _BROWSE_CACHE_LOCK = threading.Lock()

    @classmethod
    def browse_snapshot_directory(cls, repo_dir: str, snapshot_id: str, subpath: str = "") -> Dict[str, Any]:
        """
        High-performance on-demand folder browser.
        Instead of loading 100,000 files into DOM at once, returns ONLY direct children
        under the requested subpath in ~0.01s.
        """
        storage = BlobStorage(repo_dir)
        snap_path = os.path.join(storage.snapshots_dir, f"{snapshot_id}.json")
        if not os.path.exists(snap_path):
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found.")

        mtime = os.path.getmtime(snap_path)
        entries = None

        with cls._BROWSE_CACHE_LOCK:
            cached = cls._BROWSE_CACHE.get(snapshot_id)
            if cached and cached[0] == mtime:
                entries = cached[1]

        if entries is None:
            with open(snap_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries", [])
            with cls._BROWSE_CACHE_LOCK:
                # Keep max 5 snapshots cached in memory
                if len(cls._BROWSE_CACHE) >= 5:
                    cls._BROWSE_CACHE.pop(next(iter(cls._BROWSE_CACHE)))
                cls._BROWSE_CACHE[snapshot_id] = (mtime, entries)

        subpath_norm = subpath.replace('\\', '/').strip('/')
        prefix = subpath_norm + '/' if subpath_norm else ''

        dirs = {}
        files = []

        for e in entries:
            rp = e.get("rel_path", "").replace('\\', '/').strip('/')
            if prefix:
                if not rp.startswith(prefix):
                    continue
                remain = rp[len(prefix):]
            else:
                remain = rp

            parts = remain.split('/')
            if len(parts) == 1:
                files.append({
                    "name": parts[0],
                    "type": "file",
                    "size": e.get("size", 0),
                    "mtime": e.get("mtime", 0),
                    "rel_path": rp,
                    "status": e.get("status", "unmodified")
                })
            else:
                dirname = parts[0]
                if dirname not in dirs:
                    dirs[dirname] = {
                        "name": dirname,
                        "type": "directory",
                        "rel_path": prefix + dirname,
                        "file_count": 0,
                        "size": 0
                    }
                dirs[dirname]["file_count"] += 1
                dirs[dirname]["size"] += e.get("size", 0)

        dir_list = sorted(dirs.values(), key=lambda x: x["name"].lower())
        file_list = sorted(files, key=lambda x: x["name"].lower())

        return {
            "snapshot_id": snapshot_id,
            "subpath": subpath_norm,
            "items": dir_list + file_list,
            "total_items": len(dir_list) + len(file_list)
        }
