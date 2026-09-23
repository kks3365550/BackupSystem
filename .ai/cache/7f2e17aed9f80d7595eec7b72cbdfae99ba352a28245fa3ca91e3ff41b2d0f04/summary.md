# File Contract Summary: `tests/test_repository_chaos.py`
- **Lines**: 308
- **Symbols Count**: 14
- **Imports Count**: 21

### Key Dependencies (Imports)
`os`, `sys`, `json`, `shutil`, `tempfile`, `unittest`, `subprocess`, `pathlib`, `typing`, `typing`, `core.snapshot`, `core.crypto_sign`, `core.worm`, `disaster_recovery`, `disaster_recovery`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestRepositoryChaos`** | `global` | L33-L304 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestRepositoryChaos` | L34-L78 | args: (self) |
| `function` | **`tearDown`** | `TestRepositoryChaos` | L80-L98 | args: (self) |
| `function` | **`_handle_rm_error`** | `TestRepositoryChaos::tearDown` | L86-L96 | args: (func, path, exc_info) |
| `function` | **`test_01_manifest_single_deleted`** | `TestRepositoryChaos` | L103-L126 | args: (self) |
| `function` | **`test_02_manifest_corrupted_json`** | `TestRepositoryChaos` | L131-L144 | args: (self) |
| `function` | **`test_03_signature_forged`** | `TestRepositoryChaos` | L149-L163 | args: (self) |
| `function` | **`test_04_blob_bit_rot`** | `TestRepositoryChaos` | L168-L188 | args: (self) |
| `function` | **`test_05_blob_missing`** | `TestRepositoryChaos` | L193-L206 | args: (self) |
| `function` | **`test_06_orphan_blobs_injected`** | `TestRepositoryChaos` | L211-L222 | args: (self) |
| `function` | **`test_07_blob_shard_directory_deleted`** | `TestRepositoryChaos` | L227-L242 | args: (self) |
| `function` | **`test_08_repo_relocation`** | `TestRepositoryChaos` | L247-L258 | args: (self) |
| `function` | **`test_09_database_and_cache_lost`** | `TestRepositoryChaos` | L263-L277 | args: (self) |
| `function` | **`test_10_standalone_disaster_recovery_cli`** | `TestRepositoryChaos` | L282-L304 | args: (self) |

