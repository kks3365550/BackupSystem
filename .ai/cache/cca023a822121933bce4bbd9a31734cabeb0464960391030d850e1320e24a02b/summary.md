# File Contract Summary: `core/windows_task.py`
- **Lines**: 137
- **Symbols Count**: 5
- **Imports Count**: 6

### Key Dependencies (Imports)
`os`, `sys`, `subprocess`, `typing`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`get_python_executable`** | `global` | L8-L25 | -> str /* Finds the best Python executable, priori */ |
| `function` | **`_run_schtasks_cmd`** | `global` | L27-L50 | args: (cmd_list: list, timeout: int) /* Safely executes schtasks with robust byt */ |
| `function` | **`register_windows_scheduled_task`** | `global` | L52-L98 | args: (profile_id, schedule_type: str, schedule_value: str) /* Registers or updates a scheduled task in */ |
| `function` | **`unregister_windows_scheduled_task`** | `global` | L100-L110 | /* Deletes the task from Windows Task Sched */ |
| `function` | **`get_windows_scheduled_task_status`** | `global` | L112-L137 | /* Queries current task status from Windows */ |

