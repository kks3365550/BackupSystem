# File Contract Summary: `core/notifier.py`
- **Lines**: 162
- **Symbols Count**: 5
- **Imports Count**: 7

### Key Dependencies (Imports)
`os`, `json`, `time`, `requests`, `typing`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`get_kakao_token_data`** | `global` | L11-L18 |  |
| `function` | **`save_kakao_token_data`** | `global` | L20-L23 | args: (token_data) |
| `function` | **`refresh_kakao_access_token`** | `global` | L25-L55 | args: (rest_api_key: str, refresh_token: str, client_secret) /* Refreshes the Kakao access token using t */ |
| `function` | **`send_kakao_message`** | `global` | L57-L122 | args: (text: str) -> bool /* Sends a message to the user's own KakaoT */ |
| `function` | **`notify_backup_result`** | `global` | L124-L162 | args: (manifest, error_msg, profile_name: str) /* Formats and broadcasts backup summary no */ |

