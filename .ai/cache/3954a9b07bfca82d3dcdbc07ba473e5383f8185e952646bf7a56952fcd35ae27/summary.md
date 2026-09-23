# File Contract Summary: `core/restore.py`
- **Lines**: 302
- **Symbols Count**: 4
- **Imports Count**: 15

### Key Dependencies (Imports)
`os`, `time`, `hashlib`, `threading`, `concurrent.futures`, `typing`, `typing`, `typing`, `typing`, `typing`, `core.storage`, `core.snapshot`, `core.registry_backup`, `subprocess`, `sys`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`RestoreEngine`** | `global` | L10-L302 |  |
| `method` | **`restore_snapshot`** | `RestoreEngine` | L12-L244 | args: (cls, repo_dir: str, snapshot_id: str, target_dir) /* Restores files from a specific snapshot. */ |
| `function` | **`_restore_one`** | `RestoreEngine::restore_snapshot` | L88-L137 | args: (entry) |
| `function` | **`verify_snapshot_integrity`** | `RestoreEngine` | L247-L302 | args: (cls, repo_dir: str, snapshot_id: str, progress_callback) /* Verifies that all blobs referenced by th */ |

