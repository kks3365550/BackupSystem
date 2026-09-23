# File Contract Summary: `core/retention.py`
- **Lines**: 96
- **Symbols Count**: 3
- **Imports Count**: 8

### Key Dependencies (Imports)
`os`, `time`, `typing`, `typing`, `typing`, `typing`, `core.storage`, `core.snapshot`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`RetentionManager`** | `global` | L16-L96 | /* 스토리지 보존 주기 및 여유 공간을 관리하는 엔진 */ |
| `method` | **`__init__`** | `RetentionManager` | L19-L20 | args: (self, repo_dir: str) |
| `function` | **`apply_policy`** | `RetentionManager` | L22-L96 | args: (self, retention_count, retention_days, min_free_gb) /* 저장소에 보존 정책을 적용하여 만료된 스냅샷을 정리하고 고아 청크를 회수 */ |

