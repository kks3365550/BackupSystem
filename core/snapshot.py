import os
import time
import json
import uuid
import datetime
from typing import Dict, List, Any, Optional, Callable
from core.hasher import calculate_sha256, get_file_stat
from core.filter import PathFilter
from core.storage import BlobStorage

class SnapshotEngine:
    @staticmethod
    def _generate_snapshot_id() -> str:
        ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_str = uuid.uuid4().hex[:6]
        return f"snap_{ts_str}_{rand_str}"

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
        cancel_event: Optional[Any] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        storage = BlobStorage(repo_dir)
        path_filter = PathFilter(exclude_patterns=exclude_patterns)

        # 1. Build fast incremental diff cache from existing snapshots in the repository
        existing_snapshots = cls.list_snapshots(repo_dir)
        prev_snapshot = None
        for s in existing_snapshots:
            if s.get("profile_id") == profile_id or s.get("profile_name") == profile_name:
                prev_snapshot = cls.get_snapshot(repo_dir, s["id"])
                break
        if not prev_snapshot and existing_snapshots:
            # Fallback to the latest global snapshot in this repository
            prev_snapshot = cls.get_snapshot(repo_dir, existing_snapshots[0]["id"])

        prev_entries_map = {}
        # Load entries from recent snapshots into fast cache
        snapshots_to_cache = [prev_snapshot] if prev_snapshot else []
        for s in existing_snapshots[:5]:
            if s and s.get("id") != (prev_snapshot.get("id") if prev_snapshot else None):
                snap_obj = cls.get_snapshot(repo_dir, s["id"])
                if snap_obj:
                    snapshots_to_cache.append(snap_obj)

        for snap_item in snapshots_to_cache:
            if snap_item and "entries" in snap_item:
                for entry in snap_item["entries"]:
                    s_root = entry.get("source_root", "")
                    r_path = entry.get("rel_path", "")
                    # Full normalized path key
                    full_p = os.path.normpath(os.path.join(s_root, r_path)).replace('\\', '/').lower()
                    if full_p not in prev_entries_map:
                        prev_entries_map[full_p] = entry
                    # Tuple key
                    tuple_key = (s_root, r_path)
                    if tuple_key not in prev_entries_map:
                        prev_entries_map[tuple_key] = entry

        # 2. Prepare for scanning
        all_files_to_process = []
        for src in sources:
            src = os.path.abspath(src)
            if not os.path.exists(src):
                continue

            if os.path.isfile(src):
                if not path_filter.is_excluded(src, is_dir=False):
                    all_files_to_process.append((src, os.path.dirname(src), os.path.basename(src)))
            else:
                for root, dirs, files in os.walk(src):
                    # Filter directories in place to avoid walking into excluded dirs
                    dirs[:] = [d for d in dirs if not path_filter.is_excluded(os.path.join(root, d), is_dir=True)]

                    for file in files:
                        full_path = os.path.join(root, file)
                        if not path_filter.is_excluded(full_path, is_dir=False):
                            rel_path = os.path.relpath(full_path, src).replace('\\', '/')
                            all_files_to_process.append((full_path, src, rel_path))

                    if progress_callback and (len(all_files_to_process) % 100 == 0 or len(all_files_to_process) == 1):
                        progress_callback({
                            "type": "scanning",
                            "current_file": f"파일 목록 탐색 중... ({len(all_files_to_process)}개 발견)",
                            "processed_files": 0,
                            "total_files": len(all_files_to_process),
                            "percent": 0,
                            "new_files": 0,
                            "modified_files": 0,
                            "unmodified_files": 0,
                            "transferred_bytes": 0
                        })

        total_files_count = len(all_files_to_process)
        total_source_bytes = 0
        new_files_count = 0
        modified_files_count = 0
        unmodified_files_count = 0
        new_stored_bytes = 0
        processed_files_count = 0
        entries = []
        seen_keys = set()

        # 3. Process files (Incremental & Deduplication)
        for full_path, src_root, rel_path in all_files_to_process:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Backup operation was cancelled by user.")

            processed_files_count += 1
            stat = get_file_stat(full_path)
            if not stat:
                continue

            f_size = stat['size']
            f_mtime = stat['mtime']
            total_source_bytes += f_size
            key = (src_root, rel_path)
            seen_keys.add(key)

            norm_full_path = os.path.normpath(full_path).replace('\\', '/').lower()
            prev_entry = prev_entries_map.get(norm_full_path) or prev_entries_map.get(key)
            is_unmodified = False

            # Check if file is exactly identical in size and mtime to previous snapshot
            if prev_entry and prev_entry.get("sha256") and prev_entry.get("size") == f_size and abs(prev_entry.get("mtime", 0) - f_mtime) < 0.001:
                # Fast path: Reuse previous sha256 and blob reference without reading file
                sha256_hash = prev_entry.get("sha256")
                blob_id = prev_entry.get("blob_id", sha256_hash)
                # Verify blob exists in storage
                if blob_id and storage.has_blob(blob_id):
                    is_unmodified = True
                    unmodified_files_count += 1
                    entry = {
                        "source_root": src_root,
                        "rel_path": rel_path,
                        "size": f_size,
                        "mtime": f_mtime,
                        "sha256": sha256_hash,
                        "blob_id": blob_id,
                        "status": "unmodified"
                    }
                    entries.append(entry)

            if not is_unmodified:
                # File is new or modified: compute SHA-256 and store blob
                try:
                    sha256_hash = calculate_sha256(full_path)
                    _, orig_size, stored_size, is_new_blob = storage.put_file_blob(
                        full_path,
                        sha256_hash=sha256_hash,
                        compress_level=compress_level
                    )
                    if is_new_blob:
                        new_stored_bytes += stored_size

                    status = "modified" if prev_entry else "new"
                    if status == "modified":
                        modified_files_count += 1
                    else:
                        new_files_count += 1

                    entry = {
                        "source_root": src_root,
                        "rel_path": rel_path,
                        "size": f_size,
                        "mtime": f_mtime,
                        "sha256": sha256_hash,
                        "blob_id": sha256_hash,
                        "status": status
                    }
                    entries.append(entry)
                except (PermissionError, OSError) as e:
                    # Locked or inaccessible file: log and continue
                    entry = {
                        "source_root": src_root,
                        "rel_path": rel_path,
                        "size": f_size,
                        "mtime": f_mtime,
                        "error": str(e),
                        "status": "error"
                    }
                    entries.append(entry)

            # Progress callback notification
            if progress_callback and (processed_files_count % 10 == 0 or processed_files_count == total_files_count):
                percent = round((processed_files_count / max(1, total_files_count)) * 100, 1)
                progress_callback({
                    "type": "progress",
                    "current_file": rel_path,
                    "processed_files": processed_files_count,
                    "total_files": total_files_count,
                    "percent": percent,
                    "new_files": new_files_count,
                    "modified_files": modified_files_count,
                    "unmodified_files": unmodified_files_count,
                    "transferred_bytes": new_stored_bytes
                })

        # Calculate deleted files count compared to previous snapshot
        deleted_files_count = 0
        if prev_snapshot and "entries" in prev_snapshot:
            for k in prev_entries_map.keys():
                if k not in seen_keys:
                    deleted_files_count += 1

        duration = time.time() - start_time
        snapshot_id = cls._generate_snapshot_id()
        backup_type = "incremental" if prev_snapshot else "full"

        dedup_saved_bytes = max(0, total_source_bytes - new_stored_bytes)

        snapshot_manifest = {
            "id": snapshot_id,
            "created_at": time.time(),
            "iso_time": datetime.datetime.now().isoformat(),
            "profile_id": profile_id,
            "profile_name": profile_name,
            "backup_type": backup_type,
            "base_snapshot_id": prev_snapshot["id"] if prev_snapshot else None,
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

        # 4. Save snapshot manifest
        snapshot_file = os.path.join(storage.snapshots_dir, f"{snapshot_id}.json")
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot_manifest, f, indent=2)

        return snapshot_manifest

    @classmethod
    def list_snapshots(cls, repo_dir: str) -> List[Dict[str, Any]]:
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
                        # Return metadata summary for fast listing (omit large entries array)
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

        # Sort by creation time descending (newest first)
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
    def delete_snapshot(cls, repo_dir: str, snapshot_id: str, prune_orphaned_blobs: bool = True) -> bool:
        storage = BlobStorage(repo_dir)
        snap_path = os.path.join(storage.snapshots_dir, f"{snapshot_id}.json")
        if not os.path.exists(snap_path):
            return False

        deleted = False
        import stat as stat_mod
        for attempt in range(4):
            try:
                if os.path.exists(snap_path):
                    try:
                        os.chmod(snap_path, stat_mod.S_IWRITE)
                    except Exception:
                        pass
                    os.remove(snap_path)
                    deleted = True
                    break
            except Exception:
                time.sleep(0.2)

        if deleted and prune_orphaned_blobs:
            try:
                cls.prune_storage(repo_dir)
            except Exception:
                pass
        return deleted

    @classmethod
    def prune_snapshots(cls, repo_dir: str, retention_count: Optional[int] = None, max_age_days: Optional[int] = None) -> List[str]:
        """Prunes old snapshots based on retention policy and deletes unreferenced blobs."""
        try:
            snapshots = cls.list_snapshots(repo_dir)
        except Exception:
            return []

        deleted_ids = []

        if retention_count and len(snapshots) > retention_count:
            # list is sorted newest first, so anything beyond retention_count should be removed
            to_delete = snapshots[retention_count:]
            for s in to_delete:
                try:
                    if cls.delete_snapshot(repo_dir, s["id"], prune_orphaned_blobs=False):
                        deleted_ids.append(s["id"])
                except Exception:
                    pass

        if max_age_days:
            cutoff_ts = time.time() - (max_age_days * 86400)
            try:
                remaining_snapshots = cls.list_snapshots(repo_dir)
                for s in remaining_snapshots:
                    if s.get("created_at", 0) < cutoff_ts:
                        try:
                            if cls.delete_snapshot(repo_dir, s["id"], prune_orphaned_blobs=False):
                                deleted_ids.append(s["id"])
                        except Exception:
                            pass
            except Exception:
                pass

        if deleted_ids:
            try:
                cls.prune_storage(repo_dir)
            except Exception:
                pass

        return deleted_ids

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

        for entry in snapshot_data.get("entries", []):
            rel_path = entry.get("rel_path", "")
            parts = rel_path.split('/')
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
                    "children": children_list
                }
            return node

        return dict_to_list(root)
