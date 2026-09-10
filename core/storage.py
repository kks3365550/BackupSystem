import os
import zlib
import json
import hashlib
import shutil
from typing import Optional, Tuple, Dict, Any, Set, List
from core.hasher import calculate_sha256, calculate_bytes_sha256

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

class BlobStorage:
    def __init__(self, repo_dir: str):
        self.repo_dir = os.path.abspath(repo_dir)
        self.blobs_dir = os.path.join(self.repo_dir, "blobs")
        self.snapshots_dir = os.path.join(self.repo_dir, "snapshots")
        self.meta_file = os.path.join(self.repo_dir, "repo_meta.json")
        self.init_repo()
        from core.metadata_db import MetadataDB
        self.db = MetadataDB(self.repo_dir)

    def init_repo(self):
        os.makedirs(self.blobs_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)
        if not os.path.exists(self.meta_file):
            meta = {
                "version": "2.0.0",
                "compression": "zstd" if HAS_ZSTD else "zlib",
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

    def put_file_blob(self, filepath: str, sha256_hash: Optional[str] = None, compress_level: int = 3) -> Tuple[str, int, int, bool]:
        """
        Compresses and saves a file as a content-addressed blob.
        Uses Zstandard if available (high speed & high compression), otherwise zlib.
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

        stored_size = 0
        with open(filepath, "rb") as fin, open(temp_blob_path, "wb") as fout:
            if HAS_ZSTD:
                cctx = zstd.ZstdCompressor(level=compress_level)
                with cctx.stream_writer(fout, closefd=False) as compressor:
                    while True:
                        chunk = fin.read(1048576)
                        if not chunk:
                            break
                        compressor.write(chunk)
            else:
                compressor = zlib.compressobj(level=compress_level if compress_level in range(1, 10) else 6)
                while True:
                    chunk = fin.read(1048576)
                    if not chunk:
                        break
                    compressed_chunk = compressor.compress(chunk)
                    if compressed_chunk:
                        fout.write(compressed_chunk)
                tail = compressor.flush()
                if tail:
                    fout.write(tail)

        stored_size = os.path.getsize(temp_blob_path)
        os.replace(temp_blob_path, blob_path)
        self.db.record_new_blob(stored_size)
        return sha256_hash, orig_size, stored_size, True

    def put_file_blob_onepass(self, filepath: str, compress_level: int = 3, cancel_event=None) -> Tuple[str, int, int, bool]:
        """
        Single-Pass (One-Pass) streaming hash and compression:
        Reads the file only ONCE to compute SHA-256 and compress to temporary blob.
        Deduplicates if the blob already exists. Cuts disk I/O by 50%.
        """
        orig_size = os.path.getsize(filepath)
        sha256 = hashlib.sha256()

        temp_dir = os.path.join(self.blobs_dir, "_temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"tmp_{os.getpid()}_{hashlib.md5(filepath.encode('utf-8', 'replace')).hexdigest()}_{os.urandom(4).hex()}.blob")

        try:
            with open(filepath, "rb") as fin, open(temp_file, "wb") as fout:
                if HAS_ZSTD:
                    cctx = zstd.ZstdCompressor(level=compress_level)
                    with cctx.stream_writer(fout, closefd=False) as compressor:
                        while True:
                            if cancel_event and cancel_event.is_set():
                                raise InterruptedError("Operation cancelled")
                            chunk = fin.read(1048576)
                            if not chunk:
                                break
                            sha256.update(chunk)
                            compressor.write(chunk)
                else:
                    compressor = zlib.compressobj(level=compress_level if compress_level in range(1, 10) else 6)
                    while True:
                        if cancel_event and cancel_event.is_set():
                            raise InterruptedError("Operation cancelled")
                        chunk = fin.read(1048576)
                        if not chunk:
                            break
                        sha256.update(chunk)
                        compressed_chunk = compressor.compress(chunk)
                        if compressed_chunk:
                            fout.write(compressed_chunk)
                    tail = compressor.flush()
                    if tail:
                        fout.write(tail)

            sha256_hash = sha256.hexdigest()
            blob_path = self.get_blob_abs_path(sha256_hash)

            # Deduplication: If already stored, remove temp and return existing
            if os.path.exists(blob_path):
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                stored_size = os.path.getsize(blob_path)
                return sha256_hash, orig_size, stored_size, False

            # New blob
            os.makedirs(os.path.dirname(blob_path), exist_ok=True)
            os.replace(temp_file, blob_path)
            stored_size = os.path.getsize(blob_path)
            self.db.record_new_blob(stored_size)
            return sha256_hash, orig_size, stored_size, True

        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

    def put_bytes_blob(self, data: bytes, compress_level: int = 3) -> Tuple[str, int, int, bool]:
        sha256_hash = calculate_bytes_sha256(data)
        blob_path = self.get_blob_abs_path(sha256_hash)
        orig_size = len(data)

        if os.path.exists(blob_path):
            stored_size = os.path.getsize(blob_path)
            return sha256_hash, orig_size, stored_size, False

        os.makedirs(os.path.dirname(blob_path), exist_ok=True)
        if HAS_ZSTD:
            cctx = zstd.ZstdCompressor(level=compress_level)
            compressed = cctx.compress(data)
        else:
            compressed = zlib.compress(data, level=compress_level if compress_level in range(1, 10) else 6)

        temp_blob_path = blob_path + ".tmp"
        with open(temp_blob_path, "wb") as f:
            f.write(compressed)
        os.replace(temp_blob_path, blob_path)
        self.db.record_new_blob(len(compressed))
        return sha256_hash, orig_size, len(compressed), True

    def extract_blob_to_file(self, sha256_hash: str, dest_filepath: str, verify_hash: bool = True) -> bool:
        """
        Decompresses blob directly to dest_filepath with HYBRID automatic format detection.
        Detects Zstandard vs zlib magic bytes with zero false-positives and fallbacks.
        """
        blob_path = self.get_blob_abs_path(sha256_hash)
        if not os.path.exists(blob_path):
            raise FileNotFoundError(f"Blob not found in repository: {sha256_hash}")

        os.makedirs(os.path.dirname(dest_filepath), exist_ok=True)
        temp_dest = dest_filepath + ".restore.tmp"

        # Check first 4 magic bytes
        with open(blob_path, "rb") as f_head:
            magic_header = f_head.read(4)

        is_zstd = (magic_header == ZSTD_MAGIC)

        # Decompress with appropriate engine + fallback
        success = False
        sha256 = hashlib.sha256() if verify_hash else None

        # Attempt 1: primary detected engine
        for engine in ("zstd" if is_zstd else "zlib", "zlib" if is_zstd else "zstd"):
            if engine == "zstd" and not HAS_ZSTD:
                continue
            try:
                if sha256:
                    sha256 = hashlib.sha256()

                with open(blob_path, "rb") as fin, open(temp_dest, "wb") as fout:
                    if engine == "zstd":
                        dctx = zstd.ZstdDecompressor()
                        with dctx.stream_reader(fin) as reader:
                            while True:
                                chunk = reader.read(1048576)
                                if not chunk:
                                    break
                                fout.write(chunk)
                                if sha256:
                                    sha256.update(chunk)
                    else:
                        decompressor = zlib.decompressobj()
                        while True:
                            chunk = fin.read(1048576)
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
                success = True
                break
            except Exception:
                if os.path.exists(temp_dest):
                    try:
                        os.remove(temp_dest)
                    except OSError:
                        pass
                continue

        if not success:
            raise RuntimeError(f"Failed to decompress blob '{sha256_hash}' using both zstd and zlib engines.")

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

        if compressed.startswith(ZSTD_MAGIC) and HAS_ZSTD:
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(compressed)
        try:
            return zlib.decompress(compressed)
        except Exception:
            if HAS_ZSTD:
                dctx = zstd.ZstdDecompressor()
                return dctx.decompress(compressed)
            raise

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
        if deleted_count > 0:
            self.db.record_removed_blobs(deleted_count, freed_bytes)
        return deleted_count, freed_bytes

    def get_storage_stats(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Returns storage stats instantly via SQLite metadata cache."""
        return self.db.get_storage_stats(force_refresh=force_refresh)
