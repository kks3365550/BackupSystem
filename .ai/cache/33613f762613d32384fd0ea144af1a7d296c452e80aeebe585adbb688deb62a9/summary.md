# File Contract Summary: `tests/test_self_healing.py`
- **Lines**: 131
- **Symbols Count**: 5
- **Imports Count**: 10

### Key Dependencies (Imports)
`os`, `json`, `stat`, `tempfile`, `unittest`, `hashlib`, `core.storage`, `core.storage`, `core.verify`, `core.verify`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestSelfHealing`** | `global` | L17-L127 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestSelfHealing` | L18-L26 | args: (self) |
| `function` | **`tearDown`** | `TestSelfHealing` | L28-L39 | args: (self) |
| `function` | **`test_self_healing_corrupted_blob_with_valid_source`** | `TestSelfHealing` | L41-L87 | args: (self) /* 원본 소스가 온전한 경우 손상된 블롭이 복원 검증 시 자동 자가 치유(S */ |
| `function` | **`test_self_healing_fails_when_source_missing`** | `TestSelfHealing` | L89-L127 | args: (self) /* 원본 소스가 없는 상태에서 블롭이 손상되었으면 정상적으로 RestoreV */ |

