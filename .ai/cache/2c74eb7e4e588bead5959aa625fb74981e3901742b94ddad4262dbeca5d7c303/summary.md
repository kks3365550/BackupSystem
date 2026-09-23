# File Contract Summary: `core/system_image.py`
- **Lines**: 257
- **Symbols Count**: 8
- **Imports Count**: 15

### Key Dependencies (Imports)
`os`, `sys`, `time`, `shutil`, `ctypes`, `subprocess`, `datetime`, `threading`, `typing`, `typing`, `typing`, `typing`, `core.notifier`, `core.notifier`, `core.notifier`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`SystemImageManager`** | `global` | L11-L257 |  |
| `method` | **`is_admin`** | `SystemImageManager` | L18-L22 | args: (cls) -> bool |
| `function` | **`get_status`** | `SystemImageManager` | L25-L92 | args: (cls, target_drive: str) |
| `function` | **`append_log`** | `SystemImageManager` | L95-L101 | args: (cls, msg: str, level: str) |
| `function` | **`get_logs`** | `SystemImageManager` | L104-L109 | args: (cls) |
| `function` | **`start_backup`** | `SystemImageManager` | L112-L240 | args: (cls, target_drive: str, log_callback) |
| `function` | **`_run_worker`** | `SystemImageManager::start_backup` | L123-L236 |  |
| `function` | **`stop_backup`** | `SystemImageManager` | L243-L257 | args: (cls) |

