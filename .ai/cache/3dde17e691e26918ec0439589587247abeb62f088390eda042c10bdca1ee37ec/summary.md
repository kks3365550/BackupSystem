# File Contract Summary: `tests/test_live_mutating_file.py`
- **Lines**: 52
- **Symbols Count**: 4
- **Imports Count**: 6

### Key Dependencies (Imports)
`os`, `tempfile`, `unittest`, `hashlib`, `core.snapshot`, `core.verify`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestLiveMutatingFile`** | `global` | L15-L48 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestLiveMutatingFile` | L16-L21 | args: (self) |
| `function` | **`tearDown`** | `TestLiveMutatingFile` | L23-L24 | args: (self) |
| `function` | **`test_live_mutating_file_records_actual_blob_size`** | `TestLiveMutatingFile` | L26-L48 | args: (self) /* 백업 도중 크기가 변하는 파일에 대해 매니페스트가 실제 블롭 크기를 기록 */ |

