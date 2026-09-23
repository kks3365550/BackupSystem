# File Contract Summary: `run.py`
- **Lines**: 143
- **Symbols Count**: 6
- **Imports Count**: 13

### Key Dependencies (Imports)
`os`, `sys`, `time`, `socket`, `asyncio`, `webbrowser`, `threading`, `subprocess`, `warnings`, `uvicorn`, `core.config`, `ctypes`, `traceback`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`ensure_dependencies`** | `global` | L29-L50 |  |
| `function` | **`is_port_in_use`** | `global` | L56-L62 | args: (port: int) -> bool |
| `function` | **`open_browser`** | `global` | L64-L83 | args: (port: int) |
| `function` | **`main`** | `global` | L85-L115 |  |
| `function` | **`show_error_dialog`** | `global` | L117-L123 | args: (title: str, message: str) |
| `function` | **`log_startup_error`** | `global` | L125-L133 | args: (err_str: str) |

