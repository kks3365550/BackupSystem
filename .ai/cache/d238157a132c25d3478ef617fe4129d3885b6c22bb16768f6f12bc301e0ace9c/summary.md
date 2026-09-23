# File Contract Summary: `emergency_restore.py`
- **Lines**: 465
- **Symbols Count**: 9
- **Imports Count**: 20

### Key Dependencies (Imports)
`os`, `sys`, `json`, `zlib`, `hashlib`, `time`, `glob`, `threading`, `concurrent.futures`, `typing`, `typing`, `typing`, `typing`, `zstandard`, `stat`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`format_bytes`** | `global` | L32-L39 | args: (size: int) -> str |
| `function` | **`get_blob_path`** | `global` | L41-L45 | args: (repo_dir: str, sha256_hash: str) -> str |
| `function` | **`extract_blob`** | `global` | L47-L106 | args: (blob_path: str, dest_path: str, expected_sha256: str, verify_hash: bool) -> bool |
| `function` | **`get_candidate_repositories`** | `global` | L108-L147 |  |
| `function` | **`_latest_snap_time`** | `get_candidate_repositories` | L138-L144 | args: (r: str) -> float |
| `function` | **`find_snapshots`** | `global` | L149-L172 | args: (repo_dir: str) |
| `function` | **`run_emergency_restore`** | `global` | L174-L393 | args: (repo_dir: str, snapshot_path: str, target_override, remap_user: bool) |
| `function` | **`_worker_restore`** | `run_emergency_restore` | L248-L290 | args: (entry) |
| `function` | **`main`** | `global` | L396-L462 |  |

