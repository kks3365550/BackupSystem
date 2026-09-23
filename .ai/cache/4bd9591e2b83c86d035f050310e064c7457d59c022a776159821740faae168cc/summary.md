# File Contract Summary: `disaster_recovery.py`
- **Lines**: 649
- **Symbols Count**: 13
- **Imports Count**: 20

### Key Dependencies (Imports)
`os`, `sys`, `json`, `zlib`, `hashlib`, `time`, `glob`, `argparse`, `concurrent.futures`, `typing`, `typing`, `typing`, `typing`, `typing`, `zstandard`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`format_bytes`** | `global` | L45-L53 | args: (size: int) -> str |
| `function` | **`get_candidate_repositories`** | `global` | L56-L94 | /* 시스템 내 백업 저장소 후보 경로 자동 탐색 */ |
| `function` | **`_latest_snap_time`** | `get_candidate_repositories` | L85-L91 | args: (r: str) -> float |
| `function` | **`get_blob_path`** | `global` | L97-L102 | args: (repo_dir: str, sha256_hash: str) -> str /* 해시값에 해당하는 블롭 파일 경로 반환 */ |
| `function` | **`verify_ed25519_manifest`** | `global` | L105-L125 | args: (manifest, pubkey_path: str) /* Manifest의 Ed25519 전자서명 검증 */ |
| `function` | **`verify_manifest_fingerprint`** | `global` | L128-L148 | args: (manifest) /* Manifest 내부 파일 엔트리 기반 SHA-256 결합 지문(Fing */ |
| `function` | **`list_snapshots`** | `global` | L151-L196 | args: (repo_dir: str) /* 저장소 내 스냅샷 목록 로드 및 정렬 */ |
| `function` | **`extract_blob`** | `global` | L199-L279 | args: (blob_path: str, dest_path: str, expected_sha256: str, verify_hash: bool) -> bool /* 단일 블롭을 읽어 대상 파일로 복원 (v1 암호화 및 v0 평문 자동 판 */ |
| `function` | **`audit_repository`** | `global` | L282-L367 | args: (repo_dir: str) /* 저장소 내 모든 블롭(.blob)의 Bit-Rot 전수 감사 */ |
| `function` | **`check_blob`** | `audit_repository` | L298-L335 | args: (path: str) |
| `function` | **`restore_snapshot`** | `global` | L370-L533 | args: (repo_dir: str, snapshot_id: str, dest_dir, verify_hash: bool) /* 지정된 스냅샷 복원 실행 (v1 암호화 및 v0 평문 자동 지원) */ |
| `function` | **`process_entry`** | `restore_snapshot` | L467-L499 | args: (entry) |
| `function` | **`main`** | `global` | L536-L645 |  |

