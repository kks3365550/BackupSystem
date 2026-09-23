# File Contract Summary: `tests/test_web_auth_api.py`
- **Lines**: 94
- **Symbols Count**: 6
- **Imports Count**: 8

### Key Dependencies (Imports)
`os`, `shutil`, `tempfile`, `unittest`, `unittest.mock`, `starlette.testclient`, `core`, `web.app`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestWebAuthApi`** | `global` | L17-L90 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestWebAuthApi` | L18-L25 | args: (self) |
| `function` | **`tearDown`** | `TestWebAuthApi` | L27-L29 | args: (self) |
| `function` | **`test_status_unconfigured`** | `TestWebAuthApi` | L31-L36 | args: (self) |
| `function` | **`test_setup_and_login_flow`** | `TestWebAuthApi` | L38-L72 | args: (self) |
| `function` | **`test_localhost_bypass`** | `TestWebAuthApi` | L74-L90 | args: (self) |

