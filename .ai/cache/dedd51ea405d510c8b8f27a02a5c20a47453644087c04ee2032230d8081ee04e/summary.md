# File Contract Summary: `core/registry_backup.py`
- **Lines**: 214
- **Symbols Count**: 10
- **Imports Count**: 10

### Key Dependencies (Imports)
`os`, `sys`, `subprocess`, `typing`, `typing`, `typing`, `typing`, `typing`, `tempfile`, `winreg`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`AppPackageCollector`** | `global` | L6-L89 | /* Pre-indexes Start Menu shortcuts, AppDat */ |
| `method` | **`__init__`** | `AppPackageCollector` | L11-L21 | args: (self, dest_dir: str) |
| `function` | **`_index_shortcuts`** | `AppPackageCollector` | L23-L37 | args: (self) |
| `function` | **`_index_appdata`** | `AppPackageCollector` | L39-L57 | args: (self) |
| `function` | **`_index_uninstall_registry`** | `AppPackageCollector` | L59-L89 | args: (self) |
| `function` | **`find_app_start_menu_shortcuts`** | `global` | L91-L102 | args: (app_name: str, publisher: str, collector) |
| `function` | **`find_app_data_directories`** | `global` | L104-L115 | args: (app_name: str, publisher: str, collector) |
| `function` | **`export_universal_app_registry`** | `global` | L117-L178 | args: (app_name: str, publisher: str, dest_dir: str, collector) |
| `function` | **`import_registry_file`** | `global` | L180-L191 | args: (reg_filepath: str) -> bool |
| `function` | **`collect_full_app_package`** | `global` | L193-L214 | args: (app_name: str, publisher: str, install_location: str, temp_reg_dir: str) |

