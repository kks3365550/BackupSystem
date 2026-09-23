# File Contract Summary: `tests/test_vss_manager.py`
- **Lines**: 86
- **Symbols Count**: 5
- **Imports Count**: 8

### Key Dependencies (Imports)
`os`, `unittest`, `unittest.mock`, `unittest.mock`, `core.vss_manager`, `core.vss_manager`, `core.vss_manager`, `core.vss_manager`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestVSSManager`** | `global` | L19-L82 | extends: unittest.TestCase |
| `method` | **`test_extract_drive_letter`** | `TestVSSManager` | L20-L29 | args: (self) |
| `function` | **`test_get_shadow_path_mapping`** | `TestVSSManager` | L31-L51 | args: (self) /* VSS 활성화 시 원본 경로가 Shadow Copy 장치 경로로 정확히  */ |
| `function` | **`test_fallback_when_not_admin`** | `TestVSSManager` | L53-L60 | args: (self) /* 관리자 권한이 없을 때 strict=False인 경우 예외 없이 직접 읽 */ |
| `function` | **`test_cleanup_on_exception`** | `TestVSSManager` | L62-L82 | args: (self) /* 컨텍스트 블록 내에서 예외가 발생하더라도 _delete_shadow가 반 */ |

