# File Contract Summary: `tests/test_replication_qos.py`
- **Lines**: 158
- **Symbols Count**: 10
- **Imports Count**: 10

### Key Dependencies (Imports)
`os`, `json`, `time`, `tempfile`, `unittest`, `typing`, `typing`, `typing`, `core.replication`, `core.replication`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `class` | **`TestTokenBucketLimiter`** | `global` | L17-L46 | extends: unittest.TestCase /* TokenBucketLimiter의 QoS 대역폭 제한 동작 테스트. */ |
| `method` | **`test_token_bucket_no_limit`** | `TestTokenBucketLimiter` | L20-L28 | args: (self) /* bandwidth=0일 때 consume()이 즉시 반환되어 지연이 없음 */ |
| `function` | **`test_token_bucket_throttling`** | `TestTokenBucketLimiter` | L30-L46 | args: (self) /* bandwidth=2MB/s일 때 토큰 고갈 후 2MB 소비에 최소 0. */ |
| `class` | **`TestReplicationManagerQoS`** | `global` | L49-L154 | extends: unittest.TestCase /* ReplicationManager의 QoS 및 진행률 콜백 동작 테스트. */ |
| `method` | **`setUp`** | `TestReplicationManagerQoS` | L52-L64 | args: (self) /* 테스트용 임시 디렉토리 구조 생성. */ |
| `function` | **`tearDown`** | `TestReplicationManagerQoS` | L66-L79 | args: (self) /* 임시 디렉토리 정리. */ |
| `function` | **`_create_test_blob`** | `TestReplicationManagerQoS` | L81-L87 | args: (self, blob_id: str, content: bytes) -> None |
| `function` | **`_create_test_snapshot`** | `TestReplicationManagerQoS` | L89-L98 | args: (self, snapshot_id: str, blob_ids) -> None |
| `function` | **`test_replication_with_progress_callback`** | `TestReplicationManagerQoS` | L100-L154 | args: (self) /* 대역폭 제한 하에서 스냅샷 복제 시 진행률 콜백 및 결과 검증. */ |
| `function` | **`mock_progress`** | `TestReplicationManagerQoS::test_replication_with_progress_callback` | L119-L120 | args: (info) |

