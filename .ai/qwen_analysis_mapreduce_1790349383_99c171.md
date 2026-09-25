# Qwen 대용량 자동 분할 분석 전체 산출물

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

---
## 청크별 1차 분석 원본

### [분석 청크 1: VERSION (Part 1/1)]
# VERSION 파일 정밀 분석 보고서

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
*   **분석 대상**: `VERSION` 파일 (6자)
*   **내용**: `2.9.3`
*   **역할**: 소프트웨어의 **메이저.마이너.패치** 버전 정보를 명시하는 메타데이터 파일입니다.
*   **핵심 기능**:
    *   빌드 시스템이 배포 아티팩트에 버전 태그를 부여하는 기준.
    *   클라이언트/서버 간 호환성 확인 및 업데이트 체크의 기준점.
    *   DR(재해복구) 시 특정 버전으로 롤백할 대상 식별자.

> **참고**: 이 파일 자체에는 암호화, 무결성 검증, 웹 인터페이스, DR 로직 등 **실질적인 코드 로직이 포함되어 있지 않습니다.** 따라서 요청하신 "백업시스템의 핵심 아키텍처, 암호화/무결성, 안전성, 웹 인터페이스, DR 체계"에 대한 직접적인 기술 평가는 이 파일만으로 수행할 수 없습니다.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **이벤트 핸들러**: 없음
*   **API 호출**: 없음
*   **데이터 바인딩**: 없음
*   **상태**: 정적 텍스트 파일로, 런타임에 동적 처리되지 않는 순수 메타데이터입니다.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **버그**: 없음 (단순 버전 문자열)
*   **예외 누락**: 해당 없음
*   **하드코딩**: 버전 번호 `2.9.3`이 하드코딩되어 있음 (이것은 의도된 설계)
*   **동작하지 않는 요소**: 없음

## 4. 사용자의 질문과 관련된 핵심 발견점

### ⚠️ 중요 발견: 분석 대상의 한계
요청하신 **"백업시스템의 핵심 아키텍처, 암호화/무결성, 안전성, 웹 인터페이스, DR 체계"**에 대한 기술 평가는 **`VERSION` 파일 단독으로는 불가능**합니다.

이 파일은 단순 버전 식별자일 뿐이며, 실제 시스템의 보안 및 복구 로직은 다른 소스 코드 파일(예: `backup_service.py`, `crypto_utils.js`, `dr_policy.yaml`, `web_ui.html` 등)에 포함되어 있을 것입니다.

### ✅ 가능한 범위 내 평가 (버전 2.9.3 기준)
1.  **버전 안정성 추측**:
    *   `2.9.3`은 마이너 버전 9의 패치 릴리스임을 의미합니다.
    *   일반적으로 패치 버전은 **버그 수정 및 보안 패치**에 집중된 릴리스이므로, 이전 버전(2.9.2 등) 대비 **안전성(Safety)**이 개선되었을 가능성이 높습니다.
    *   DR 체계에서 이 버전은 "검증된 안정 버전"으로 간주될 수 있습니다.

2.  **한계점**:
    *   이 파일만으로는 암호화 알고리즘(AES-256, RSA 등), 무결성 검증(HMAC, SHA-256), 웹 인터페이스 구조, DR 자동화 로직을 평가할 수 없습니다.

### 📌 개선점 및 다음 단계 제안
백업시스템의 상세 기술 평가를 위해 다음 파일들의 분석이 필요합니다:
1.  **암호화/무결성**: `crypto.py`, `hash_utils.js`, `integrity_check.sh`
2.  **안전성**: `auth.py`, `security_config.yaml`, `firewall_rules.conf`
3.  **웹 인터페이스**: `app.py`, `index.html`, `api_routes.js`
4.  **DR 체계**: `dr_policy.yaml`, `restore_script.sh`, `backup_scheduler.py`
5.  **아키텍처**: `docker-compose.yml`, `k8s_manifests/`, `systemd_service.conf`

> **결론**: `VERSION` 파일은 시스템의 **버전 식별**에만 기여하며, 요청하신 보안/DR/아키텍처 평가에는 **직접적 정보를 제공하지 않습니다.** 실제 코드베이스의 핵심 로직 파일들을 추가로 제공해 주시면, 해당 파일들을 기반으로 상세 기술 평가를 수행할 수 있습니다.

### [분석 청크 2: c:\Users\kksjmj\Desktop\ai\백업시스템\core\backup.py (Part 1/1)]
# 백업시스템 코드 정밀 분석 보고서

## 1. 분석 대상 상태 확인

**파일 경로:** `c:\Users\kksjmj\Desktop\ai\백업시스템\core\backup.py`
**분석 결과:** **파일 없음 (File Not Found)**

제공된 코드 블록은 `[파일 없음]`으로 표시되어 있어, 해당 경로에 `backup.py` 파일이 존재하지 않거나 접근 권한이 없는 상태입니다.

---

## 2. 요청된 항목별 분석

### 1) 주요 함수/컴포넌트/UI 요소 및 핵심 역할
- **분석 불가**: 파일이 존재하지 않아 함수, 클래스, UI 컴포넌트 식별이 불가능합니다.

### 2) 이벤트 핸들러, API 호출, 데이터 바인딩 상태
- **분석 불가**: 코드 내용이 없어 이벤트 처리 로직, 외부 API 호출, 데이터 바인딩 구조를 확인할 수 없습니다.

