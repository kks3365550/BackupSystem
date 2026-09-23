# File Contract Summary: `core/auth.py`
- **Lines**: 221
- **Symbols Count**: 14
- **Imports Count**: 9

### Key Dependencies (Imports)
`os`, `json`, `secrets`, `hashlib`, `threading`, `datetime`, `datetime`, `typing`, `typing`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`_get_auth_config_path`** | `global` | L28-L30 | -> str |
| `function` | **`_load_auth_config`** | `global` | L33-L57 | -> dict |
| `function` | **`_save_auth_config`** | `global` | L60-L66 | args: (config: dict) -> None |
| `function` | **`_hash_password`** | `global` | L69-L77 | args: (password: str, salt_hex: str) -> str |
| `function` | **`is_auth_configured`** | `global` | L80-L84 | -> bool /* 마스터 비밀번호가 설정되어 있는지 확인 */ |
| `function` | **`get_auth_status`** | `global` | L87-L99 | args: (client_ip) -> dict /* 인증 상태 요약 정보 반환 */ |
| `function` | **`setup_master_password`** | `global` | L102-L126 | args: (password: str, allow_localhost_bypass: bool) -> bool /* 최초 마스터 비밀번호 설정 */ |
| `function` | **`verify_master_password`** | `global` | L129-L140 | args: (password: str) -> bool /* 마스터 비밀번호 일치 여부 검증 */ |
| `function` | **`change_master_password`** | `global` | L143-L171 | args: (old_password: str, new_password: str) -> bool /* 마스터 비밀번호 변경 */ |
| `function` | **`set_localhost_bypass`** | `global` | L174-L179 | args: (enabled: bool) -> None /* 로컬 루프백 접속 시 인증 자동 우회 여부 설정 */ |
| `function` | **`create_session`** | `global` | L182-L190 | -> str /* 유효한 세션 토큰을 생성하고 저장 */ |
| `function` | **`validate_session`** | `global` | L193-L205 | args: (token) -> bool /* 세션 토큰의 유효성을 검사 */ |
| `function` | **`revoke_session`** | `global` | L208-L213 | args: (token) -> None /* 세션 토큰 폐기(로그아웃) */ |
| `function` | **`_cleanup_expired_sessions`** | `global` | L216-L221 | -> None /* 만료된 세션 정리 (내부용, _lock 보유 상태에서 호출) */ |

