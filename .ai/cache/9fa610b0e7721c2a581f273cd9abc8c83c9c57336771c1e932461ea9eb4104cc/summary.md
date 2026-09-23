# File Contract Summary: `core/snapshot.py`
- **Lines**: 954
- **Symbols Count**: 18
- **Imports Count**: 42

### Key Dependencies (Imports)
`os`, `time`, `json`, `uuid`, `datetime`, `threading`, `queue`, `concurrent.futures`, `typing`, `typing`, `typing`, `typing`, `typing`, `typing`, `core.hasher`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`SnapshotEngine`** | `global` | L26-L954 |  |
| `method` | **`_generate_snapshot_id`** | `SnapshotEngine` | L28-L31 | -> str |
| `function` | **`_scan_sources_parallel`** | `SnapshotEngine` | L34-L171 | args: (cls, sources, path_filter: PathFilter, num_workers: int) /* Fast parallel directory exploration usin */ |
| `function` | **`worker_loop`** | `SnapshotEngine::_scan_sources_parallel` | L75-L157 |  |
| `function` | **`create_snapshot`** | `SnapshotEngine` | L174-L210 | args: (cls, repo_dir: str, sources, profile_id: str) |
| `function` | **`_create_snapshot_internal`** | `SnapshotEngine` | L213-L278 | args: (cls, repo_dir: str, sources, profile_id: str) |
| `function` | **`_execute_backup_pipeline`** | `SnapshotEngine` | L281-L678 | args: (cls, repo_dir: str, sources, profile_id: str) |
| `function` | **`_worker_process_file`** | `SnapshotEngine::_execute_backup_pipeline` | L390-L422 | args: (item) |
| `function` | **`_async_replicate_task`** | `SnapshotEngine::_execute_backup_pipeline` | L651-L657 |  |
| `function` | **`list_snapshots`** | `SnapshotEngine` | L681-L712 | args: (cls, repo_dir: str) |
| `function` | **`get_snapshot`** | `SnapshotEngine` | L715-L721 | args: (cls, repo_dir: str, snapshot_id: str) |
| `function` | **`ensure_disk_space`** | `SnapshotEngine` | L724-L733 | args: (cls, repo_dir: str, min_free_gb: float) /* Fail-Closed Low-Disk Safeguard: */ |
| `function` | **`delete_snapshot`** | `SnapshotEngine` | L736-L768 | args: (cls, repo_dir: str, snapshot_id: str, prune_orphaned_blobs: bool) -> bool |
| `function` | **`prune_snapshots`** | `SnapshotEngine` | L771-L793 | args: (cls, repo_dir: str, retention_count, max_age_days) /* Prunes old snapshots based on retention  */ |
| `function` | **`prune_storage`** | `SnapshotEngine` | L796-L815 | args: (cls, repo_dir: str) /* Collects all referenced blob hashes acro */ |
| `function` | **`build_snapshot_tree`** | `SnapshotEngine` | L818-L872 | args: (cls, snapshot_data) /* Converts snapshot file entries list into */ |
| `function` | **`dict_to_list`** | `SnapshotEngine::build_snapshot_tree` | L857-L870 | args: (node) |
| `function` | **`browse_snapshot_directory`** | `SnapshotEngine` | L879-L954 | args: (cls, repo_dir: str, snapshot_id: str, subpath: str) /* High-performance on-demand folder browse */ |