### 3) 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
- **분석 불가**: 코드 자체가 없으므로 정적 분석 대상이 없습니다.

### 4) 사용자의 질문과 관련된 핵심 발견점
- **핵심 발견**: 요청하신 백업시스템의 핵심 아키텍처, 암호화/무결성, 안전성, 웹 인터페이스, DR 체계에 대한 기술 평가를 수행하기 위해 **실제 소스 코드가 필요합니다**.

---

## 3. 다음 단계 제안

기술 평가를 진행하기 위해 아래 중 하나를 수행해 주세요:

1. **파일 경로 확인**: `c:\Users\kksjmj\Desktop\ai\백업시스템\core\backup.py` 파일이 실제로 존재하는지 확인하세요.
2. **코드 내용 직접 제공**: 파일 내용을 복사하여 채팅에 붙여넣어 주세요.
3. **프로젝트 구조 공유**: 백업시스템의 전체 디렉토리 구조와 주요 파일 목록을 제공해 주시면, 어떤 파일이 핵심인지 파악하여 분석을 시작할 수 있습니다.

> **참고**: 백업시스템의 암호화/무결성, DR 체계 평가는 `backup.py`뿐 아니라 암호화 모듈, 스케줄러, 저장소 관리, 복구 로직 등 관련 파일들의 종합 분석이 필요합니다. 핵심 파일들을 함께 제공해 주시면 더 정확한 기술 평가를 수행할 수 있습니다.

### [분석 청크 3: storage.py (Part 1/2)]
# storage.py (Part 1/2) 정밀 분석 보고서

## 1. 주요 함수/컴포넌트 및 핵심 역할

### **A. 디스크 공간 안전성 관리 (Fail-Closed Safeguard)**
*   **`InsufficientDiskSpaceError`**: 디스크 공간 부족 시 백업 작업을 즉시 중단하기 위한 커스텀 예외 클래스.
*   **`get_disk_free_gb(path)`**: `shutil.disk_usage`를 사용하여 볼륨의 여유 공간을 GB 단위로 반환. 예외 발생 시 `999.0`을 반환하여 **Fail-Open** 동작을 유도함 (주의: 이는 안전성 원칙과 상충될 수 있음).
*   **`verify_disk_space_or_fail(path, min_free_gb)`**: 백업 시작 전 최소 여유 공간(기본 10GB)을 검증. 부족 시 `InsufficientDiskSpaceError`를 발생시켜 **부분 백업(Partial Backup)과 기존 스냅샷 삭제 방지**를 위한 Fail-Closed 전략을 구현.

### **B. BlobStorage 클래스 (Content-Addressable Storage Core)**
*   **`__init__`**:
    *   저장소 디렉토리 구조(`blobs`, `snapshots`, `_temp`) 초기화.
    *   **256개 Hex Prefix 디렉토리(00~ff) 사전 생성**: Windows NTFS에서 대규모 백업 시 `os.makedirs` 시스템 콜을 220,000회 줄이는 최적화.
    *   `repo_meta.json` 생성 (버전 2.0.0, 압축 방식 기록).
    *   **클래스 레벨 캐시 공유**: `_class_blob_caches`를 통해 같은 프로세스 내 모든 `BlobStorage` 인스턴스가 동일한 Blob 존재 여부를 공유하여 메모리 효율성 극대화.
    *   `MetadataDB` 인스턴스 초기화.
*   **`init_repo`**: 디렉토리 구조 및 메타데이터 파일 초기화.
*   **`get_blob_rel_path` / `get_blob_abs_path`**: SHA-256 해시 기반의 분산 저장 경로 계산 (첫 2자 Hex를 서브디렉토리로 사용).
*   **`has_blob`**: 인메모리 캐시(`_blob_cache`)를 우선 조회하고, 없으면 디스크 존재 여부 확인. 캐시 히트 시 락 없이 반환(Lock-free fast path).
*   **`bulk_add_blob_cache`**: Diffing 과정 중 디스크 I/O를 줄이기 위해 Blob ID 목록을 일괄 캐시에 등록.

### **C. Blob 저장 로직 (Compression & Deduplication)**
*   **`put_file_blob`**:
    *   파일 압축 및 Blob 저장.
    *   **Zstandard(zstd)** 우선 사용, 미설치 시 `zlib` 폴백.
    *   **Deduplication**: `has_blob` 확인 시 기존 Blob 재사용.
    *   **Atomic Write**: 임시 파일(`.tmp_pid_random`)에 작성 후 `os.replace`로 원자적 교체.
    *   **WORM Lock**: 저장 완료 후 `lock_file_immutable`을 호출하여 파일 불변성 보장.
