# File Contract Summary: `core/hasher.py`
- **Lines**: 30
- **Symbols Count**: 3
- **Imports Count**: 5

### Key Dependencies (Imports)
`hashlib`, `os`, `typing`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`calculate_sha256`** | `global` | L5-L11 | args: (filepath: str, block_size: int) -> str /* Calculate SHA-256 hash of a file efficie */ |
| `function` | **`calculate_bytes_sha256`** | `global` | L13-L15 | args: (data: bytes) -> str /* Calculate SHA-256 of byte array. */ |
| `function` | **`get_file_stat`** | `global` | L17-L30 | args: (filepath: str) /* Get file size and modified timestamp saf */ |

