# File Contract Summary: `tests/test_p0_fail_closed.py`
- **Lines**: 133
- **Symbols Count**: 7
- **Imports Count**: 10

### Key Dependencies (Imports)
`os`, `shutil`, `tempfile`, `unittest`, `unittest.mock`, `core.storage`, `core.storage`, `core.storage`, `core.snapshot`, `core.retention`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestFailClosedDiskPolicy`** | `global` | L21-L129 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestFailClosedDiskPolicy` | L22-L32 | args: (self) |
| `function` | **`tearDown`** | `TestFailClosedDiskPolicy` | L34-L42 | args: (self) |
| `function` | **`test_verify_disk_space_or_fail_insufficient`** | `TestFailClosedDiskPolicy` | L44-L50 | args: (self) /* 여유 공간이 부족할 때 InsufficientDiskSpaceError  */ |
| `function` | **`test_verify_disk_space_or_fail_sufficient`** | `TestFailClosedDiskPolicy` | L52-L57 | args: (self) /* 여유 공간이 충분할 때 정상 통과 확인 */ |
| `function` | **`test_create_snapshot_fail_closed_preserves_existing_snapshots`** | `TestFailClosedDiskPolicy` | L59-L112 | args: (self) /* [가장 중요한 P0 테스트] */ |
| `function` | **`test_retention_manager_does_not_prune_due_to_disk_space`** | `TestFailClosedDiskPolicy` | L114-L129 | args: (self) /* 보존 관리자(RetentionManager)가 디스크 공간 부족으로 임의 */ |

