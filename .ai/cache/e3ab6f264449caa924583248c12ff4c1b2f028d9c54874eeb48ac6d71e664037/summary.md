# File Contract Summary: `tests/test_v241_features.py`
- **Lines**: 229
- **Symbols Count**: 8
- **Imports Count**: 14

### Key Dependencies (Imports)
`os`, `sys`, `json`, `time`, `shutil`, `hashlib`, `tempfile`, `unittest`, `core.worm`, `core.verify`, `core.verify`, `core.storage`, `core.snapshot`, `core.crypto_sign`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestV241Features`** | `global` | L32-L225 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestV241Features` | L34-L45 | args: (self) |
| `function` | **`tearDown`** | `TestV241Features` | L47-L60 | args: (self) |
| `function` | **`test_worm_manager_file_and_directory`** | `TestV241Features` | L62-L105 | args: (self) /* 1. WORMManager를 통한 파일 및 디렉토리 WORM 잠금/해제  */ |
| `function` | **`test_audit_entire_repository_healthy`** | `TestV241Features` | L107-L129 | args: (self) /* 2. 정상 스냅샷 생성 후 audit_entire_repository() */ |
| `function` | **`test_audit_entire_repository_detects_bit_rot`** | `TestV241Features` | L131-L159 | args: (self) /* 3. 블롭 파일 강제 바이트 변조(Bit Rot) 시 audit_enti */ |
| `function` | **`test_audit_entire_repository_detects_signature_tampering`** | `TestV241Features` | L161-L191 | args: (self) /* 4. 스냅샷 manifest 내용 위조 시 audit_entire_rep */ |
| `function` | **`test_snapshot_engine_with_worm_and_offsite_replication`** | `TestV241Features` | L193-L225 | args: (self) /* 5. SnapshotEngine WORM 보호 및 비동기 오프사이트 복제 */ |

