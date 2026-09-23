# File Contract Summary: `core/config.py`
- **Lines**: 151
- **Symbols Count**: 9
- **Imports Count**: 8

### Key Dependencies (Imports)
`os`, `json`, `uuid`, `typing`, `typing`, `typing`, `typing`, `shutil`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`ConfigManager`** | `global` | L43-L151 |  |
| `method` | **`_ensure_dir`** | `ConfigManager` | L45-L46 |  |
| `function` | **`get_settings`** | `ConfigManager` | L49-L61 | args: (cls) |
| `function` | **`save_settings`** | `ConfigManager` | L64-L67 | args: (cls, settings) |
| `function` | **`get_profiles`** | `ConfigManager` | L70-L93 | args: (cls) |
| `function` | **`save_profiles`** | `ConfigManager` | L96-L113 | args: (cls, profiles) |
| `function` | **`get_profile`** | `ConfigManager` | L117-L122 | args: (cls, profile_id: str) |
| `function` | **`save_profile`** | `ConfigManager` | L125-L141 | args: (cls, profile) |
| `function` | **`delete_profile`** | `ConfigManager` | L144-L151 | args: (cls, profile_id: str) -> bool |

