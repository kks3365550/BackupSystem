# File Contract Summary: `core/scheduler.py`
- **Lines**: 356
- **Symbols Count**: 17
- **Imports Count**: 20

### Key Dependencies (Imports)
`os`, `json`, `glob`, `time`, `threading`, `datetime`, `typing`, `typing`, `typing`, `typing`, `typing`, `core.config`, `core.snapshot`, `core.notifier`, `core.notifier`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`BackupScheduler`** | `global` | L11-L356 |  |
| `method` | **`__new__`** | `BackupScheduler` | L15-L20 | args: (cls) |
| `function` | **`_init`** | `BackupScheduler` | L22-L31 | args: (self) |
| `function` | **`start`** | `BackupScheduler` | L33-L39 | args: (self) |
| `function` | **`stop`** | `BackupScheduler` | L41-L45 | args: (self) |
| `function` | **`register_log_callback`** | `BackupScheduler` | L47-L48 | args: (self, callback) |
| `function` | **`_log`** | `BackupScheduler` | L50-L57 | args: (self, profile_name: str, message: str, level: str) |
| `function` | **`_should_run_profile`** | `BackupScheduler` | L59-L100 | args: (self, profile) -> bool |
| `function` | **`_run_profile_backup`** | `BackupScheduler` | L102-L189 | args: (self, profile) |
| `function` | **`on_progress`** | `BackupScheduler::_run_profile_backup` | L128-L130 | args: (p_data) |
| `function` | **`_load_audit_state`** | `BackupScheduler` | L191-L198 | args: (self) |
| `function` | **`_save_audit_state`** | `BackupScheduler` | L200-L210 | args: (self, state) |
| `function` | **`_is_backup_running`** | `BackupScheduler` | L212-L213 | args: (self) -> bool |
| `function` | **`_run_tier2_weekly_audit`** | `BackupScheduler` | L215-L260 | args: (self, repo_dir: str) /* Tier 2: 주간(Weekly) 모든 스냅샷의 Manifest 서명 및 */ |
| `function` | **`_run_tier3_monthly_audit`** | `BackupScheduler` | L262-L281 | args: (self, repo_dir: str) /* Tier 3: 월간(Monthly) 저장소 내 모든 블롭(.blob)의  */ |
| `function` | **`_check_deep_scans`** | `BackupScheduler` | L283-L334 | args: (self, profiles) /* Tier 2/Tier 3 주기 검사 및 심야 스케줄링 트리거 */ |
| `function` | **`_run_loop`** | `BackupScheduler` | L336-L356 | args: (self) |

