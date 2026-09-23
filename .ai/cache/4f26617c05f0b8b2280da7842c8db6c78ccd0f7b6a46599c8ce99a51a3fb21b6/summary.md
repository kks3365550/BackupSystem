# File Contract Summary: `core/crypto_at_rest.py`
- **Lines**: 321
- **Symbols Count**: 11
- **Imports Count**: 18

### Key Dependencies (Imports)
`os`, `json`, `secrets`, `hashlib`, `threading`, `typing`, `typing`, `typing`, `typing`, `pathlib`, `zstandard`, `cryptography.hazmat.primitives.ciphers.aead`, `cryptography.hazmat.primitives.kdf.scrypt`, `cryptography.exceptions`, `stat`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`StorageKeyDeriver`** | `global` | L58-L72 | /* Scrypt KDF 기반 스토리지 대칭키(Storage Key) 파생 및 */ |
| `method` | **`derive`** | `StorageKeyDeriver` | L62-L72 | args: (master_key_bytes: bytes, salt: bytes, n: int, r: int) -> bytes |
| `class` | **`CryptoAtRestEngine`** | `global` | L75-L321 | /* CAS Dedup 100% 보존 저장 데이터 암호화/복호화 엔진 */ |
| `method` | **`__init__`** | `CryptoAtRestEngine` | L80-L88 | args: (self, storage_key: bytes, kdf_metadata) |
| `function` | **`from_passphrase`** | `CryptoAtRestEngine` | L91-L126 | args: (cls, passphrase: str, repo_dir: str, create_if_missing: bool) -> CryptoAtRestEngine /* 패스프레이즈 및 저장소 메타데이터(keys/key_metadata.jso */ |
| `function` | **`from_key_file`** | `CryptoAtRestEngine` | L129-L151 | args: (cls, key_file_path: str, repo_dir: str) -> CryptoAtRestEngine /* 오프라인 백업 키 파일 또는 마스터 키 파일로부터 로드 */ |
| `function` | **`build_blob_aad`** | `CryptoAtRestEngine` | L154-L163 | args: (plaintext_sha256: str) -> bytes /* 블롭 암호화용 AAD (특정 snapshot_id에 바인딩하지 않음으로써 */ |
| `function` | **`encrypt_blob_data`** | `CryptoAtRestEngine` | L165-L187 | args: (self, plaintext_data: bytes, plaintext_sha256: str, compress_level: int) -> bytes /* 평문 데이터를 Zstd 압축 후 AES-256-GCM 암호화 */ |
| `function` | **`decrypt_blob_data`** | `CryptoAtRestEngine` | L189-L234 | args: (self, blob_bytes: bytes, expected_plaintext_sha256: str) -> bytes /* 블롭 바이트열을 복호화하고 Zstd 압축 해제하여 원본 평문 반환 */ |
| `function` | **`save_blob_atomic`** | `CryptoAtRestEngine` | L236-L306 | args: (self, repo_dir: str, plaintext_data: bytes, plaintext_sha256: str) /* CAS 원자적 저장 함수 (CAS Dedup 100% 보존 보장) */ |
| `function` | **`export_key_backup`** | `CryptoAtRestEngine` | L308-L321 | args: (self, backup_file_path: str, passphrase_hint: str) /* 키 분실 방지를 위한 오프라인 키 백업 파일 생성 (Chaos 22 대응 */ |

