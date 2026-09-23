# File Contract Summary: `core/metadata_db.py`
- **Lines**: 330
- **Symbols Count**: 12
- **Imports Count**: 11

### Key Dependencies (Imports)
`os`, `time`, `json`, `sqlite3`, `threading`, `contextlib`, `typing`, `typing`, `typing`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`MetadataDB`** | `global` | L9-L330 |  |
| `method` | **`__init__`** | `MetadataDB` | L12-L17 | args: (self, repo_dir: str) |
| `function` | **`_get_connection`** | `MetadataDB` | L20-L34 | args: (self) |
| `function` | **`_init_db`** | `MetadataDB` | L36-L82 | args: (self) |
| `function` | **`record_new_blob`** | `MetadataDB` | L84-L110 | args: (self, stored_size: int, count: int) /* Atomically increments blob count and sto */ |
| `function` | **`record_removed_blobs`** | `MetadataDB` | L112-L126 | args: (self, deleted_count: int, freed_bytes: int) /* Atomically decrements blob count and sto */ |
| `function` | **`rebuild_blobs_summary`** | `MetadataDB` | L128-L154 | args: (self) /* Scans disk to accurately recalculate blo */ |
| `function` | **`sync_snapshots`** | `MetadataDB` | L156-L230 | args: (self) /* Synchronizes snapshot JSON metadata into */ |
| `function` | **`update_snapshot_verification`** | `MetadataDB` | L232-L245 | args: (self, snapshot_id: str, is_verified: bool, error_count: int) /* Updates verification status for a specif */ |
| `function` | **`list_snapshots`** | `MetadataDB` | L247-L292 | args: (self) /* Returns snapshot metadata summaries in u */ |
| `function` | **`get_storage_stats`** | `MetadataDB` | L294-L322 | args: (self, force_refresh: bool) /* Calculates storage stats in 0.001s using */ |
| `function` | **`delete_snapshot_record`** | `MetadataDB` | L324-L330 | args: (self, snapshot_id: str) |