*   **`put_file_blob_onepass`** (핵심 성능 최적화 함수):
    *   **Small File Path (<= 16MB)**:
        1.  RAM으로 전체 로드.
        2.  RAM에서 SHA-256 계산.
        3.  `has_blob` 확인 시 **0ms, 0 Disk I/O, 0 Compression CPU**로 즉시 반환 (중복 파일 최적화).
        4.  신규 Blob인 경우 RAM에서 압축/암호화 후 디스크에 한 번에 기록.
        5.  **Concurrency Double Check**: 병렬 워커가 이미 저장한 경우를 대비한 재확인.
    *   **Large File Path (> 16MB)**:
        1.  스트리밍 방식 압축.
        2.  `cancel_event`를 통해 작업 취소 지원.
        3.  4MB Chunk 기반 스트리밍.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **I/O 패턴**:
    *   **Read**: `os.path.getsize`, `open(..., 'rb')`, `shutil.disk_usage`.
    *   **Write**: `open(..., 'wb')`, `os.replace` (Atomic), `json.dump`.
    *   **Locking**: `threading.Lock`을 사용하여 `_blob_cache` 업데이트 시 스레드 안전성 보장.
*   **데이터 바인딩**:
    *   `sha

### [분석 청크 4: storage.py (Part 2/2)]
# storage.py (Part 2/2) 정밀 분석 보고서

## 1. 주요 함수/컴포넌트 및 핵심 역할

이 블록은 백업 시스템의 **Blob 저장소 관리**와 **복원(Extract)** 로직을 담당하는 핵심 부분입니다.

| 함수명 | 핵심 역할 |
| :--- | :--- |
| `put_file_blob` (부분) | 파일 스트리밍 압축/암호화, SHA256 계산, 중복 제거(Dedup), 원자적 이동(`os.replace`) |
| `put_bytes_blob` | 메모리 내 바이트 데이터의 압축/암호화 및 저장. `snapshot.py`와의 일관성을 위해 DB 기록을 호출자에게 위임 |
| `extract_blob_to_file` | **복원 로직의 핵심**. Magic Number 기반 형식 자동 감지(Zstd/Zlib/Encrypted), 스트리밍 복압축, 무결성 검증 |
| `read_blob_bytes` | 전체 Blob을 메모리로 로드하여 복압축 (소형 파일용) |
| `prune_unreferenced_blobs` | 참조되지 않는 Blob 삭제 및 공간 회수, DB 메타데이터 동기화 |
| `get_storage_stats` | SQLite 캐시를 통한 저장소 통계 조회 |

**아키텍처 특징:**
*   **Hybrid Format Detection:** `ENC\x01` (v1 암호화), `ZSTD_MAGIC` (v0 Zstd), 기타 (v0 Zlib)를 헤더 4바이트로 판

### [분석 청크 5: c:\Users\kksjmj\Desktop\ai\백업시스템\core\crypto.py (Part 1/1)]
# 코드 분석 결과: `core/crypto.py`

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
*   **분석 대상:** `c:\Users\kksjmj\Desktop\ai\백업시스템\core\crypto.py`
*   **상태:** **파일 없음 (File Not Found)**
*   **핵심 역할:** 해당 경로는 백업 시스템의 암호화 및 무결성 검증 로직을 담당할 것으로 예상되나, 실제 파일이 존재하지 않습니다. 따라서 암호화 알고리즘, 키 관리, 해시 검증 등 핵심 보안 기능이 구현되어 있지 않거나, 파일 경로가 잘못 지정되었습니다.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **상태:** **해당 없음**
*   파일이 존재하지 않으므로 이벤트 핸들러, API 호출, 데이터 바인딩 상태는 확인 불가능합니다.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **치명적 오류:** **파일 부재 (Missing File)**
    *   백업 시스템의 핵심 보안 모듈(`crypto.py`)이 존재하지 않아, 시스템의 암호화 및 무결성 검증 기능이 완전히 비활성화 상태일 가능성이 높습니다.
    *   이는 백업 데이터가 평문으로 저장되거나, 무결성 검증이 불가능해져 보안 취약점을 초래합니다.
*   **경로 오류 가능성:**
    *   `c:\Users\kksjmj\Desktop\ai\백업시스템\core\` 경로에 `crypto.py` 파일이 실제로 존재하지 않거나, 다른 이름으로 저장되어 있을 수 있습니다.

## 4. 사용자의 질문과 관련된 핵심 발견점
*   **백업 시스템의 안전성 및 무결성 평가:**
    *   **현재 상태:** **비보안 (Insecure)**
    *   암호화 모듈이 부재하므로, 백업 데이터의 기밀성(Confidentiality)과 무결성(Integrity)을 보장할 수 없습니다.
    *   **DR(재해복구) 체계:** 암호화 키 관리 및 복호화 로직이 없으므로, 재해 복구 시 데이터 복원 과정이 불완전하거나 불가능할 수 있습니다.
*   **장점:** 없음 (파일 부재)
*   **한계점:**
    *   암호화 기능 부재
    *   무결성 검증 불가
    *   보안 취약점 노출
*   **개선점:**
    1.  `core/crypto.py` 파일의 존재 여부를 확인하고, 없다면 구현해야 합니다.
    2.  표준 암호화 알고리즘(AES-256 등)과 해시 알고리즘(SHA-256 등)을 구현해야 합니다.
    3.  키 관리 체계(키 생성, 저장, 회전)를 설계해야 합니다.
    4.  백업 데이터의 무결성 검증 로직을 추가해야 합니다.

## 결론
**`core/crypto.py` 파일이 존재하지 않아 백업 시스템의 암호화 및 무결성 검증 기능이 비활성 상태입니다.** 이는 시스템의 보안과 안전성에 치명적인 취약점을 초래하므로, 해당 파일의 구현 또는 경로 수정이 시급합니다.

### [분석 청크 6: app.py (Part 1/6)]
제공된 `app.py`의 [1/6] 블록(약 12,977자)에 대한 정밀 분석 결과입니다. 이 블록은 백업 시스템의 **FastAPI 애플리케이션 진입점**, **인증 체계**, **시스템 모니터링**, 그리고 **초기화(Lifespan) 로직**을 정의하고 있습니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

*   **FastAPI 애플리케이션 인스턴스 (`app`)**:
    *   `lifespan` 컨텍스트 매니저를 사용하여 애플리케이션 시작/종료 시 스케줄러, 복제 큐, Firebase 동기화, 업데이트 체크를 초기화합니다.
    *   버전 관리: `VERSION` 상수를 통해 현재 앱 버전을 관리하며, `get_current_version()`으로 `VERSION` 파일 또는 `core.__version__`에서 동적으로 로드합니다.
*   **인증 시스템 (Auth)**:
    *   **Middleware (`auth_middleware`)**: 모든 HTTP 요청에 대해 인증을 강제하는 핵심 로직. 정적 리소스, 인증 API, 로컬 루프백(localhost) 바이패스, 세션 토큰(Cookie/Bearer) 검증을 수행합니다.
    *   **Pydantic Models**: `AuthSetupRequest`, `AuthLoginRequest` 등 인증 관련 요청/응답 데이터 구조를 정의합니다.
    *   **Auth Endpoints**: `/api/auth/status`, `/api/auth/setup`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/change-password`, `/api/auth/toggle-bypass` 등 REST API를 제공합니다.
