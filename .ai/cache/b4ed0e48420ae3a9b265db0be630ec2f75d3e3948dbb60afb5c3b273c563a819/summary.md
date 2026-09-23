# File Contract Summary: `core/crypto_sign.py`
- **Lines**: 252
- **Symbols Count**: 14
- **Imports Count**: 15

### Key Dependencies (Imports)
`os`, `json`, `logging`, `typing`, `typing`, `typing`, `cryptography.hazmat.primitives.asymmetric.ed25519`, `cryptography.hazmat.primitives.asymmetric.ed25519`, `cryptography.hazmat.primitives.serialization`, `cryptography.hazmat.primitives.serialization`, `cryptography.hazmat.primitives.serialization`, `cryptography.hazmat.primitives.serialization`, `cryptography.hazmat.primitives.serialization`, `cryptography.hazmat.primitives.serialization`, `cryptography.exceptions`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`Ed25519Signer`** | `global` | L44-L185 | /* Ed25519 키 페어를 관리하고 Manifest에 대한 디지털 서명/검 */ |
| `method` | **`__init__`** | `Ed25519Signer` | L55-L62 | args: (self, repo_dir: str) |
| `function` | **`ensure_key_pair`** | `Ed25519Signer` | L64-L79 | args: (self) -> None /* Ed25519 키 페어가 존재하는지 확인하고, 없으면 생성하여 저장. */ |
| `function` | **`_get_private_key_instance`** | `Ed25519Signer` | L81-L84 | args: (self) -> Ed25519PrivateKey |
| `function` | **`_load_private_key`** | `Ed25519Signer` | L86-L92 | args: (self) -> None |
| `function` | **`_save_private_key`** | `Ed25519Signer` | L94-L114 | args: (self, private_key: Ed25519PrivateKey) -> None |
| `function` | **`_load_public_key`** | `Ed25519Signer` | L116-L122 | args: (self) -> None |
| `function` | **`_save_public_key`** | `Ed25519Signer` | L124-L143 | args: (self, public_key: Ed25519PublicKey) -> None |
| `function` | **`_prepare_manifest_payload`** | `Ed25519Signer` | L145-L151 | args: (self, manifest) -> bytes |
| `function` | **`sign_manifest`** | `Ed25519Signer` | L153-L164 | args: (self, manifest) -> str |
| `function` | **`verify_manifest`** | `Ed25519Signer` | L166-L185 | args: (self, manifest) -> bool |
| `function` | **`verify_manifest_signature_ed25519`** | `global` | L188-L218 | args: (manifest, pub_key_path_or_bytes) -> bool /* 독립적인 Ed25519 서명 검증 함수. */ |
| `function` | **`sign_bytes_ed25519`** | `global` | L221-L232 | args: (data: bytes, priv_key_path_or_bytes) -> str /* 임의의 바이트 데이터에 대한 Ed25519 서명 생성 (hex 반환). */ |
| `function` | **`verify_bytes_ed25519`** | `global` | L235-L252 | args: (data: bytes, signature_hex: str, pub_key_path_or_bytes) -> bool /* 임의의 바이트 데이터에 대한 Ed25519 서명 검증. */ |

