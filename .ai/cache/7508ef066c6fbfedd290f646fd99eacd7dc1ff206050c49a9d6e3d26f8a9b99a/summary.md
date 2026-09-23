# File Contract Summary: `tests/test_crypto_at_rest.py`
- **Lines**: 170
- **Symbols Count**: 10
- **Imports Count**: 14

### Key Dependencies (Imports)
`os`, `shutil`, `tempfile`, `unittest`, `concurrent.futures`, `hashlib`, `zstandard`, `core.crypto_at_rest`, `core.crypto_at_rest`, `core.crypto_at_rest`, `core.crypto_at_rest`, `core.crypto_at_rest`, `core.crypto_at_rest`, `stat`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestCryptoAtRest`** | `global` | L25-L166 | extends: unittest.TestCase |
| `method` | **`setUp`** | `TestCryptoAtRest` | L26-L31 | args: (self) |
| `function` | **`tearDown`** | `TestCryptoAtRest` | L33-L41 | args: (self) |
| `function` | **`_onerror`** | `TestCryptoAtRest::tearDown` | L34-L40 | args: (func, path, exc_info) |
| `function` | **`test_01_cas_dedup_100_percent`** | `TestCryptoAtRest` | L43-L64 | args: (self) /* 동일 데이터 암호화 저장 시 단 1개의 블롭 파일만 생성되고 신규 쓰기가 */ |
| `function` | **`test_02_v0_v1_backward_compatibility`** | `TestCryptoAtRest` | L66-L97 | args: (self) /* v0 평문 블롭(Zstd)과 v1 암호화 블롭(ENC\x01)이 공존할  */ |
| `function` | **`test_03_storage_key_derivation_and_scrypt_metadata`** | `TestCryptoAtRest` | L99-L114 | args: (self) /* 동일 마스터키 + 메타데이터로부터 Storage Key가 100% 일치하 */ |
| `function` | **`test_04_concurrent_worker_same_blob_race`** | `TestCryptoAtRest` | L116-L143 | args: (self) /* 16개 워커 스레드가 동시에 동일한 블롭 저장을 시도할 때 충돌 없이 단 */ |
| `function` | **`worker`** | `TestCryptoAtRest::test_04_concurrent_worker_same_blob_race` | L122-L124 |  |
| `function` | **`test_05_tamper_evident_aad_and_nonce`** | `TestCryptoAtRest` | L145-L166 | args: (self) /* 암호문, Nonce, 또는 AAD 해시 중 1바이트라도 변조되면 복호화가 */ |