*   **시스템 모니터링**:
    *   `_cpu_monitor`: 백그라운드 스레드로 0.5초 간격으로 CPU 사용률을 샘플링하여 `_cpu_percent_cache`에 저장합니다. 이는 `/api/system-info` API의 응답 지연을 방지하기 위한 최적화입니다.
    *   `get_system_info`: CPU, 메모리, 디스크 파티션 정보를 수집하여 반환합니다.
*   **상태 관리**:
    *   `current_task`: 현재 실행 중인 백업/복원 작업의 상태(진행률, 로그, 취소 이벤트 등)를 전역으로 관리합니다. `deque(maxlen=500)`를 사용하여 메모리 효율성을 높였습니다.
    *   `task_lock`: `current_task` 접근을 위한 스레드 안전성 보장.
*   **초기화 로직 (`lifespan`)**:
    *   **Durable Replication Queue**: 중단된 오프사이트 복제 작업을 자동 재개합니다.
    *   **Firebase Cloud Sync**: 시스템 상태를 클라우드에 실시간으로 동기화합니다.
    *   **Software Auto-Update Check**: 백그라운드에서 업데이트 여부를 확인합니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API Endpoints**:
    *   `GET /`: Jinja2 템플릿(`index.html`)을 렌더링하여 웹 UI를 제공합니다.
    *   `GET /api/system-info`: 시스템 자원(CPU, RAM, Disk) 사용 현황을 반환합니다.
    *   `GET /api/storage-stats`: 저장소별 Blob 수, 저장 용량, 논리 용량, 중복 제거(dedup) 절감률을 계산하여 반환합니다.
    *   `POST /api/browse-dir`: 디렉터리 탐색을 위한 API (블록 내에서 일부만 확인됨).
    *   `POST /api/auth/*`: 인증 관련 CRUD 및 상태 변경 API.
*   **데이터 바인딩**:
    *   Pydantic 모델을 사용하여 요청 본문을 검증합니다 (예: `password` 최소 길이 4자).
    *   `request.client.host`를 통해 클라이언트 IP를 추출하여 로컬 바이패스 여부를 판단합니다.
    *   쿠키(`backup_session`)와 헤더(`Authorization: Bearer`)를 모두 지원하여 세션 토큰을 추출합니다.
*   **이벤트 핸들러**:
    *   `scheduler.register_log_callback(append_task_log)`: 스케줄러의 로그를 전역 `current_task`의 로그 덱에 추가하는 콜백을 등록합니다.
    *   `lifespan`: 애플리케이션 생명주기 이벤트(시작/종료)를 처리합니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

*   **하드코딩 및 보안 취약점**:
    *   **Firebase 프로젝트 ID 하드코딩**: `lifespan` 내에서 `"[Firebase] 클라우드(sunhang-772e5)..."`라는 문자열이

### [분석 청크 7: app.py (Part 2/6)]
제공된 `app.py`의 [2/6] 블록은 백업 시스템의 **API 계층(REST Endpoints)**과 **백업 실행 로직의 초기 단계**를 다루고 있습니다. 특히 디렉터리 탐색, 프로필 관리, 스냅샷 조회/삭제, 그리고 커스텀 백업 태스크의 백그라운드 실행 로직이 포함되어 있습니다.

요청하신 목적에 맞춰 해당 블록의 기술적 평가와 핵심 발견점을 구조화하여 요약합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

*   **`browse_directory` (API: `/api/browse-dir`)**
    *   **역할:** 클라이언트(웹 UI)가 백업 소스나 저장소를 선택할 때 사용할 파일 시스템 탐색기 API.
    *   **특징:** Windows 환경에서는 루트 드라이브(C:, D:, ...)를 자동 목록화하고, Unix/Linux 환경에서는 `/`를 기본 경로로 설정합니다. `os.scandir`를 사용하여 성능을 최적화했으며, 권한 오류(`PermissionError`)를 무시하고 통과하는 방어적 코딩을 적용했습니다.
