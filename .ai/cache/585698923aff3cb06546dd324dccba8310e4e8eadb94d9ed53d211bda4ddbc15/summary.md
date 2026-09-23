# File Contract Summary: `cli.py`
- **Lines**: 174
- **Symbols Count**: 9
- **Imports Count**: 7

### Key Dependencies (Imports)
`argparse`, `sys`, `os`, `json`, `core.snapshot`, `core.restore`, `core.config`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`format_bytes`** | `global` | L16-L24 | args: (size_bytes: int) -> str |
| `function` | **`cmd_backup`** | `global` | L26-L71 | args: (args) |
| `function` | **`on_progress`** | `cmd_backup` | L49-L50 | args: (p) |
| `function` | **`cmd_list`** | `global` | L73-L87 | args: (args) |
| `function` | **`cmd_restore`** | `global` | L89-L108 | args: (args) |
| `function` | **`on_progress`** | `cmd_restore` | L96-L97 | args: (p) |
| `function` | **`cmd_verify`** | `global` | L110-L118 | args: (args) |
| `function` | **`cmd_stats`** | `global` | L120-L132 | args: (args) |
| `function` | **`main`** | `global` | L134-L171 |  |

