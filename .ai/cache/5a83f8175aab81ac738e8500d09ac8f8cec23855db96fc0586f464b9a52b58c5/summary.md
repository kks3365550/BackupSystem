# File Contract Summary: `tray_app.py`
- **Lines**: 350
- **Symbols Count**: 19
- **Imports Count**: 11

### Key Dependencies (Imports)
`os`, `sys`, `json`, `time`, `ctypes`, `webbrowser`, `threading`, `urllib.request`, `urllib.error`, `ctypes`, `subprocess`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`GUID`** | `global` | L69-L75 | extends: ctypes.Structure |
| `class` | **`NOTIFYICONDATAW`** | `global` | L78-L95 | extends: ctypes.Structure |
| `class` | **`WNDCLASSEXW`** | `global` | L105-L119 | extends: ctypes.Structure |
| `class` | **`POINT`** | `global` | L122-L123 | extends: ctypes.Structure |
| `class` | **`BackupTrayApp`** | `global` | L135-L345 |  |
| `method` | **`__init__`** | `BackupTrayApp` | L136-L142 | args: (self) |
| `function` | **`run`** | `BackupTrayApp` | L144-L204 | args: (self) |
| `function` | **`show_notification`** | `BackupTrayApp` | L206-L214 | args: (self, title: str, text: str, info_flag: int) /* Windows Native 풍선/토스트 알림 발송 */ |
| `function` | **`wnd_proc`** | `BackupTrayApp` | L216-L243 | args: (self, hwnd, msg, wparam) |
| `function` | **`show_context_menu`** | `BackupTrayApp` | L245-L260 | args: (self) /* 우클릭 팝업 메뉴 표시 */ |
| `function` | **`open_dashboard`** | `BackupTrayApp` | L262-L263 | args: (self) |
| `function` | **`trigger_backup`** | `BackupTrayApp` | L265-L282 | args: (self) |
| `function` | **`_call`** | `BackupTrayApp::trigger_backup` | L266-L280 |  |
| `function` | **`check_status_now`** | `BackupTrayApp` | L284-L297 | args: (self) |
| `function` | **`_call`** | `BackupTrayApp::check_status_now` | L285-L295 |  |
| `function` | **`restart_server`** | `BackupTrayApp` | L299-L312 | args: (self) |
| `function` | **`_call`** | `BackupTrayApp::restart_server` | L300-L310 |  |
| `function` | **`exit_app`** | `BackupTrayApp` | L314-L316 | args: (self) |
| `function` | **`_monitor_server_status`** | `BackupTrayApp` | L318-L345 | args: (self) /* 백그라운드에서 백업 진행/완료 상태를 모니터링하여 토스트 알림 발송 */ |

