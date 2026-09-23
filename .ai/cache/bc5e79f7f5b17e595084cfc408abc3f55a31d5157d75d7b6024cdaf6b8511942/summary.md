# File Contract Summary: `tests/test_v239_verification.py`
- **Lines**: 143
- **Symbols Count**: 8
- **Imports Count**: 14

### Key Dependencies (Imports)
`os`, `shutil`, `tempfile`, `unittest`, `unittest.mock`, `core.vss_manager`, `core.vss_manager`, `core.verify`, `core.verify`, `core.verify`, `core.verify`, `core.snapshot`, `core.storage`, `core.storage`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestV239Verification`** | `global` | L25-L139 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestV239Verification` | L26-L44 | args: (self) |
| `function` | **`tearDown`** | `TestV239Verification` | L46-L53 | args: (self) |
| `function` | **`test_vss_strict_mode_blocks_unauthorized_backup`** | `TestV239Verification` | L55-L61 | args: (self) /* VSS Strict 모드: 관리자 권한 미부여 시 Silent Fallb */ |
| `function` | **`test_vss_optional_mode_allows_fallback`** | `TestV239Verification` | L63-L68 | args: (self) /* VSS Optional 모드: 관리자 권한 미부여 시 일반 직접 읽기 모 */ |
| `function` | **`test_manifest_signature_and_tamper_detection`** | `TestV239Verification` | L70-L90 | args: (self) /* Manifest 서명 생성 및 위변조 탐지 검증 */ |
| `function` | **`test_automated_restore_verification_pipeline`** | `TestV239Verification` | L92-L113 | args: (self) /* 백업 생성 시 Automated Restore Verification 및 */ |
| `function` | **`test_restore_verification_detects_corrupted_blob`** | `TestV239Verification` | L115-L139 | args: (self) /* 블롭 파일이 손상되었을 때 verify_restore_sampling이  */ |

