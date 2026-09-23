# File Contract Summary: `core/storage.py`
- **Lines**: 539
- **Symbols Count**: 17
- **Imports Count**: 22

### Key Dependencies (Imports)
`os`, `zlib`, `json`, `hashlib`, `shutil`, `threading`, `typing`, `typing`, `typing`, `typing`, `typing`, `typing`, `core.hasher`, `core.hasher`, `zstandard`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`InsufficientDiskSpaceError`** | `global` | L18-L20 | extends: Exception /* Raised when repository disk free space i */ |
| `function` | **`get_disk_free_gb`** | `global` | L24-L30 | args: (path: str) -> float /* Returns free disk space in gigabytes for */ |
| `function` | **`verify_disk_space_or_fail`** | `global` | L32-L45 | args: (path: str, min_free_gb: float) -> float /* Fail-Closed Disk Space Verification: */ |
| `class` | **`BlobStorage`** | `global` | L55-L539 |  |
| `method` | **`__init__`** | `BlobStorage` | L61-L75 | args: (self, repo_dir: str, crypto_engine) |
| `function` | **`init_repo`** | `BlobStorage` | L77-L93 | args: (self) |
| `function` | **`get_blob_rel_path`** | `BlobStorage` | L95-L99 | args: (self, sha256_hash: str) -> str |
| `function` | **`get_blob_abs_path`** | `BlobStorage` | L101-L104 | args: (self, sha256_hash: str) -> str |
| `function` | **`has_blob`** | `BlobStorage` | L106-L117 | args: (self, sha256_hash: str) -> bool |
| `function` | **`bulk_add_blob_cache`** | `BlobStorage` | L119-L124 | args: (self, blob_ids) -> None /* Pre-populates the in-memory blob cache t */ |
| `function` | **`put_file_blob`** | `BlobStorage` | L126-L198 | args: (self, filepath: str, sha256_hash, compress_level: int) /* Compresses and saves a file as a content */ |
| `function` | **`put_file_blob_onepass`** | `BlobStorage` | L200-L337 | args: (self, filepath: str, compress_level: int, cancel_event) /* High-Performance Single-Pass (One-Pass)  */ |
| `function` | **`put_bytes_blob`** | `BlobStorage` | L339-L375 | args: (self, data: bytes, compress_level: int) |
| `function` | **`extract_blob_to_file`** | `BlobStorage` | L377-L491 | args: (self, sha256_hash: str, dest_filepath: str, verify_hash: bool) -> bool /* Decompresses blob directly to dest_filep */ |
| `function` | **`read_blob_bytes`** | `BlobStorage` | L493-L510 | args: (self, sha256_hash: str) -> bytes |
| `function` | **`prune_unreferenced_blobs`** | `BlobStorage` | L512-L535 | args: (self, active_hashes) /* Deletes blobs that are not present in ac */ |
| `function` | **`get_storage_stats`** | `BlobStorage` | L537-L539 | args: (self, force_refresh: bool) /* Returns storage stats instantly via SQLi */ |

