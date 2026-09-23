# File Contract Summary: `core/replication.py`
- **Lines**: 368
- **Symbols Count**: 16
- **Imports Count**: 18

### Key Dependencies (Imports)
`os`, `json`, `time`, `shutil`, `threading`, `typing`, `typing`, `typing`, `typing`, `typing`, `concurrent.futures`, `concurrent.futures`, `core.storage`, `core.storage`, `core.storage`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TokenBucketLimiter`** | `global` | L28-L57 | /* QoS 대역폭 제한을 위한 토큰 버킷 알고리즘 (time.monotoni */ |
| `method` | **`__init__`** | `TokenBucketLimiter` | L33-L38 | args: (self, max_mb_per_sec: float) |
| `function` | **`consume`** | `TokenBucketLimiter` | L40-L57 | args: (self, num_bytes: int) |
| `class` | **`ReplicationManager`** | `global` | L60-L368 | /* 로컬 CAS 저장소의 블롭과 스냅샷을 오프사이트 원격 저장소로 증분 복제 */ |
| `method` | **`__init__`** | `ReplicationManager` | L68-L88 | args: (self, local_repo_dir: str, remote_repo_dir: str, bandwidth_limit_mb: float) |
| `function` | **`_ensure_remote_structure`** | `ReplicationManager` | L90-L96 | args: (self) /* 원격지에 필요한 디렉토리 구조 및 256개 접두사 디렉토리 생성. */ |
| `function` | **`_get_blob_rel_path`** | `ReplicationManager` | L98-L102 | args: (self, blob_id: str) -> str |
| `function` | **`_get_local_blob_path`** | `ReplicationManager` | L104-L105 | args: (self, blob_id: str) -> str |
| `function` | **`_get_remote_blob_path`** | `ReplicationManager` | L107-L108 | args: (self, blob_id: str) -> str |
| `function` | **`get_missing_blobs`** | `ReplicationManager` | L110-L120 | args: (self, target_blob_ids) /* 원격지에 아직 복제되지 않은 블롭 ID 목록 반환. */ |
| `function` | **`replicate_blob`** | `ReplicationManager` | L122-L160 | args: (self, blob_id: str) -> int /* 단일 블롭을 원격지로 원자적 복사 및 WORM 잠금. 복사된 바이트 수  */ |
| `function` | **`_load_snapshot_manifest`** | `ReplicationManager` | L162-L168 | args: (self, snapshot_id: str) |
| `function` | **`_extract_blob_ids_from_manifest`** | `ReplicationManager` | L170-L192 | args: (self, manifest) |
| `function` | **`_copy_snapshot_manifest`** | `ReplicationManager` | L194-L225 | args: (self, snapshot_id: str) -> bool /* 스냅샷 manifest.json을 원격지로 원자적 복사. */ |
| `function` | **`replicate_snapshot`** | `ReplicationManager` | L227-L323 | args: (self, snapshot_id: str, max_workers: int, progress_callback) /* 특정 스냅샷에 필요한 누락된 블롭들만 증분 복제하고 매니페스트 동기화 ( */ |
| `function` | **`replicate_all_missing`** | `ReplicationManager` | L325-L368 | args: (self, max_workers: int) /* 로컬 저장소의 모든 스냅샷과 블롭을 원격지로 증분 동기화. */ |

