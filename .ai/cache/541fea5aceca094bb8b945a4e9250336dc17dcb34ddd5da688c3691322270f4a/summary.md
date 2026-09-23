# File Contract Summary: `core/vss_manager.py`
- **Lines**: 268
- **Symbols Count**: 18
- **Imports Count**: 10

### Key Dependencies (Imports)
`os`, `re`, `sys`, `ctypes`, `logging`, `subprocess`, `typing`, `typing`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`VSSRequiredError`** | `global` | L22-L24 | extends: Exception /* VSS strict mode에서 섀도 복사본 생성 실패 시 발생하는 예외 */ |
| `class` | **`VSSCreationError`** | `global` | L27-L29 | extends: Exception /* VSS 섀도 복사본 생성 실패 시 내부적으로 발생하는 예외. */ |
| `function` | **`is_admin`** | `global` | L32-L39 | -> bool /* 현재 프로세스가 Windows 관리자 권한으로 실행 중인지 확인. */ |
| `function` | **`extract_drive_letter`** | `global` | L42-L53 | args: (path: str) /* 경로에서 드라이브 문자(예: 'C:')를 추출. */ |
| `class` | **`ShadowCopyRecord`** | `global` | L56-L66 | /* 단일 드라이브에 대한 VSS 섀도 복사본 정보 레코드 */ |
| `method` | **`__init__`** | `ShadowCopyRecord` | L60-L63 | args: (self, drive: str, shadow_id: str, device_path: str) |
| `function` | **`__repr__`** | `ShadowCopyRecord` | L65-L66 | args: (self) -> str |
| `class` | **`VSSContext`** | `global` | L69-L268 | /* 백업 세션 동안 볼륨 섀도 복사본(VSS)을 생성하고 작업 완료/예외 시 */ |
| `method` | **`__init__`** | `VSSContext` | L80-L87 | args: (self, source_paths, enabled: bool, strict: bool) |
| `function` | **`__enter__`** | `VSSContext` | L89-L112 | args: (self) -> VSSContext |
| `function` | **`__exit__`** | `VSSContext` | L114-L116 | args: (self, exc_type, exc_val, exc_tb) |
| `function` | **`_setup`** | `VSSContext` | L118-L163 | args: (self) /* 백업 소스 경로들이 속한 모든 고유 볼륨에 대해 VSS 섀도 복사본 생성 */ |
| `function` | **`_run_cmd`** | `VSSContext` | L166-L186 | args: (cmd, timeout: int) /* subprocess 안전 실행 및 윈도우 인코딩 다중 디코딩 */ |
| `function` | **`decode_bytes`** | `VSSContext::_run_cmd` | L176-L182 | args: (b: bytes) -> str |
| `function` | **`_create_shadow`** | `VSSContext` | L189-L220 | args: (cls, drive: str) -> ShadowCopyRecord /* vssadmin create shadow /for=C: 를 호출하여 섀도 */ |
| `function` | **`_delete_shadow`** | `VSSContext` | L223-L231 | args: (cls, shadow_id: str) -> bool /* vssadmin delete shadows /shadow={id} /qu */ |
| `function` | **`cleanup`** | `VSSContext` | L233-L250 | args: (self) /* 생성된 모든 섀도 복사본을 100% 누수 없이 해제. */ |
| `function` | **`get_shadow_path`** | `VSSContext` | L252-L268 | args: (self, original_path: str) -> str /* 원본 파일 경로를 섀도 복사본 장치 경로로 매핑. */ |

