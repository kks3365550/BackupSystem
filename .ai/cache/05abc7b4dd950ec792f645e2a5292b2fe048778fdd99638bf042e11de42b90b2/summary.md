# File Contract Summary: `core/worm.py`
- **Lines**: 185
- **Symbols Count**: 11
- **Imports Count**: 7

### Key Dependencies (Imports)
`os`, `sys`, `stat`, `logging`, `subprocess`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`WORMAuthorizationError`** | `global` | L23-L25 | extends: PermissionError /* Raised when an unauthorized process atte */ |
| `class` | **`WORMManager`** | `global` | L28-L173 | /* 저장소 파일 및 디렉토리에 대해 OS 및 파일시스템 수준의 WORM 보호 */ |
| `method` | **`__init__`** | `WORMManager` | L34-L35 | args: (self) |
| `function` | **`_run_icacls`** | `WORMManager` | L37-L59 | args: (self, target_path: str, arguments: list) -> bool |
| `function` | **`protect_file`** | `WORMManager` | L61-L87 | args: (self, filepath: str, use_ntfs_acl: bool) -> bool /* 파일을 수정/삭제할 수 없도록 WORM 보호를 적용합니다. */ |
| `function` | **`unprotect_file`** | `WORMManager` | L89-L116 | args: (self, filepath: str, authorized: bool) -> bool /* 정당한 삭제나 정리를 위해 WORM 보호를 해제합니다. */ |
| `function` | **`protect_directory`** | `WORMManager` | L118-L127 | args: (self, dirpath: str) -> bool /* 디렉토리 내 파일 삭제(Delete Child)를 거부하는 WORM AC */ |
| `function` | **`unprotect_directory`** | `WORMManager` | L129-L142 | args: (self, dirpath: str, authorized: bool) -> bool /* 디렉토리의 Delete Child 거부 ACL을 해제합니다. */ |
| `function` | **`protect_repository`** | `WORMManager` | L144-L173 | args: (self, repo_dir: str, protect_dirs: bool) /* 저장소 내 모든 스냅샷 매니페스트 및 블롭 디렉토리에 대해 일괄 WORM */ |
| `function` | **`lock_file_immutable`** | `global` | L179-L181 | args: (filepath: str, use_ntfs_acl: bool) -> bool /* 하위 호환성을 지원하는 WORM 잠금 함수 */ |
| `function` | **`unlock_file_writable`** | `global` | L183-L185 | args: (filepath: str, authorized: bool) -> bool /* 하위 호환성을 지원하는 WORM 해제 함수 (명시적 권한 검증) */ |

