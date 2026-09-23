# File Contract Summary: `web/app.py`
- **Lines**: 1598
- **Symbols Count**: 69
- **Imports Count**: 78

### Key Dependencies (Imports)
`os`, `sys`, `time`, `json`, `base64`, `shutil`, `threading`, `psutil`, `datetime`, `tempfile`, `collections`, `contextlib`, `typing`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`get_current_version`** | `global` | L37-L51 | -> str |
| `function` | **`_cpu_monitor`** | `global` | L57-L62 |  |
| `function` | **`append_task_log`** | `global` | L81-L85 | args: (msg: str, level: str) |
| `function` | **`lifespan`** | `global` | L90-L106 | args: (app: FastAPI) |
| `class` | **`AuthSetupRequest`** | `global` | L111-L113 | extends: BaseModel |
| `class` | **`AuthLoginRequest`** | `global` | L115-L116 | extends: BaseModel |
| `class` | **`AuthChangePasswordRequest`** | `global` | L118-L120 | extends: BaseModel |
| `class` | **`AuthBypassRequest`** | `global` | L122-L123 | extends: BaseModel |
| `function` | **`auth_middleware`** | `global` | L128-L173 | args: (request: Request, call_next) |
| `function` | **`auth_status`** | `global` | L178-L187 | args: (request: Request) |
| `function` | **`auth_setup`** | `global` | L190-L197 | args: (req: AuthSetupRequest) |
| `function` | **`auth_login`** | `global` | L200-L213 | args: (req: AuthLoginRequest) |
| `function` | **`auth_logout`** | `global` | L216-L226 | args: (request: Request) |
| `function` | **`auth_change_password`** | `global` | L229-L236 | args: (req: AuthChangePasswordRequest) |
| `function` | **`auth_toggle_bypass`** | `global` | L239-L244 | args: (req: AuthBypassRequest) |
| `function` | **`index_page`** | `global` | L251-L252 | args: (request: Request) |
| `function` | **`get_system_info`** | `global` | L256-L287 |  |
| `function` | **`get_storage_stats`** | `global` | L290-L316 | args: (repo_dir) |
| `class` | **`BrowseDirRequest`** | `global` | L319-L320 | extends: BaseModel |
| `function` | **`browse_directory`** | `global` | L323-L365 | args: (req: BrowseDirRequest) |
| `function` | **`list_profiles`** | `global` | L369-L370 |  |
| `function` | **`save_profile`** | `global` | L373-L376 | args: (profile) |
| `function` | **`delete_profile`** | `global` | L379-L383 | args: (profile_id: str) |
| `function` | **`_get_all_candidate_repos`** | `global` | L385-L436 | args: (repo_dir) /* Auto-discovers all active backup reposit */ |
| `function` | **`_latest_snap_time`** | `_get_all_candidate_repos` | L427-L433 | args: (r: str) -> float |
| `function` | **`list_snapshots`** | `global` | L440-L472 | args: (repo_dir) |
| `function` | **`_find_snapshot_repo`** | `global` | L474-L482 | args: (snapshot_id: str, repo_dir) |
| `function` | **`get_snapshot`** | `global` | L485-L505 | args: (snapshot_id: str, repo_dir, include_entries: bool) |
| `function` | **`browse_snapshot`** | `global` | L508-L515 | args: (snapshot_id: str, subpath: str, repo_dir) |
| `function` | **`get_snapshot_tree`** | `global` | L518-L525 | args: (snapshot_id: str, repo_dir) |
| `function` | **`delete_snapshot`** | `global` | L528-L536 | args: (snapshot_id: str, repo_dir) |
| `function` | **`list_installed_apps`** | `global` | L540-L541 | args: (refresh: bool) |
| `function` | **`list_project_items`** | `global` | L544-L545 |  |
| `class` | **`RunBackupRequest`** | `global` | L548-L553 | extends: BaseModel |
| `class` | **`RunCustomSelectionBackupRequest`** | `global` | L555-L563 | extends: BaseModel |
| `function` | **`_background_custom_backup_task`** | `global` | L565-L815 | args: (params) |
| `function` | **`on_progress`** | `_background_custom_backup_task` | L721-L725 | args: (p_data) |
| `function` | **`run_custom_selection_backup`** | `global` | L818-L836 | args: (req: RunCustomSelectionBackupRequest, background_tasks: BackgroundTasks) |
| `function` | **`_background_backup_task`** | `global` | L839-L978 | args: (params) |
| `function` | **`on_progress`** | `_background_backup_task` | L880-L884 | args: (p_data) |
| `function` | **`run_backup`** | `global` | L981-L999 | args: (req: RunBackupRequest, background_tasks: BackgroundTasks) |
| `function` | **`cancel_backup`** | `global` | L1002-L1008 |  |
| `function` | **`get_task_status`** | `global` | L1011-L1021 |  |
| `class` | **`RunRestoreRequest`** | `global` | L1024-L1030 | extends: BaseModel |
| `function` | **`_background_restore_task`** | `global` | L1032-L1086 | args: (params) |
| `function` | **`on_progress`** | `_background_restore_task` | L1052-L1054 | args: (p_data) |
| `function` | **`run_restore`** | `global` | L1089-L1107 | args: (req: RunRestoreRequest, background_tasks: BackgroundTasks) |
| `class` | **`RunVerifyRequest`** | `global` | L1110-L1112 | extends: BaseModel |
| `function` | **`run_verify`** | `global` | L1115-L1144 | args: (req: RunVerifyRequest) |
| `function` | **`prune_storage`** | `global` | L1148-L1156 | args: (repo_dir) |
| `class` | **`WindowsTaskRegisterRequest`** | `global` | L1161-L1164 | extends: BaseModel |
| `function` | **`get_windows_task_status`** | `global` | L1167-L1168 |  |
| `function` | **`register_windows_task`** | `global` | L1171-L1177 | args: (req: WindowsTaskRegisterRequest) |
| `function` | **`unregister_windows_task`** | `global` | L1180-L1183 |  |
| `class` | **`SystemImageStartRequest`** | `global` | L1188-L1189 | extends: BaseModel |
| `function` | **`get_system_image_status`** | `global` | L1192-L1193 | args: (target_drive: str) |
| `function` | **`start_system_image`** | `global` | L1196-L1201 | args: (req: SystemImageStartRequest) |
| `function` | **`get_system_image_logs`** | `global` | L1204-L1205 |  |
| `function` | **`stop_system_image`** | `global` | L1208-L1209 |  |
| `function` | **`shutdown_system`** | `global` | L1213-L1218 |  |
| `function` | **`_kill`** | `shutdown_system` | L1214-L1216 |  |
| `function` | **`self_update`** | `global` | L1222-L1341 | args: (request: Request, custom_body: bytes, custom_signature: str) /* Receives raw zip binary of latest code,  */ |
| `function` | **`_trigger_update_and_restart`** | `self_update` | L1322-L1335 |  |
| `function` | **`get_release_info`** | `global` | L1349-L1377 | /* Returns latest release package metadata  */ |
| `function` | **`download_update_package`** | `global` | L1381-L1405 | /* Streams the signed release zip package t */ |
| `function` | **`check_remote_release`** | `global` | L1409-L1459 | args: (master_url: str) /* Queries the master release origin (K12)  */ |
| `function` | **`_parse_v`** | `check_remote_release` | L1428-L1432 | args: (v_str) |
| `function` | **`sync_remote_release`** | `global` | L1463-L1487 | args: (request: Request) /* Downloads signed release from master ser */ |
| `function` | **`get_alerts_summary`** | `global` | L1492-L1597 | /* Aggregates recent backup failures, activ */ |

