# File Contract Summary: `simulate_recovery.py`
- **Lines**: 409
- **Symbols Count**: 3
- **Imports Count**: 16

### Key Dependencies (Imports)
`os`, `sys`, `time`, `shutil`, `stat`, `hashlib`, `typing`, `typing`, `typing`, `core.snapshot`, `core.restore`, `core.storage`, `core.storage`, `core.storage`, `core.hasher`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`safe_rmtree`** | `global` | L27-L37 | args: (path: str) /* Safely removes directory tree unlocking  */ |
| `function` | **`_handle_readonly`** | `safe_rmtree` | L31-L36 | args: (func, p, excinfo) |
| `function` | **`run_disaster_recovery_simulation`** | `global` | L39-L405 |  |

