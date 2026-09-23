# File Contract Summary: `core/verify.py`
- **Lines**: 550
- **Symbols Count**: 13
- **Imports Count**: 17

### Key Dependencies (Imports)
`os`, `json`, `time`, `zlib`, `hashlib`, `random`, `typing`, `typing`, `typing`, `typing`, `typing`, `core.storage`, `core.storage`, `core.storage`, `core.storage`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`RestoreVerificationError`** | `global` | L22-L24 | extends: Exception /* 자동 복원 검증 실패 시 발생하는 커스텀 예외 (Crash-Consist */ |
| `function` | **`generate_manifest_signature`** | `global` | L27-L43 | args: (entries) -> str /* 전체 파일 엔트리의 sha256들을 정렬 결합하여 최종 SHA-256 서 */ |
| `function` | **`verify_manifest_signature`** | `global` | L46-L54 | args: (manifest) -> bool /* manifest의 manifest_signature와 엔트리들로부터 재계 */ |
| `class` | **`IntegrityVerifier`** | `global` | L57-L549 | /* 스냅샷 및 블롭 저장소의 물리적 무결성을 검증하는 엔진 */ |
| `method` | **`__init__`** | `IntegrityVerifier` | L60-L63 | args: (self, repo_dir: str, crypto_engine) |
| `function` | **`verify_blob`** | `IntegrityVerifier` | L65-L119 | args: (self, sha256_hash: str) /* 단일 블롭의 압축 해제 및 SHA-256 일치 여부를 검증 (v1 암호화 */ |
| `function` | **`verify_snapshot`** | `IntegrityVerifier` | L121-L185 | args: (self, snapshot_manifest, sample_ratio: float, max_samples: int) /* 스냅샷 내 블롭들의 물리적 무결성 검증. */ |
| `function` | **`_decompress_and_hash_blob`** | `IntegrityVerifier` | L187-L227 | args: (self, blob_path: str) /* 블롭 파일을 스트리밍 압축 해제하며 크기와 SHA-256을 실시간 계산. */ |
| `function` | **`_has_special_chars`** | `IntegrityVerifier` | L229-L238 | args: (self, path: str) -> bool /* 경로에 한글, 공백, 유니코드 문자가 포함되어 있는지 검사. */ |
| `function` | **`verify_restore_sampling`** | `IntegrityVerifier` | L240-L405 | args: (self, snapshot_manifest, sample_count: int, self_heal: bool) /* 🔴 Automated Restore Verification (자동 복원  */ |
| `function` | **`_add_sample`** | `IntegrityVerifier::verify_restore_sampling` | L293-L302 | args: (pool, max_count: int) |
| `function` | **`audit_entire_repository`** | `IntegrityVerifier` | L407-L549 | args: (self, progress_callback) /* 저장소 전체에 대한 심층 무결성 전수 검증 (Deep Scan & Bit */ |
| `function` | **`_report`** | `IntegrityVerifier::audit_entire_repository` | L434-L442 | args: (msg: str) |

