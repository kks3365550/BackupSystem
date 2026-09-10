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
        target_dir: str,
        selected_rel_paths: Optional[List[str]] = None,
        overwrite: bool = True,
        verify_hash: bool = True,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Restores files from a specific snapshot to target_dir.
        Fix #6: Parallel multi-threaded restoration using ThreadPoolExecutor.
        Fix #14: Path traversal check — all dest paths must remain under target_dir.
        """
        start_time = time.time()
        storage = BlobStorage(repo_dir)
        snapshot = SnapshotEngine.get_snapshot(repo_dir, snapshot_id)

        if not snapshot:
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found.")

        target_dir = os.path.abspath(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        entries = snapshot.get("entries", [])
        to_restore = []

        if selected_rel_paths:
            # Normalize selected paths
            normalized_selected = [p.replace('\\', '/').strip('/') for p in selected_rel_paths]
            for entry in entries:
                rel_p = entry.get("rel_path", "").replace('\\', '/').strip('/')
                for sel in normalized_selected:
                    if rel_p == sel or rel_p.startswith(sel + "/"):
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

        def _restore_one(entry):
            if cancel_event and cancel_event.is_set():
                return "cancelled", 0

            rel_path = entry.get("rel_path")
            blob_id = entry.get("blob_id") or entry.get("sha256")
            f_size = entry.get("size", 0)
            f_mtime = entry.get("mtime")

            if not rel_path or not blob_id:
                return "skip", 0

            dest_path = os.path.normpath(os.path.join(target_dir, rel_path))

            # Fix #14: Path traversal protection
            if not dest_path.startswith(target_dir):
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

                # If restored file is a registry key (.reg), auto-import to Windows
                if dest_path.lower().endswith(".reg"):
                    try:
                        from core.registry_backup import import_registry_file
                        import_registry_file(dest_path)
                    except Exception:
                        pass

                return "ok", f_size
            except Exception as e:
                return ("fail", 0, rel_path, str(e))

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

        duration = time.time() - start_time
        return {
            "snapshot_id": snapshot_id,
            "target_dir": target_dir,
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
