import os
import zlib
import json
import hashlib
import shutil
from typing import Optional, Tuple, Dict, Any, Set, List
from core.hasher import calculate_sha256, calculate_bytes_sha256

class BlobStorage:
    def __init__(self, repo_dir: str):
        self.repo_dir = os.path.abspath(repo_dir)
        self.blobs_dir = os.path.join(self.repo_dir, "blobs")
        self.snapshots_dir = os.path.join(self.repo_dir, "snapshots")
        self.meta_file = os.path.join(self.repo_dir, "repo_meta.json")
        self.init_repo()

    def init_repo(self):
        os.makedirs(self.blobs_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)
        if not os.path.exists(self.meta_file):
            meta = {
                "version": "1.0",
                "compression": "zlib",
                "format": "content-addressable-snapshots"
            }
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

    def get_blob_rel_path(self, sha256_hash: str) -> str:
        if not sha256_hash:
            return ""
        prefix = sha256_hash[:2]
        return os.path.join(prefix, f"{sha256_hash}.blob")

    def get_blob_abs_path(self, sha256_hash: str) -> str:
        if not sha256_hash:
            return ""
        return os.path.join(self.blobs_dir, self.get_blob_rel_path(sha256_hash))

    def has_blob(self, sha256_hash: str) -> bool:
        if not sha256_hash:
            return False
        blob_path = self.get_blob_abs_path(sha256_hash)
        return bool(blob_path and os.path.exists(blob_path))

    def put_file_blob(self, filepath: str, sha256_hash: Optional[str] = None, compress_level: int = 6) -> Tuple[str, int, int, bool]:
        """
        Compresses and saves a file as a content-addressed blob.
        Returns (sha256_hash, original_size, stored_size, is_new_blob).
        """
        orig_size = os.path.getsize(filepath)
        if not sha256_hash:
            sha256_hash = calculate_sha256(filepath)

        blob_path = self.get_blob_abs_path(sha256_hash)

        # Deduplication check: if blob already exists, skip writing!
        if os.path.exists(blob_path):
            stored_size = os.path.getsize(blob_path)
            return sha256_hash, orig_size, stored_size, False

        os.makedirs(os.path.dirname(blob_path), exist_ok=True)
        temp_blob_path = blob_path + ".tmp"

        compressor = zlib.compressobj(level=compress_level)
        stored_size = 0

        with open(filepath, "rb") as fin, open(temp_blob_path, "wb") as fout:
            while True:
                chunk = fin.read(65536)
                if not chunk:
                    break
                compressed_chunk = compressor.compress(chunk)
                if compressed_chunk:
                    fout.write(compressed_chunk)
                    stored_size += len(compressed_chunk)
            tail = compressor.flush()
            if tail:
                fout.write(tail)
                stored_size += len(tail)

        os.replace(temp_blob_path, blob_path)
        return sha256_hash, orig_size, stored_size, True

    def put_bytes_blob(self, data: bytes, compress_level: int = 6) -> Tuple[str, int, int, bool]:
        sha256_hash = calculate_bytes_sha256(data)
        blob_path = self.get_blob_abs_path(sha256_hash)
        orig_size = len(data)

        if os.path.exists(blob_path):
            stored_size = os.path.getsize(blob_path)
            return sha256_hash, orig_size, stored_size, False

        os.makedirs(os.path.dirname(blob_path), exist_ok=True)
        compressed = zlib.compress(data, level=compress_level)
        temp_blob_path = blob_path + ".tmp"
        with open(temp_blob_path, "wb") as f:
            f.write(compressed)
        os.replace(temp_blob_path, blob_path)
        return sha256_hash, orig_size, len(compressed), True

    def extract_blob_to_file(self, sha256_hash: str, dest_filepath: str, verify_hash: bool = True) -> bool:
        """Decompresses blob directly to dest_filepath and optionally verifies hash."""
        blob_path = self.get_blob_abs_path(sha256_hash)
        if not os.path.exists(blob_path):
            raise FileNotFoundError(f"Blob not found in repository: {sha256_hash}")

        os.makedirs(os.path.dirname(dest_filepath), exist_ok=True)
        temp_dest = dest_filepath + ".restore.tmp"

        decompressor = zlib.decompressobj()
        sha256 = hashlib.sha256() if verify_hash else None

        with open(blob_path, "rb") as fin, open(temp_dest, "wb") as fout:
            while True:
                chunk = fin.read(65536)
                if not chunk:
                    break
                decompressed_chunk = decompressor.decompress(chunk)
                if decompressed_chunk:
                    fout.write(decompressed_chunk)
                    if sha256:
                        sha256.update(decompressed_chunk)
            tail = decompressor.flush()
            if tail:
                fout.write(tail)
                if sha256:
                    sha256.update(tail)

        if verify_hash and sha256.hexdigest() != sha256_hash:
            if os.path.exists(temp_dest):
                os.remove(temp_dest)
            raise ValueError(f"Hash verification failed for {dest_filepath} (Expected: {sha256_hash}, got {sha256.hexdigest()})")

        if os.path.exists(dest_filepath):
            os.remove(dest_filepath)
        os.replace(temp_dest, dest_filepath)
        return True

    def read_blob_bytes(self, sha256_hash: str) -> bytes:
        blob_path = self.get_blob_abs_path(sha256_hash)
        if not os.path.exists(blob_path):
            raise FileNotFoundError(f"Blob not found: {sha256_hash}")
        with open(blob_path, "rb") as f:
            compressed = f.read()
        return zlib.decompress(compressed)

    def prune_unreferenced_blobs(self, active_hashes: Set[str]) -> Tuple[int, int]:
        """Deletes blobs that are not present in active_hashes set. Returns (deleted_count, freed_bytes)."""
        deleted_count = 0
        freed_bytes = 0

        for root, _, files in os.walk(self.blobs_dir):
            for file in files:
                if file.endswith(".blob"):
                    blob_hash = file[:-5]
                    if blob_hash not in active_hashes:
                        blob_path = os.path.join(root, file)
                        try:
                            fsize = os.path.getsize(blob_path)
                            os.remove(blob_path)
                            deleted_count += 1
                            freed_bytes += fsize
                        except OSError:
                            pass
        return deleted_count, freed_bytes

    def get_storage_stats(self) -> Dict[str, Any]:
        total_blobs = 0
        total_blob_bytes = 0
        for root, _, files in os.walk(self.blobs_dir):
            for file in files:
                if file.endswith(".blob"):
                    total_blobs += 1
                    try:
                        total_blob_bytes += os.path.getsize(os.path.join(root, file))
                    except OSError:
                        pass

        snapshot_files = [f for f in os.listdir(self.snapshots_dir) if f.endswith(".json")]
        total_logical_bytes = 0
        total_logical_files = 0

        for snap_name in snapshot_files:
            try:
                with open(os.path.join(self.snapshots_dir, snap_name), "r", encoding="utf-8") as f:
                    snap_data = json.load(f)
                    total_logical_bytes += snap_data.get("summary", {}).get("total_bytes", 0)
                    total_logical_files += snap_data.get("summary", {}).get("total_files", 0)
            except Exception:
                pass

        saved_bytes = max(0, total_logical_bytes - total_blob_bytes)
        ratio = (saved_bytes / total_logical_bytes * 100) if total_logical_bytes > 0 else 0.0

        return {
            "total_blobs": total_blobs,
            "stored_bytes": total_blob_bytes,
            "logical_bytes": total_logical_bytes,
            "total_snapshots": len(snapshot_files),
            "dedup_saved_bytes": saved_bytes,
            "savings_percentage": round(ratio, 1)
        }
