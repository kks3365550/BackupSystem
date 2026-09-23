# File Contract Summary: `tests/test_encryption_chaos.py`
- **Lines**: 323
- **Symbols Count**: 16
- **Imports Count**: 19

### Key Dependencies (Imports)
`os`, `sys`, `json`, `shutil`, `tempfile`, `unittest`, `subprocess`, `hashlib`, `typing`, `typing`, `core.snapshot`, `core.crypto_at_rest`, `core.worm`, `disaster_recovery`, `disaster_recovery`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestEncryptionChaos`** | `global` | L30-L319 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestEncryptionChaos` | L31-L72 | args: (self) |
| `function` | **`tearDown`** | `TestEncryptionChaos` | L74-L92 | args: (self) |
| `function` | **`_handle_rm_error`** | `TestEncryptionChaos::tearDown` | L80-L90 | args: (func, path, exc_info) |
| `function` | **`test_11_encrypted_blob_bit_rot`** | `TestEncryptionChaos` | L97-L114 | args: (self) |
| `function` | **`test_12_encrypted_blob_missing`** | `TestEncryptionChaos` | L119-L131 | args: (self) |
| `function` | **`test_13_wrong_master_key`** | `TestEncryptionChaos` | L136-L142 | args: (self) |
| `function` | **`test_14_corrupted_encryption_metadata`** | `TestEncryptionChaos` | L147-L161 | args: (self) |
| `function` | **`test_15_nonce_corruption`** | `TestEncryptionChaos` | L166-L180 | args: (self) |
| `function` | **`test_16_encrypted_repo_relocation`** | `TestEncryptionChaos` | L185-L194 | args: (self) |
| `function` | **`test_17_db_cache_lost_encrypted_dr`** | `TestEncryptionChaos` | L199-L215 | args: (self) |
| `function` | **`test_18_standalone_dr_encrypted_cli`** | `TestEncryptionChaos` | L220-L242 | args: (self) |
| `function` | **`test_19_client_side_replication_only`** | `TestEncryptionChaos` | L247-L265 | args: (self) |
| `function` | **`test_20_key_unavailable_graceful_fail`** | `TestEncryptionChaos` | L270-L275 | args: (self) |
| `function` | **`test_21_encryption_key_loss`** | `TestEncryptionChaos` | L280-L292 | args: (self) |
| `function` | **`test_22_key_backup_restore`** | `TestEncryptionChaos` | L297-L319 | args: (self) |

