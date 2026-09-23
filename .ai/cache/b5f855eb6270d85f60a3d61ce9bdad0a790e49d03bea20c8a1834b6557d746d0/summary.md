# File Contract Summary: `tests/test_sprint1_durable_queue.py`
- **Lines**: 219
- **Symbols Count**: 7
- **Imports Count**: 12

### Key Dependencies (Imports)
`os`, `sys`, `json`, `time`, `shutil`, `tempfile`, `unittest`, `core.replication_queue`, `core.snapshot`, `core.storage`, `core.worm`, `core.worm`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestSprint1DurableQueue`** | `global` | L29-L215 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestSprint1DurableQueue` | L31-L41 | args: (self) |
| `function` | **`tearDown`** | `TestSprint1DurableQueue` | L43-L55 | args: (self) |
| `function` | **`test_durable_queue_lifecycle`** | `TestSprint1DurableQueue` | L57-L97 | args: (self) /* 1. Durable Replication Queue 전체 생명주기 및 원 */ |
| `function` | **`test_crash_and_auto_resume`** | `TestSprint1DurableQueue` | L99-L144 | args: (self) /* 2. 전송 중 강제 중단(Crash) 모의 및 auto-resume 복구 */ |
| `function` | **`test_worm_prune_authorization_enforcement`** | `TestSprint1DurableQueue` | L146-L181 | args: (self) /* 3. WORM Prune 권한 분리: authorized=False 차단 */ |
| `function` | **`test_end_to_end_snapshot_with_durable_queue_and_worker`** | `TestSprint1DurableQueue` | L183-L215 | args: (self) /* 4. SnapshotEngine create_snapshot 연동 Dur */ |

