## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]**
*   **암호화 모듈 부재 (`core/crypto.py`)**: 백업 시스템의 핵심 보안 모듈이 파일 시스템에서 **존재하지 않거나** 경로 오류로 인해 로드되지 않는 상태입니다. 이는 백업 데이터가 평문으로 저장되거나, 무결성 검증이 불가능해져 **기밀성(Confidentiality)과 무결성(Integrity)이 완전히 무너진 상태**입니다.
*   **자가 업데이트(Self-Update) 실패 시 서비스 영구 중단**: `app.py`의 자가 업데이트 로직에서 `tar` 명령 실패 시 `os._exit(0)`을 호출하여 프로세스를 강제 종료합니다. 재시작 로직이 부재하거나 실패할 경우 **백업 서비스가 영구적으로 다운**되며, 재해 복구(DR) 능력이 상실됩니다.
*   **하드코딩된 Firebase 프로젝트 ID**: `lifespan` 초기화 로직에 Firebase 프로젝트 ID(`sunhang-772e5`)가 하드코딩되어 있습니다. 이는 보안 취약점(정보 노출)이자, 환경 변경 시 배포가 불가능한 **유지보수 리스크**를 초래합니다.

**[BUG]**
*   **`get_disk_free_gb`의 Fail-Open 결함**: 디스크 공간 조회 예외 발생 시 `999.0` GB를 반환하여 **Fail-Open** 동작을 유도합니다. 이는 디스크 공간 부족으로 인한 백업 실패를 방지하기 위한 Fail-Closed 전략(`verify_disk_space_or_fail`)과 상충되며, **부분 백업(Partial Backup)이나 기존 스냅샷 삭제**라는 치명적인 사이드 이펙트를 유발할 수 있습니다.
*   **`_find_snapshot_repo` 및 `active_repo` 선택 로직의 취약성**: 복원/검증/모니터링 시 `profiles[0]` 또는 첫 번째 프로필을 무조건적으로 활성 저장소로 가정합니다. 다중 프로필 환경에서 **잘못된 저장소에서 복원을 시도하거나, 잘못된 디스크 용량을 모니터링**하여 거짓 안심(False Sense of Security)을 유발합니다.
*   **`gc.collect()`의 불필요한 오버헤드**: 백업 작업 중 `manifest` 삭제 후 `gc.collect()`를 명시적으로 호출하여 전체 힙을 스캔합니다. 대용량 백업 시 **CPU 사용률 급증 및 백업 속도 저하**를 유발하는 성능 병목입니다.

**[RISK]**
*   **전역 상태(`current_task`) 경쟁 조건**: `current_task` 전역 변수에 대한 접근이 `task_lock`으로 보호되지만, `_background_custom_backup_task`와 `_background_backup_task`가 동시에 실행되지 않도록 하는 **409 Conflict 체크 로직의 경계 조건**이 명확하지 않아, 동시 요청 시 상태 불일치(Race Condition)가 발생할 수 있습니다.
*   **Windows `tar` 명령 의존성**: 자가 업데이트 시 Windows 기본 `tar` 명령에 의존합니다. 구형 Windows나 특정 보안 정책 환경에서 `tar`가 차단되거나 zip 형식 지원이 불안정할 경우 **업데이트 파이프라인이 실패**합니다.
*   **Firebase/카카오톡 외부 의존성**: 백업 완료 후 알림 및 상태 동기화를 위해 외부 API를 호출합니다. 네트워크 장애 시 **백업 작업 자체가 실패로 처리되거나** 상태가 동기화되지 않아 DR 체계의 신뢰성이 떨어집니다.

**[ACTION]**
1.  **`core/crypto.py` 구현/복구**: AES-256-GCM 암호화 및 SHA-256 무결성 검증 로직을 즉시 구현하거나, 기존 암호화 모듈의 경로를 수정하여 로드되도록 해야 합니다.
2.  **자가 업데이트 로직 재설계**: `tar` 명령 의존성을 제거하고 Python 내장 `zipfile` 모듈을 사용하여 안전한 압축 해제를 구현하세요. `os._exit(0)` 대신 서비스 재시작을 위한 Graceful Shutdown 및 재시작 로직을 추가하세요.
3.  **디스크 공간 검증 로직 수정**: `get_disk_free_gb`의 예외 처리를 `0.0` 또는 `None`으로 변경하고, `verify_disk_space_or_fail`에서 이를 Fail-Closed로 처리하도록 수정하여 **부분 백업 방지**를 보장하세요.
4.  **활성 저장소 식별 로직 개선**: `profiles[0]` 대신 **최근 백업이 발생한 프로필** 또는 **사용자가 명시적으로 선택한 프로필**의 `repo_dir`를 동적으로 식별하는 로직을 구현하세요.
5.  **하드코딩 제거**: Firebase 프로젝트 ID, 마스터 서버 URL 등을 `ConfigManager` 또는 환경 변수(Environment Variable)를 통해 동적으로 로드하도록 수정하세요.

