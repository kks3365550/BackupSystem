import os
import time
from typing import Dict, List, Any, Optional, Callable
from core.storage import BlobStorage
from core.snapshot import SnapshotEngine
from core.hasher import calculate_sha256

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
        If selected_rel_paths is provided, only restores matching files or subpaths.
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

        for entry in to_restore:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Restore operation was cancelled by user.")

            rel_path = entry.get("rel_path")
            blob_id = entry.get("blob_id") or entry.get("sha256")
            f_size = entry.get("size", 0)
            f_mtime = entry.get("mtime")

            if not rel_path or not blob_id:
                continue

            dest_path = os.path.normpath(os.path.join(target_dir, rel_path))

            if os.path.exists(dest_path) and not overwrite:
                skipped_files += 1
                continue

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

                restored_files += 1
                restored_bytes += f_size
            except Exception as e:
                failed_files.append({
                    "rel_path": rel_path,
                    "error": str(e)
                })

            if progress_callback and (restored_files % 10 == 0 or (restored_files + skipped_files + len(failed_files)) == total_files):
                pct = round(((restored_files + skipped_files + len(failed_files)) / max(1, total_files)) * 100, 1)
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
                # Read and decompress to verify hash
                data = storage.read_blob_bytes(blob_id)
                actual_hash = calculate_sha256_bytes(data) if False else None
                # Check SHA256
                import hashlib
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
