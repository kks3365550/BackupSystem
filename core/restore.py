import os
import time
import hashlib
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional, Callable
from core.storage import BlobStorage
from core.snapshot import SnapshotEngine

class RestoreEngine:
    @classmethod
    def restore_snapshot(
        cls,
        repo_dir: str,
        snapshot_id: str,
        target_dir: Optional[str] = None,
        selected_rel_paths: Optional[List[str]] = None,
        overwrite: bool = True,
        verify_hash: bool = True,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[Any] = None,
        in_place: bool = False
    ) -> Dict[str, Any]:
        """
        Restores files from a specific snapshot.
        - If in_place=True: restores each file back to its original source_root location (multi-source safe).
        - If in_place=False: restores all files into specified target_dir.
        """
        start_time = time.time()
        storage = BlobStorage(repo_dir)
        snapshot = SnapshotEngine.get_snapshot(repo_dir, snapshot_id)

        if not snapshot:
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found.")

        if not in_place:
            if not target_dir:
                raise ValueError("target_dir is required when in_place=False")
            target_dir = os.path.abspath(target_dir)
            os.makedirs(target_dir, exist_ok=True)
            norm_target = target_dir
            norm_target_prefix = norm_target if norm_target.endswith(os.sep) else norm_target + os.sep
            norm_target_lower = norm_target.lower()
            norm_target_prefix_lower = norm_target_prefix.lower()

        entries = snapshot.get("entries", [])
        to_restore = []

        if selected_rel_paths:
            # Normalize selected paths for case-insensitive matching
            normalized_selected = [p.replace('\\', '/').strip('/').lower() for p in selected_rel_paths]
            for entry in entries:
                rel_p = entry.get("rel_path", "").replace('\\', '/').strip('/')
                rel_p_lower = rel_p.lower()
                for sel in normalized_selected:
                    if rel_p_lower == sel or rel_p_lower.startswith(sel + "/"):
                        to_restore.append(entry)
                        break
        else:
            to_restore = entries

        total_files = len(to_restore)
        restored_files = 0
        skipped_files = 0
        failed_files = []
        restored_bytes = 0
        lock = threading.Lock()

        num_workers = min(12, max(4, os.cpu_count() or 4))
        current_user_profile = os.path.normpath(os.path.expanduser('~'))
        remap_from = ""
        for entry in to_restore:
            src = entry.get("source_root", "")
            if "users" in src.lower():
                parts = src.replace('/', '\\').split('\\')
                try:
                    u_idx = [p.lower() for p in parts].index("users")
                    if u_idx + 1 < len(parts):
                        backup_user = parts[u_idx + 1]
                        drive_prefix = parts[0] if ':' in parts[0] else 'C:'
                        candidate_remap = os.path.normpath(f"{drive_prefix}\\Users\\{backup_user}")
                        if candidate_remap.lower() != current_user_profile.lower():
                            remap_from = candidate_remap
                            break
                except (ValueError, IndexError):
                    continue

        def _restore_one(entry):
            if cancel_event and cancel_event.is_set():
                return "cancelled", 0

            rel_path = entry.get("rel_path")
            blob_id = entry.get("blob_id") or entry.get("sha256")
            f_size = entry.get("size", 0)
            f_mtime = entry.get("mtime")

            if not rel_path or not blob_id:
                return "skip", 0

            if in_place:
                src_root = entry.get("source_root")
                if not src_root:
                    return ("fail", 0, rel_path, "스냅샷에 원본 경로(source_root) 정보가 없습니다.")
                file_target_dir = os.path.abspath(src_root)
                if remap_from:
                    norm_base = os.path.normpath(file_target_dir)
                    if norm_base.lower().startswith(remap_from.lower()):
                        file_target_dir = os.path.normpath(current_user_profile + norm_base[len(remap_from):])
                dest_path = os.path.normpath(os.path.join(file_target_dir, rel_path))
                f_norm_target = file_target_dir
                f_norm_prefix = f_norm_target if f_norm_target.endswith(os.sep) else f_norm_target + os.sep
                dest_lower = dest_path.lower()
                if not (dest_lower == f_norm_target.lower() or dest_lower.startswith(f_norm_prefix.lower())):
                    return ("fail", 0, rel_path, "경로 트래버설 차단: 원본 디렉토리 밖으로 복원 시도")
            else:
                dest_path = os.path.normpath(os.path.join(target_dir, rel_path))
                dest_lower = dest_path.lower()
                # Strict case-insensitive path traversal protection with boundary prefix
                if not (dest_lower == norm_target_lower or dest_lower.startswith(norm_target_prefix_lower)):
                    return ("fail", 0, rel_path, "경로 트래버설 차단: 대상 디렉토리 밖으로 복원 시도")

            if os.path.exists(dest_path) and not overwrite:
                return "skip", 0

            try:
                storage.extract_blob_to_file(blob_id, dest_path, verify_hash=verify_hash)
                # Restore original modified time if present
                if f_mtime:
                    try:
                        os.utime(dest_path, (f_mtime, f_mtime))
                    except OSError:
                        pass

                is_reg = dest_path.lower().endswith(".reg")
                return "ok", f_size, dest_path if is_reg else None
            except Exception as e:
                return ("fail", 0, rel_path, str(e))

        reg_files_to_import = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(_restore_one, entry): entry for entry in to_restore}
            for fut in concurrent.futures.as_completed(futures):
                if cancel_event and cancel_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise InterruptedError("Restore operation was cancelled by user.")

                result = fut.result()
                entry = futures[fut]
                rel_path = entry.get("rel_path", "")

                with lock:
                    if result[0] == "ok":
                        restored_files += 1
                        restored_bytes += result[1]
                        if len(result) > 2 and result[2]:
                            reg_files_to_import.append(result[2])
                    elif result[0] == "skip":
                        skipped_files += 1
                    elif result[0] == "fail":
                        failed_files.append({
                            "rel_path": result[2],
                            "error": result[3]
                        })
                    # cancelled: just skip

                    done = restored_files + skipped_files + len(failed_files)
                    if progress_callback and (done % 5 == 0 or done == total_files):
                        pct = round((done / max(1, total_files)) * 100, 1)
                        progress_callback({
                            "type": "progress",
                            "current_file": rel_path,
                            "restored_files": restored_files,
                            "skipped_files": skipped_files,
                            "failed_files": len(failed_files),
                            "total_files": total_files,
                            "percent": pct,
                            "restored_bytes": restored_bytes
                        })

        # Fix: Safely import registry files sequentially after all files are restored
        if reg_files_to_import:
            try:
                from core.registry_backup import import_registry_file
                for rf in reg_files_to_import:
                    try:
                        import_registry_file(rf)
                    except Exception:
                        pass
            except Exception:
                pass

        duration = time.time() - start_time
        return {
            "snapshot_id": snapshot_id,
            "target_dir": target_dir if not in_place else "ORIGINAL_LOCATION",
            "total_files": total_files,
            "restored_files": restored_files,
            "skipped_files": skipped_files,
            "failed_files": failed_files,
            "restored_bytes": restored_bytes,
            "duration_seconds": round(duration, 2)
        }

    @classmethod
    def verify_snapshot_integrity(
        cls,
        repo_dir: str,
        snapshot_id: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Verifies that all blobs referenced by this snapshot are present and uncorrupted.
        Fix #3: Removed 'if False:' dead code — actual_hash was always None.
        """
        storage = BlobStorage(repo_dir)
        snapshot = SnapshotEngine.get_snapshot(repo_dir, snapshot_id)
        if not snapshot:
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found.")

        entries = snapshot.get("entries", [])
        total_files = len(entries)
        verified_count = 0
        missing_blobs = []
        corrupted_blobs = []

        for i, entry in enumerate(entries):
            blob_id = entry.get("blob_id") or entry.get("sha256")
            rel_path = entry.get("rel_path")

            if not storage.has_blob(blob_id):
                missing_blobs.append({"rel_path": rel_path, "blob_id": blob_id})
                continue

            try:
                # Read and decompress to verify SHA-256 hash (Fix #3: removed dead 'if False:' block)
                data = storage.read_blob_bytes(blob_id)
                h = hashlib.sha256(data).hexdigest()
                if h != blob_id:
                    corrupted_blobs.append({"rel_path": rel_path, "blob_id": blob_id})
                else:
                    verified_count += 1
            except Exception as e:
                corrupted_blobs.append({"rel_path": rel_path, "blob_id": blob_id, "error": str(e)})

            if progress_callback and (i % 10 == 0 or i == total_files - 1):
                progress_callback({
                    "verified": verified_count,
                    "total": total_files,
                    "percent": round(((i + 1) / max(1, total_files)) * 100, 1)
                })

        is_valid = (len(missing_blobs) == 0 and len(corrupted_blobs) == 0)
        return {
            "snapshot_id": snapshot_id,
            "is_valid": is_valid,
            "total_files": total_files,
            "verified_files": verified_count,
            "missing_blobs": missing_blobs,
            "corrupted_blobs": corrupted_blobs
        }
