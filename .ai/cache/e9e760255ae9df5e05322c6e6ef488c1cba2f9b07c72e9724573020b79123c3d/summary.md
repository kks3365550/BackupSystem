# File Contract Summary: `core/lock.py`
- **Lines**: 192
- **Symbols Count**: 10
- **Imports Count**: 12

### Key Dependencies (Imports)
`os`, `sys`, `time`, `json`, `socket`, `datetime`, `typing`, `typing`, `typing`, `msvcrt`, `psutil`, `ctypes`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`BackupAlreadyRunningError`** | `global` | L30-L34 | extends: Exception /* 이미 다른 백업 프로세스가 실행 중일 때 발생하는 예외 */ |
| `method` | **`__init__`** | `BackupAlreadyRunningError` | L32-L34 | args: (self, message: str, lock_info) |
| `class` | **`BackupLock`** | `global` | L37-L192 | /* 저장소(repo_dir) 레벨의 상호 배제 백업 락. */ |
| `method` | **`__init__`** | `BackupLock` | L45-L51 | args: (self, repo_dir: str, timeout_sec: float, process_desc: str) |
| `function` | **`_is_pid_alive`** | `BackupLock` | L53-L74 | args: (self, pid: int) -> bool /* 해당 PID를 가진 프로세스가 실제로 시스템에 살아있는지 검사 */ |
| `function` | **`_read_lock_info`** | `BackupLock` | L76-L84 | args: (self) /* 기존 락 파일의 메타데이터 조회 */ |
| `function` | **`acquire`** | `BackupLock` | L86-L158 | args: (self) -> bool /* 락 획득 시도. */ |
| `function` | **`release`** | `BackupLock` | L160-L185 | args: (self) /* 락 해제 및 락 파일 정리 */ |
| `function` | **`__enter__`** | `BackupLock` | L187-L189 | args: (self) |
| `function` | **`__exit__`** | `BackupLock` | L191-L192 | args: (self, exc_type, exc_val, exc_tb) |

