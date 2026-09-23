# File Contract Summary: `core/replication_queue.py`
- **Lines**: 334
- **Symbols Count**: 18
- **Imports Count**: 9

### Key Dependencies (Imports)
`os`, `sqlite3`, `threading`, `time`, `typing`, `typing`, `typing`, `typing`, `core.replication`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`ReplicationQueueManager`** | `global` | L17-L334 | /* SQLite WAL 모드를 활용한 Durable 오프사이트 복제 큐 관리 */ |
| `method` | **`__init__`** | `ReplicationQueueManager` | L25-L41 | args: (self, db_path_or_repo_dir: str) |
| `function` | **`_get_connection`** | `ReplicationQueueManager` | L43-L49 | args: (self) |
| `function` | **`_init_db`** | `ReplicationQueueManager` | L51-L74 | args: (self) |
| `function` | **`enqueue`** | `ReplicationQueueManager` | L76-L113 | args: (self, snapshot_id: str, repo_dir: str, remote_repo_dir: str) -> int /* PENDING 상태로 큐에 등록. 이미 존재하는 경우 id를 반환하고 미 */ |
| `function` | **`get_status`** | `ReplicationQueueManager` | L115-L146 | args: (self, snapshot_id: str) /* 스냅샷의 현재 복제 상태를 조회합니다. */ |
| `function` | **`_update_state`** | `ReplicationQueueManager` | L148-L163 | args: (self, task_id: int, state: str, error_msg) |
| `function` | **`_increment_attempts`** | `ReplicationQueueManager` | L165-L173 | args: (self, task_id: int) |
| `function` | **`process_next_task`** | `ReplicationQueueManager` | L175-L212 | args: (self) -> bool /* 대기(PENDING) 또는 중단 복구(TRANSFERRING) 작업을 1 */ |
| `function` | **`_fetch_next_task`** | `ReplicationQueueManager` | L214-L239 | args: (self) |
| `function` | **`resume_all_interrupted`** | `ReplicationQueueManager` | L241-L254 | args: (self) -> int /* PC 비정상 종료(Power-off/Crash)로 중단된 모든 TRANS */ |
| `function` | **`start_background_worker`** | `ReplicationQueueManager` | L256-L270 | args: (self, poll_interval: float) /* 백그라운드 스레드로 큐를 감시하며 대기 작업을 순차 처리합니다. */ |
| `function` | **`stop_background_worker`** | `ReplicationQueueManager` | L272-L275 | args: (self, timeout: float) |
| `function` | **`_worker_loop`** | `ReplicationQueueManager` | L277-L286 | args: (self, poll_interval: float) |
| `function` | **`list_tasks`** | `ReplicationQueueManager` | L288-L317 | args: (self, limit: int) |
| `function` | **`close`** | `ReplicationQueueManager` | L319-L328 | args: (self) |
| `function` | **`__enter__`** | `ReplicationQueueManager` | L330-L331 | args: (self) |
| `function` | **`__exit__`** | `ReplicationQueueManager` | L333-L334 | args: (self, exc_type, exc_val, exc_tb) |