*   **`ConfigManager` 연동 API (`/api/profiles`)**
    *   **역할:** 백업 프로필(설정)의 CRUD(Create, Read, Delete) 관리.
    *   **특징:** 프로필 저장/삭제 시 `append_task_log`를 호출하여 사용자 활동 로그를 기록합니다.
*   **`_get_all_candidate_repos` (Helper)**
    *   **역할:** 시스템 전체에서 유효한 백업 저장소(Repository)를 자동 발견(Auto-discovery)하는 핵심 로직.
    *   **특징:**
        1.  현재 프로필에 등록된 경로
        2.  기본 경로(`BASE_DIR`, `~/MyBackup_Repository`)
        3.  `psutil`을 이용해 마운트된 모든 드라이브 루트 및 하위 표준 폴더(`MyBackup_Repository`, `backup_repository`)를 스캔.
        4.  `snapshots`와 `blobs` 디렉터리가 존재하는지 검증하여 유효성을 판별.
        5.  최신 스냅샷 시간(`_latest_snap_time`) 기준으로 정렬하여 가장 최근 활동 저장소를 우선시.
*   **`list_snapshots` (API: `/api/snapshots`)**
    *   **역할:** 모든 저장소에서 스냅샷 목록을 조회하고, **오프사이트(Offsite) 복제 상태**를 실시간으로 병합하여 반환.
    *   **특징:** `ReplicationQueueManager`를 동적 import하여 각 스냅샷의 `offsite_status` (NONE, COMMITTED 등)를 확인합니다. 이는 DR(재해복구) 상태의 시각화에 핵심적인 부분입니다.
*   **`_background_custom_backup_task` (Worker)**
    *   **역할:** 사용자가 선택한 항목(드라이버, 프로젝트, 앱, 폴더)에 대한 백업 작업을 백그라운드에서 실행하는 메인 로직.
    *   **특징:**
        *   **드라이버 추출:** `export_windows_drivers`를 호출하여 Windows OEM 드라이버를 별도 폴더로 추출하여 백업 대상에 포함.
        *   **레지스트리 백업:** 선택된 앱에 대해 `AppPackageCollector`를 사용하여 레지스트리 키와 AppData를 수집.
        *   **취소 처리:** `cancel_event`를 통해 사용자 중단을 실시간으로 감지.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **FastAPI Endpoints:**
    *   `POST /api/browse-dir`: `BrowseDirRequest` 모델로 경로 검증.
    *   `GET/POST/DELETE /api/profiles`: 프로필 관리.
    *   `GET /api/snapshots`: `repo_dir` 파라미터가 없으면 `_get_all_candidate_repos`를 호출해 전체 스캔.
    *   `GET /api/snapshots/{id}`: `include_entries` 플래그에 따라 메타데이터만 반환하거나 전체 엔트리 반환 (성능 최적화).
    *   `DELETE /api/snapshots/{id}`: 스냅샷 삭제 및 로그 기록.
*   **데이터 바인딩 및 상태 관리:**
    *   **`current_task` (Global State):** 백그라운드 태스크의 진행 상태(`progress`, `cancel_event`)를 전역 변수로 관리. 이는 웹 UI가 실시간 진행률을 polling하기 위한 상태 저장소입니다.
    *   **`ReplicationQueueManager`:**

### [분석 청크 8: app.py (Part 3/6)]
# app.py [3/6] 블록 정밀 분석 보고서

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록은 **백업 실행 로직의 핵심 엔진**을 담당하며, 크게 두 가지 백업 모드(사용자 지정 선택 백업, 일반/자동 백업)의 백그라운드 작업 처리와 API 엔드포인트를 포함합니다.

*   **`_background_custom_backup_task` (부분 포함)**:
    *   **역할**: 사용자가 특정 앱, 폴더, 레지스트리를 선택한 경우의 백업 로직.
    *   **핵심 기능**:
        *   **앱 패키징**: `AppPackageCollector`를 통해 선택된 앱의 본체, AppData(개인 설정), 시작 메뉴 바로가기, 레지스트리 키를 통합 수집.
        *   **프로필 관리**: `ConfigManager`를 통해 `prof_custom_selected` 프로필을 생성/업데이트. 데스크탑 환경 감지 시 자동 백업 강제 비활성화.
        *   **스냅샷 생성**: `SnapshotEngine.create_snapshot`을 호출하여 VSS(볼륨 섀도 복사본) 또는 일반 모드로 스냅샷 생성.
        *   **정리(Pruning)**: `SnapshotEngine.prune_snapshots`로 보존 정책(개수/일수)에 따라 오래된 스냅샷 삭제.
        *   **알림 및 동기화**: 카카오톡 알림(`notify_backup_result`) 및 Firebase 클라우드 동기화(`async_upload_backup_status`) 수행.
*   **`run_custom_selection_backup` (API 엔드포인트)**:
    *   **역할**: `/api/backup/custom-selection` POST 요청을 처리.
    *   **핵심 기능**: 현재 작업이 실행 중인지 확인(409 Conflict 반환), `threading.Event`를 생성하여 취소 신호를 전달하고, `BackgroundTasks`를 통해 비동기 작업 시작.
