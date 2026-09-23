# File Contract Summary: `emergency_restore/python/zstandard/__init__.py`
- **Lines**: 217
- **Symbols Count**: 3
- **Imports Count**: 18

### Key Dependencies (Imports)
`__future__`, `__future__`, `builtins`, `io`, `os`, `platform`, `sys`, `collections.abc`, `typing`, `backend_c`, `backend_cffi`, `backend_c`, `backend_cffi`, `backend_c`, `backend_cffi`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`open`** | `global` | L97-L181 | args: (filename, mode, cctx, dctx) /* Create a file object with zstd (de)compr */ |
| `function` | **`compress`** | `global` | L184-L199 | args: (data: Buffer, level: int) -> bytes /* Compress source data using the zstd comp */ |
| `function` | **`decompress`** | `global` | L202-L217 | args: (data: Buffer, max_output_size: int) -> bytes /* Decompress a zstd frame into its origina */ |

