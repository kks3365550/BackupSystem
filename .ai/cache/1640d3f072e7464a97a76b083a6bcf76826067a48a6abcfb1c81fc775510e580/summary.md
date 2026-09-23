# File Contract Summary: `tools/release.py`
- **Lines**: 455
- **Symbols Count**: 9
- **Imports Count**: 14

### Key Dependencies (Imports)
`os`, `sys`, `re`, `io`, `time`, `base64`, `zipfile`, `argparse`, `subprocess`, `urllib.request`, `json`, `core.crypto_sign`, `time`, `socket`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`get_current_version`** | `global` | L27-L31 |  |
| `function` | **`bump_version`** | `global` | L33-L48 | args: (current: str, bump_type: str) -> str |
| `function` | **`update_source_versions`** | `global` | L50-L82 | args: (new_ver: str) |
| `function` | **`run_git_release`** | `global` | L84-L94 | args: (version: str, message: str) |
| `function` | **`sync_install_directories`** | `global` | L96-L156 |  |
| `function` | **`build_self_extracting_updater`** | `global` | L158-L310 | args: (version: str) |
| `function` | **`remote_deploy_if_online`** | `global` | L312-L352 | args: (remote_ip: str, bat_path: str, sig_hex: str, raw_bytes: bytes) |
| `function` | **`restart_local_server`** | `global` | L354-L417 | /* 로컬 백업 서버(pythonw run.py)를 Kill 후 start_s */ |
| `function` | **`main`** | `global` | L419-L452 |  |