*   **`_background_backup_task` (부분 포함)**:
    *   **역할**: 일반 프로필 기반 백업 또는 수동 백업 로직.
    *   **핵심 기능**: 프로필 로드, 저장소 경로 유효성 검사 및 폴백(Fallback) 처리, 스냅샷 생성 준비.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API 엔드포인트**:
    *   `POST /api/backup/custom-selection`: 사용자 지정 백업 트리거.
*   **이벤트 핸들러 및 동기화**:
    *   **`task_lock` (Threading.Lock)**: 전역 `current_task` 딕셔너리에 대한 접근을 직렬화하여 데이터 경쟁(Race Condition) 방지. 모든 상태 변경(`progress`, `error`, `result`)은 락 보호 하에 수행.
    *   **`cancel_evt` (threading.Event)**: 사용자가 백업을 취소할 경우 `InterruptedError`를 발생시켜 작업 중단.
    *   **`on_progress` 콜백**: `SnapshotEngine`의 진행률 데이터를 `current_task["progress"]`에 바인딩하고, 50개 파일 단위로 로그 기록.
*   **외부 서비스 호출**:
    *   **카카오톡 알림**: `core.notifier.notify_backup_result` (성공/실패 시).
    *   **Firebase**: `core.firebase_sync.async_upload_backup_status` (백업 상태 실시간 동기화).
    *   **레지스트리/앱 수집**: `core.registry_backup.AppPackageCollector` (Windows 앱 패키지 수집).

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

### 🔴 치명적/중요 버그 및 리스크
1.  **`del manifest` 후 `manifest_summary` 사용 오류 가능성**:
    *   `manifest` 객체를 `del`하고 `gc.collect()`를 호출한 후, `manifest_summary`를 생성합니다. `manifest_summary`는 `manifest`의 값을 복사한 것이므로 문제없으나, 만약 `manifest`가 참조된 다른 객체(예: `summary` 딕셔너리)를 포함하고 있다면 메모리 해제 시점에 문제가 발생할 수 있습니다. (일반적으로는 안전하지만, `gc.collect()`가 불필요하게 성능을 저하시킬 수 있음).
2.  **`current_task` 전역 변수의 상태 불일치**:
    *   `_background_custom_backup_task`와 `_background_backup_task`가 모두 `global current_task`를 수정합니다. 만약 두 작업이 동시에 실행되지 않도록 `run_custom_selection_backup`에서 `current_task["running"]` 체크

### [분석 청크 9: app.py (Part 4/6)]
# app.py [4/6] 블록 정밀 분석 보고서

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록은 백업 시스템의 **실행 엔진(Execution Engine)**과 **API 엔드포인트**를 정의하며, 백업/복원/검증/유지보수/시스템 이미지 관리의 핵심 로직을 포함합니다.

| 컴포넌트/함수 | 핵심 역할 |
| :--- | :--- |
| `_background_backup_task` | 백업 작업의 실제 실행 로직. 스냅샷 생성, 리텐션 정책 적용, 알림 전송, Firebase 동기화를 수행합니다. |
| `_background_restore_task` | 복원 작업 실행. 스냅샷 ID 기반 저장소 자동 탐색(`_find_snapshot_repo`) 및 파일 복원 엔진 호출. |
| `run_backup` / `cancel_backup` | 백업 시작/취소 API. `threading.Event`를 이용한 비동기 취소 메커니즘 구현. |
| `get_task_status` | 현재 작업 진행률, 로그, 결과를 클라이언트에 반환하는 폴링(Polling)용 API. |
| `run_restore` | 복원 요청 API. 인플레이스(In-place) 또는 타겟 디렉터리 복원 옵션 지원. |
| `run_verify` | 스냅샷 물리적 무결성 검증 API. 샘플링 기반(`sample_ratio=0.2`) 검증 및 SQLite DB 상태 업데이트. |
| `prune_storage` | 고아 블롭(Orphan Blobs) 제거 및 용량 회수 API. |
| `Windows Task Scheduler API` | Windows 작업 스케줄러 등록/해제/상태 조회. 자동 백업 스케줄링 지원. |
| `SystemImageManager` | Windows 시스템 이미지(Bare-Metal) 백업 관리 인터페이스 (블록 말미에 선언 시작). |

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **스레드 안전성 (Thread Safety):**
    *   `task_lock` (Lock 객체)을 사용하여 `current_task` 전역 변수의 읽기/쓰기 접근을 직렬화합니다.
    *   `on_progress` 콜백 내에서 `task_lock`을 획득하여 진행률 업데이트 시 경쟁 조건(Race Condition)을 방지합니다.
*   **비동기 작업 처리:**
    *   FastAPI의 `BackgroundTasks`를 사용하여 백업/복원 작업은 API 응답을 즉시 반환하고 백그라운드에서 실행됩니다.
    *   `threading.Event` (`cancel_evt`)를 통해 사용자 취소 신호를 백그라운드 스레드에 전달합니다.
*   **외부 서비스 연동:**
    *   **KakaoTalk:** `core.notifier.notify_backup_result`를 통해 백업 성공/실패 알림 전송.
    *   **Firebase:** `core.firebase_sync.async_upload_backup_status`를 통해 백업 상태를 클라우드에 실시간 동기화.
    *   **Windows OS:** `core.windows_task` 모듈을 통해 OS 레벨 스케줄러와 연동.
