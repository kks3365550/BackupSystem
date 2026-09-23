# File Contract Summary: `tests/test_disaster_scenarios.py`
- **Lines**: 240
- **Symbols Count**: 8
- **Imports Count**: 11

### Key Dependencies (Imports)
`os`, `shutil`, `tempfile`, `unittest`, `core.snapshot`, `core.restore`, `core.storage`, `core.storage`, `core.crypto_sign`, `core.crypto_sign`, `core.replication`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestDisasterScenarios`** | `global` | L23-L236 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestDisasterScenarios` | L24-L50 | args: (self) |
| `function` | **`tearDown`** | `TestDisasterScenarios` | L52-L59 | args: (self) |
| `function` | **`test_ed25519_signature_and_adversarial_tampering`** | `TestDisasterScenarios` | L61-L89 | args: (self) /* Ed25519 비대칭키 서명 생성 및 위조 시 100% 탐지 검증 */ |
| `function` | **`test_offsite_cas_blob_replication_incremental`** | `TestDisasterScenarios` | L91-L137 | args: (self) /* 오프사이트 CAS 증분 복제: 신규 블롭만 전송되고 원격지에서 정상 복원 */ |
| `function` | **`test_dr_scenario_meta_db_lost`** | `TestDisasterScenarios` | L139-L165 | args: (self) /* DR 시나리오 1: 메타데이터 DB 및 레포 설정이 완전 증발해도 스냅샷 */ |
| `function` | **`test_dr_scenario_corrupted_blob_isolation`** | `TestDisasterScenarios` | L167-L202 | args: (self) /* DR 시나리오 2: 특정 블롭 1개가 물리적으로 깨져도, 나머지 4개 파 */ |
| `function` | **`test_dr_scenario_manifest_corruption_rollback`** | `TestDisasterScenarios` | L204-L236 | args: (self) /* DR 시나리오 3: 최신 manifest가 손상되었을 때 직전 스냅샷으로 */ |

