## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]:** 없음. `all_passed: true` 및 모든 `gate_checks`가 `true`로 확인되어 시스템 무결성 및 백업 검증 성공.
**[BUG]:** 없음. JSON 구조 및 데이터 일관성 오류 미발견.
**[RISK]:** 없음. `uv_cpython` 카운트(4,637개)가 정상 범위 내이며, `as_index_cache`가 0으로 확인되어 불필요한 캐시 제거 성공.
**[ACTION]:**
1. **확인 완료**: `uv_cpython` 관련 파일은 총 **4,637개** 포함됨.
2. **경로 통계**: 제공된 JSON에는 개별 파일 경로 목록이 없으므로, `cpython-3.11.11` vs `cpython-3.11`의 세부 버전 분리는 **이 파일만으로는 불가능**.
3. **추정**: `uv`의 표준 동작 방식에 따라 `cpython-3.11.11-windows-x86_64-none` (풀 버전)이 사용되었을 가능성이 높으나, 확증을 위해 원본 `manifest_path`(`D:\MyBackup_Repository\...`)의 상세 리스트나 `uv` 캐시 디렉터리 직접 확인 필요.
**[DECISION REQUIRED]:**
- **사용자 승인**: `phase_c_snapshot_manifest.json`은 요약만 포함하므로, 세부 버전 확인을 위해 원본 매니페스트 JSON 또는 `uv` 캐시 디렉터리(`~/.cache/uv`)의 `cpython` 폴더 구조를 추가 분석할지 여부 결정 필요.

---

## PART 2. [DETAILED ANALYSIS & STRUCTURE REPORT]

### 1. 파일 구조 및 메타데이터 분석
제공된 `phase_c_snapshot_manifest.json`은 백업 스냅샷의 **요약(manifest summary)** 파일입니다. 개별 파일 경로를 나열하지 않고, 카테고리별 집계 통계만 포함하고 있습니다.

- **스냅샷 ID**: `snap_20260926_092057_7461cd`
- **생성 시각**: 2026-09-26 09:22:47
- **총 파일 수**: 220,945개
- **총 용량**: 약 22.087 GB
- **검증 상태**: `all_passed: true` (모든 게이트 체크 통과)

### 2. `uv` 및 `cpython` 관련 통계
`breakdown` 필드에서 `uv_cpython` 항목을 확인합니다.

| 항목 | 값 | 설명 |
|------|-----|------|
| `uv_cpython` | **4,637** | `uv`가 관리하는 CPython 인터프리터 및 관련 라이브러리 파일 총 개수 |
| `hermes_venv` | 24,712 | Hermes 프로젝트의 가상환경 파일 |
| `hermes_node` | 104,877 | Node.js 의존성 파일 |
| `hermes_total` | 145,984 | Hermes 전체 파일 (venv + node + 기타) |
| `as_index_cache` | 0 | 불필요한 인덱스 캐시 제거 확인 |

### 3. `cpython-3.11.11` vs `cpython-3.11` 버전 확인
**결론: 제공된 JSON 파일만으로는 특정 버전(`3.11.11` 또는 `3.11`)의 파일 수를 분리하여 확인하는 것이 불가능합니다.**

#### 이유:
1. **요약 데이터 구조**: `phase_c_snapshot_manifest.json`은 `breakdown`에서 `uv_cpython`를 단일 카운트(4,637)로만 집계하고 있습니다.
2. **경로 부재**: 개별 파일 경로나 하위 디렉터리 구조가 이 JSON에 포함되어 있지 않습니다.
3. **`uv`의 동작 방식**:
   - `uv`는 일반적으로 풀 버전(예: `cpython-3.11.11-windows-x86_64-none`)을 캐시 디렉터리에 저장합니다.
   - `cpython-3.11-windows-x86_64-none`은 `uv`의 표준 네이밍 컨벤션이 아닙니다. `uv`는 마이너 버전까지 포함하는 풀 버전을 사용합니다.
   - 따라서 **`cpython-3.11.11-windows-x86_64-none`이 사용되었을 가능성이 매우 높습니다.**

### 4. 추가 확인을 위한 조치
정확한 버전별 파일 수를 확인하려면 다음 중 하나를 수행해야 합니다:

1. **원본 매니페스트 확인**:
   - `manifest_path`: `D:\MyBackup_Repository\snapshots\snap_20260926_092057_7461cd.json`
   - 이 파일에는 개별 파일 경로가 포함되어 있을 가능성이 높습니다.

2. **`uv` 캐시 디렉터리 직접 확인**:
   - Windows: `%USERPROFILE%\.cache\uv\` 또는 `C:\Users\kksjmj\.cache\uv\`
   - `cpython` 폴더 내 하위 디렉터리 이름을 확인하면 사용된 CPython 버전을 정확히 알 수 있습니다.

3. **`uv` 명령어 사용**:
   ```bash
   uv python list
   ```
   또는
   ```bash
   uv cache dir
   ```
   명령을 실행하여 현재 시스템에 설치된 CPython 버전을 확인합니다.

### 5. 최종 요약
- **`uv_cpython` 총 파일 수**: 4,637개
- **사용된 CPython 버전**: `cpython-3.11.11-windows-x86_64-none` (추정, `uv` 표준 네이밍 컨벤션 기반)
- **`cpython-3.11-windows-x86_64-none`**: `uv`의 표준 네이밍이 아니므로 사용되지 않았을 가능성이 높음
- **확증 필요**: 원본 매니페스트 또는 `uv` 캐시 디렉터리 확인 필요