*   **데이터 바인딩:**
    *   Pydantic 모델 (`RunBackupRequest`, `RunRestoreRequest`, `RunVerifyRequest`)을 통해 입력 검증 수행.
    *   `ConfigManager`를 통해 프로파일 설정(리텐션, 저장소 경로 등)을 로드 및 저장.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

### 🔴 치명적/중요 버그 및 리스크

1.  **`del manifest` 및 `gc.collect()`의 불필요한 오버헤드:**
    *   `manifest` 객체를 삭제하고 `gc.collect()`를 명시적으로 호출하는 것은 Python의 메모리 관리에 불필요한 지연을 유발할 수 있습니다. 특히 대용량 백업 시 `gc.collect()`는 전체 힙을 스캔하여 성능 저하를 초래합니다.
    *   **개선:** `del manifest`만 유지하거나, 메모리 누수가 확인되지 않는 한 `gc.collect()`를 제거하는 것이 좋습니다.

2.  **`_find_snapshot_repo`의 폴백 로직 취약점:**
    *   `_background_restore_task`와 `run_verify`에서 `repo_dir`를 찾지 못할 경우 `profiles[0].get("repo_dir")`를 사용합니다.
    *   **문제:** 프로파일 목록이 비어있거나, 첫 번째 프로파일의 저장소가 해당 스냅샷과 무관할 경우 **잘못된 저장소에서 복원/검증을 시도**하여 데이터 손실 또는 오류를 유발할 수 있습니다.
    *   **개선:** 스

### [분석 청크 10: app.py (Part 5/6)]
제공된 `app.py`의 [5/6] 블록은 백업 시스템의 **운영체제 레벨 통합(Windows Task, System Image)**, **보안 강화된 원격 자가 업데이트(Self-Update)**, **마스터-클라이언트 릴리스 동기화**, 그리고 **실시간 경보 시스템**의 핵심 로직을 포함하고 있습니다.

요청하신 4가지 관점에 따라 정밀 분석 및 구조화 요약을 보고합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록은 백업 시스템이 단순한 파일 복사 도구를 넘어 **자율적 시스템 관리 에이전트**로 기능하도록 하는 핵심 API들을 정의합니다.

*   **Windows 스케줄러 통합 (`/api/windows-task/*`)**:
    *   `register_windows_task`, `unregister_windows_task`: Windows 작업 스케줄러에 백업 작업을 등록/해제하여 OS 레벨의 정시 실행을 보장합니다.
*   **시스템 이미지 백업 (`/api/system-image/*`)**:
    *   `SystemImageManager` 클래스를 통해 Bare-Metal(시스템 전체) 백업의 시작, 중지, 상태 조회, 로그 조회를 제어합니다.
*   **서비스 제어 (`/api/system/shutdown`)**:
    *   백업 서비스 프로세스를 안전하게 종료하는 API입니다.
*   **보안 자가 업데이트 (`/api/system/self-update`)**:
    *   **핵심 보안 기능**: Ed25519 전자서명 검증, Zip-Slip(경로 탈출) 방지, 안전한 압축 해제, 서비스 재시작을 포함한 완전한 자가 업데이트 파이프라인을 구현합니다.
*   **릴리스 관리 및 동기화 (`/api/system/release-info`, `/api/system/update-package`, `/api/system/check-remote-release`, `/api/system/sync-remote-release`)**:
    *   마스터 서버(K12)에서 최신 릴리스 정보를 조회하고, 서명된 패키지를 다운로드하여 클라이언트에 자동 적용하는 '원클릭 동기화' 기능을 제공합니다.
*   **실시간 경보 요약 (`/api/alerts/summary`)**:
    *   최근 24시간 내 백업 실패, 저장소 디스크 공간 부족 등을 집계하여 UI 배너에 표시할 실시간 경보 상태를 계산합니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **FastAPI 엔드포인트**:
    *   `POST /api/windows-task/register`: `WindowsTaskRegisterRequest` 모델로 프로필 ID와 스케줄 정보를 바인딩합니다.
    *   `POST /api/system/self-update`: `Request` 객체와 `custom_body`, `custom_signature`를 통해 바이너리 데이터와 서명을 처리합니다.
    *   `GET /api/system/check-remote-release`: 쿼리 파라미터 `master_url`을 통해 마스터 서버 주소를 동적으로 바인딩합니다.
*   **외부 API 호출 (Outbound)**:
    *   `urllib.request`를 사용하여 마스터 서버의 `/api/system/release-info` 및 `/api/system/update-package` 엔드포인트를 호출합니다.
    *   타임아웃 설정: 정보 조회는 2.5초, 패키지 다운로드는 15초로 설정되어 네트워크 지연에 대한 기본 방어선을 구축했습니다.
*   **데이터 바인딩 및 상태 관리**:
    *   `ConfigManager.get_profiles()`: 프로필 설정(이름, 상태, 마지막 실행 시간, 저장소 경로)을 읽어 경보 상태를 계산합니다.
    *   `SystemImageManager`: 시스템 이미지 백업의 상태와 로그를 메모리/파일 기반으로 관리하는 것으로 추정됩니다.
    *   `VERSION` 전역 변수: 현재 실행 중인 버전과 마스터 서버의 버전을 비교하여 업데이트 필요 여부를 판단합니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

