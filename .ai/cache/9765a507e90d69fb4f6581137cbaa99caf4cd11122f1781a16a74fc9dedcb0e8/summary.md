# File Contract Summary: `test_backup_system.py`
- **Lines**: 213
- **Symbols Count**: 3
- **Imports Count**: 11

### Key Dependencies (Imports)
`os`, `sys`, `time`, `shutil`, `tempfile`, `stat`, `core.snapshot`, `core.restore`, `core.storage`, `core.hasher`, `core.config`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`safe_rmtree`** | `global` | L13-L22 | args: (path) |
| `function` | **`_handle_readonly`** | `safe_rmtree` | L16-L21 | args: (func, p, excinfo) |
| `function` | **`test_full_system_flow`** | `global` | L24-L209 |  |