**[DECISION REQUIRED]**
*   **암호화 모듈의 존재 여부 확인**: `core/crypto.py`가 실제로 존재하는지, 아니면 다른 이름(예: `security.py`, `encryption.py`)으로 저장되어 있는지 확인해야 합니다. 만약 존재하지 않는다면, **암호화 없는 백업 시스템은 보안 표준을 충족하지 못하므로 배포를 보류**해야 합니다.
*   **자가 업데이트 전략 승인**: `tar` 명령 의존성을 제거하고 Python 내장 모듈로 대체하는 수정 사항을 승인해야 합니다. 이는 시스템의 **자율적 유지보수 능력**을 보장하는 핵심 의사결정입니다.
*   **Fail-Closed vs Fail-Open 정책 결정**: 디스크 공간 부족 시 **백업 중단(Fail-Closed)**을 우선시할지, **부분 백업 허용(Fail-Open)**을 우선시할지 명확한 정책을 결정해야 합니다. 현재 코드는 두 전략이 혼재되어 있어 **일관성 없는 동작**을 유발합니다.

## PART 2. [COMPREHENSIVE AUDIT & ARCHITECTURE REPORT]

### 1. 시스템 개요 및 아키텍처
*   **버전**: 2.9.3 (패치 릴리스, 안정성 개선 추정)
*   **코어 아키텍처**:
    *   **BlobStorage (Content-Addressable Storage)**: SHA-256 해시 기반의 분산 저장 구조. 256개 Hex Prefix 디렉토리(00~ff)를 사전 생성하여 Windows NTFS의 대규모 파일 시스템 콜을 최적화.
    *   **Deduplication & Compression**: Zstandard(zstd) 우선, zlib 폴백. Small File(<=16MB)은 RAM에서 전체 처리하여 I/O 최소화, Large File(>16MB)은 4MB Chunk 스트리밍.
    *   **Atomic Write & WORM Lock**: 임시 파일 작성 후 `os.replace`로 원자적 교체, 저장 완료 후 파일 불변성(WORM) 보장.
    *   **Web Interface (FastAPI)**: Jinja2 템플릿 기반 UI, REST API, 실시간 상태 모니터링(CPU, RAM, Disk), 인증(Middleware), 세션 관리(Cookie/Bearer).
    *   **DR (Disaster Recovery)**: 오프사이트 복제 큐(Replication Queue), Firebase 클라우드 동기화, Windows 시스템 이미지(Bare-Metal) 백업, 자가 업데이트(Self-Update).

### 2. 청크별 세부 분석 종합

#### [청크 1: VERSION]
*   **역할**: 버전 식별자 (2.9.3).
*   **평가**: 단순 메타데이터. 보안/DR 로직과 무관.

#### [청크 2: core/backup.py]
*   **상태**: **파일 부재**.
*   **영향**: 백업 실행 로직의 핵심 모듈이 누락되어 시스템의 기본 기능이 작동하지 않을 수 있음.

#### [청크 3-4: storage.py]
*   **장점**:
    *   **성능 최적화**: 256개 Hex Prefix 사전 생성, 인메모리 캐시(`_blob_cache`), Small File RAM 처리.
    *   **안전성**: Atomic Write, WORM Lock, Fail-Closed 디스크 공간 검증.
    *   **Hybrid Format Detection**: Magic Number 기반 Zstd/Zlib/Encrypted 자동 감지.
*   **한계점**:
    *   `get_disk_free_gb`의 Fail-Open 결함 (예외 시 999.0 GB 반환).
    *   `prune_unreferenced_blobs`의 DB 메타데이터 동기화 지연 가능성.

#### [청크 5: core/crypto.py]
*   **상태**: **파일 부재**.
*   **영향**: **치명적 보안 결함**. 암호화 및 무결성 검증 기능 비활성화.

#### [청크 6-11: app.py]
*   **장점**:
    *   **완벽한 API 설계**: FastAPI 기반 REST API, Pydantic 모델 검증, 비동기 작업 처리(BackgroundTasks).
    *   **실시간 모니터링**: CPU/메모리/디스크 사용률 샘플링, 실시간 경보 시스템.
    *   **DR 체계**: 오프사이트 복제 큐, Firebase 동기화, Windows Task Scheduler 연동, 시스템 이미지 백업.
    *   **보안 자가 업데이트**: Ed25519 서명 검증, Zip-Slip 방지.
*   **한계점/버그**:
    *   **하드코딩**: Firebase 프로젝트 ID, 마스터 서버 URL.
    *   **자가 업데이트**: `tar` 명령 의존성, `os._exit(0)`으로 인한 서비스 영구 중단 위험.
    *   **활성 저장소 식별**: `profiles[0]` 무조건적 선택으로 인한 잘못된 저장소 참조.
    *   **성능**: `gc.collect()`의 불필요한 오버헤드.
    *   **경쟁 조건**: `current_task` 전역 변수의 동시 접근 시 상태 불일치 가능성.

### 3. 최종 평가 및 개선 로드맵

| 영역 | 현재 상태 | 개선 우선순위 |
| :--- | :--- | :--- |
| **보안** | **비보안** (암호화 모듈 부재, 하드코딩) | **P0 (즉시)** |
| **안정성** | **불안정** (자가 업데이트 실패 시 서비스 중단, Fail-Open 디스크 검증) | **P0 (즉시)** |
| **성능** | **양호** (BlobStorage 최적화, RAM 캐시) | P2 (개선) |
| **DR** | **부분적** (Firebase/복제 큐 존재, 하지만 암호화 부재로 신뢰성 저하) | P1 (단기) |
| **유지보수** | **저** (하드코딩, 파일 부재) | P1 (단기) |

**결론**: 현재 백업 시스템은 **아키텍처적으로 우수**하지만, **보안 및 안정성 측면에서 치명적인 결함**을 가지고 있습니다. `core/crypto.py`의 부재와 자가 업데이트 로직의 취약점을 해결하기 전에는 **프로덕션 배포를 보류**해야 합니다.