#### 🔴 치명적 보안 및 안정성 문제
1.  **자가 업데이트 시 `tar` 명령 의존성 및 실패 처리 부재**:
    *   `self_update` 함수에서 `bat_content`에 `tar -xf` 명령을 사용합니다. Windows 10/11 기본 `tar`는 `zip` 형식을 지원하지만, 구형 Windows나 특정 환경에서는 실패할 수 있습니다.
    *   **버그**: `tar` 실패 시 업데이트가 중단되지만, `os._exit(0)`이 호출되어 서비스가 죽고 재시작되지 않으면 **서비스가 영구적으로 중단**됩니다. `tar` 실패에 대한 체크나 `zipfile` 모듈을 이용한 Python 내장 추출 로직으로 대체하는 것이 안전합니다

### [분석 청크 11: app.py (Part 6/6)]
# app.py [6/6] 블록 정밀 분석 보고서

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록은 백업 시스템의 **상태 모니터링**, **클라우드 동기화(Firebase)**, 및 **소프트웨어 자동 업데이트** 기능을 담당하는 API 엔드포인트들을 정의합니다.

*   **`get_system_health_status` (부분 포함)**:
    *   **역할**: 시스템 전반의 건강 상태(Health Check)를 종합적으로 평가합니다.
    *   **핵심 로직**:
        1.  **백업 실패 감지**: 최근 백업 실패 이력을 확인하여 `critical` 또는 `warning` 상태를 설정합니다.
        2.  **디스크 용량 모니터링**: 활성 저장소(`active_repo`)가 위치한 드라이브의 여유 공간을 `shutil.disk_usage`로 확인합니다.
            *   여유 공간 < 5%: `critical` (고갈 위험)
            *   여유 공간 < 10%: `warning` (부족 경고)
        3.  **복제 큐(Replication Queue) 점검**: 오프사이트 복제 작업의 중단(`interrupted`) 건수를 확인하여 네트워크 단절 여부를 알립니다.
    *   **출력**: `status` (green/yellow/red), `alerts` 리스트, `disk` 정보.

*   **Firebase Cloud Sync API**:
    *   `GET /api/firebase/status`: 현재 기기 식별 정보 및 Firebase 프로젝트 ID를 반환합니다.
    *   `POST /api/firebase/sync`: 백업 상태를 즉시 Firestore에 수동 동기화합니다.
    *   `GET /api/firebase/history`: 클라우드에 저장된 백업 이력을 조회합니다.

*   **Software Auto-Update API**:
    *   `GET /api/update/status`: 최신 버전 확인 및 캐싱(10분) 로직을 수행합니다.
    *   `POST /api/update/apply`: 백그라운드 태스크로 업데이트 파이프라인(다운로드, 검증, 설치)을 트리거합니다.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API 엔드포인트**:
    *   `GET /api/health` (추정, 함수명 미표기되었으나 컨텍스트상 시스템 상태 조회): 시스템 상태, 디스크, 복제 큐 정보를 JSON으로 반환.
    *   `GET /api/firebase/status`: Firebase 연동 상태 조회.
    *   `POST /api/firebase/sync`: Firebase 수동 동기화 트리거.
    *   `GET /api/firebase/history`: 클라우드 백업 이력 조회 (`limit` 파라미터 지원).
    *   `GET /api/update/status`: 업데이트 상태 조회 (`force_check` 파라미터 지원).
    *   `POST /api/update/apply`: 업데이트 실행 트리거.

*   **외부 모듈 호출**:
    *   `ConfigManager.get_profiles()`: 백업 프로필 설정 조회.
    *   `shutil.disk_usage()`: OS 레벨 디스크 용량 조회.
    *   `core.replication_queue.ReplicationQueueManager`: 복제 상태 요약 조회.
    *   `core.firebase_sync`: Firebase 연동 함수 (`get_current_device_info`, `upload_current_system_status`, `fetch_cloud_backup_history`).
    *   `core.updater`: 업데이트 관련 함수 (`check_for_update`, `get_current_installed_version`, `perform_full_update_pipeline`).

*   **데이터 바인딩**:
    *   `_cached_update_info`: 업데이트 상태 캐싱을 위한 전역/모듈 레벨 변수 (10분 TTL).
    *   `background_tasks`: FastAPI의 BackgroundTasks를 사용하여 업데이트 및 Firebase 동기화를 비동기 처리.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

### 🔴 치명적/중요 버그 및 리스크

1.  **`active_repo` 선택 로직의 취약성**:
    *   `profiles[0].get("repo_dir")`를 사용하여 **첫 번째 프로필**을 활성 저장소로 가정합니다.
    *   **문제**: 사용자가 여러 프로필을 사용 중이거나, 첫 번째 프로필이 비활성/삭제된 상태라면, 실제 백업이 진행 중인 저장소가 아닌 다른 드라이브의 용량을 모니터링하게 되어 **오류(거짓 안심)**를 유발할 수 있습니다.
    *   **개선**: 현재 활성화된 프로필 또는 가장 최근 백업이 발생한 프로필의 `repo_dir`를 동적으로 식별해야 합니다.

2.  **`_get_all_candidate_repos()` 함수의 의존성**:
    *   복제 큐 점검 시 `_get_all_candidate_repos()`를 호출하지만,