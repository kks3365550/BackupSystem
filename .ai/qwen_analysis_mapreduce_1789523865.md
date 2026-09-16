# Qwen 대용량 자동 분할 분석 전체 산출물

## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]: 데이터 영구 손실 및 상태 무결성 훼손**
`profiles.json`이 비어있거나 파싱 실패 시, 사용자 의도와 무관하게 **기본값(Default Profile)으로 강제 초기화(Overwrite)** 되는 치명적 결함이 존재합니다. 이는 사용자가 프로파일을 모두 삭제한 정상 상태나, 파일 손상 시에도 데이터를 복구하지 못하고 기본값으로 덮어써 기존 백업 설정을 영구적으로 소실시킵니다.

**[BUG]: `config.py` 내 3중 트리거 로직 오류**
1. **빈 리스트 오인 (L83-85)**: `profiles.json`이 존재하지만 내용이 `[]`일 때, 이를 "초기화 필요 상태"로 오해하고 `[DEFAULT_PROFILE]`을 주입하여 파일을 덮어씀.
2. **예외 처리 시 데이터 소실 (L87-88)**: JSON 파싱 실패 시 손상된 파일을 백업하지 않고 메모리상 기본값만 반환함. 이후 `save_profile()` 호출 시 이 기본값으로 전체 파일이 재작성되어 기존 데이터가 사라짐.
3. **경쟁 조건(Race Condition) 및 비원자적 쓰기**: `get_profiles()` -> 수정 -> `save_profiles()` 순서가 원자적(Atomic)이지 않아, 동시 요청이나 중간 오류 발생 시 파일이 깨지거나 빈 파일로 덮어쓰이는 리스크가 상존함.

**[RISK]: 환경 의존성 및 보안 취약점**
*   **경로 하드코딩**: `DEFAULT_PROFILE`의 경로가 모듈 로드 시점에 고정되어, 앱 설치 위치 변경 시 기존 프로필의 유효성이 상실됨.
*   **자기 업데이트(Self-Update) 위험**: `app.py`의 `self_update` 로직이 외부 스크립트(`tar`, `.bat`)에 의존하여 실패 시 파일 시스템 일관성이 깨질 수 있으며, 이는 간접적으로 설정 파일 손상을 유발할 수 있음.

**[ACTION]: 즉시 수정 가이드**
1. **빈 리스트 처리 로직 제거/수정 (`config.py: L83-85`)**: `if not profiles:` 조건에서 기본값 주입 및 저장 로직을 삭제하거나, 명시적인 `initialize_profiles()` 함수로 분리하여 앱 시작 시에만 한 번만 실행되도록 변경.
2. **안전한 예외 처리 도입 (`config.py: L87-88`)**: 파싱 실패 시 기존 파일을 `profiles.json.bak`으로 백업한 후, 기본값을 반환하되 즉시 파일에 쓰지 않도록 변경.
3. **원자적 쓰기(Atomic Write) 구현**: `save_profiles()`에서 임시 파일로 작성 후 `os.replace()`를 사용하여 파일 교체하도록 수정하여 중간 실패 시 데이터 손실 방지.

**[DECISION REQUIRED]: Antigravity 및 사용자 승인 사항**
*   **데이터 마이그레이션 정책 결정**: 기존에 손상되었거나 빈 상태인 `profiles.json`을 발견했을 때, 기본값으로 덮어쓸지(현재 로직) 아니면 파일만 백업하고 앱은 에러 상태로 유지할지(권장) 최종 결정 필요.
*   **파일 잠금(File Locking) 도입 여부**: 다중 인스턴스 실행이나 동시 요청 방지를 위해 파일 시스템 레벨의 락킹 메커니즘 도입 승인 필요.

---

## PART 2. [COMPREHENSIVE AUDIT & ARCHITECTURE REPORT]

### 1. 전체 아키텍처 및 데이터 흐름 분석
본 시스템은 FastAPI 기반 백엔드와 `ConfigManager`를 통한 파일 시스템 기반 설정 관리 구조를 취하고 있습니다.
*   **설정 계층**: `app_settings.json` (서버 포트 등)과 `profiles.json` (백업 프로필 목록)으로 분리되어 있음.
*   **데이터 흐름**: 프론트엔드 API 요청 -> `app.py` 엔드포인트 -> `ConfigManager` 정적 메서드 호출 -> 파일 시스템 I/O.
*   **핵심 문제점**: `ConfigManager.get_profiles()`가 단순한 '읽기' 함수가 아니라, 조건부 '초기화/쓰기' 로직을 내포하고 있어 부수 효과(Side Effect)로 인해 데이터 무결성이 훼손되고 있음.

### 2. 파일별 상세 감사 결과

#### A. `core/config.py` (핵심 문제 발생 지점)
이 파일은 `profiles.json` 초기화 및 덮어쓰기의 **유일한 직접적 원인**입니다.

| 라인 번호 | 함수/로직 | 문제 분석 | 수정 방향 |
| :--- | :--- | :--- | :--- |
| **L78-81** | `get_profiles()`<br>파일 존재 확인 | 파일이 물리적으로 없으면 기본값 생성 및 저장. (정상 범위이나, 경로 오류 시 오동작 가능) | 권한 오류 등 예외를 별도 처리하여 오초기화 방지. |
| **L83-85** | `get_profiles()`<br>빈 리스트 체크 | **주범**: 파일은 있으나 내용이 `[]`일 때, 이를 초기 상태로 판단하여 `[DEFAULT_PROFILE]`로 강제 덮어씀. 사용자가 의도적으로 프로파일을 비운 상태가 리셋됨. | 빈 리스트는 유효한 상태로 간주하고 기본값 주입 로직 제거. |
| **L87-88** | `get_profiles()`<br>예외 처리 | JSON 파싱 실패 시 기존 파일을 백업하지 않고 메모리상 기본값만 반환. 이후 저장 시 데이터 소실. | 손상 파일 `.bak` 백업 후, 즉시 파일 재작성 금지. |
| **L106-123** | `save_profile()`<br>단일 저장 | 전체 리스트 로드-수정-저장 방식. 읽기 단계에서 기본값이 반환되면 사용자 데이터 없이 기본값만 가진 파일로 덮어씀. | 원자적 쓰기 및 트랜잭션 개념 도입. |

#### B. `web/app.py` (간접적 리스크 및 API 계층)
*   **Part 1 분석**: `profiles.json`을 직접 조작하는 코드는 없음. 모든 읽기/쓰기는 `ConfigManager`에 위임됨.
    *   `_get_all_candidate_repos()`: 저장소 디렉터리 스캔만 수행하며 프로필 파일 자체는 수정하지 않음.
*   **Part 2 분석**: 백업 실행 및 시스템 관리 로직 포함.
    *   `_background_backup_task`: 백업 성공/실패 시 `profile["last_run"]` 등 메타데이터만 갱신 후 `ConfigManager.save_profile()` 호출. 이 과정에서 `get_profiles()`의 버그가 발동되면 전체 파일이 리셋될 수 있음.
    *   `self_update()`: 외부 스크립트(`tar`, `.bat`)를 이용한 자기 업데이트 로직. 실패 시 파일 시스템 일관성 문제 발생 가능. Python 내장 라이브러리 사용으로 교체 권장.

#### C. `run.py` (진입점 및 부수적 관리)
*   **분석 결과**: `profiles.json` 관련 코드가 전혀 없음.
*   **역할**: 의존성 체크(`ensure_dependencies`), 포트 충돌 방지, 브라우저 자동 열기, 서버 기동.
*   **리스크**: 패키지 설치 실패 시 앱 종료 로직은 존재하나, 프로필 데이터 손실과는 무관함.

### 3. 종합 결론 및 최종 수정 로드맵

**원인 확정**: `profiles.json`이 초기화되는 현상은 `core/config.py`의 `get_profiles()` 함수 내부에 있는 **조건부 자동 초기화 로직**과 **불완전한 예외 처리**가 복합적으로 작용하여 발생합니다. 특히, 빈 리스트(`[]`)를 "초기 상태"로 오해하는 L83-85 라인이 가장 빈번한 트리거입니다.

**우선순위별 수정 계획**:
1.  **[P0 - 즉시]** `config.py`의 `get_profiles()`에서 빈 리스트에 대한 기본값 주입 및 저장 로직 제거.
2.  **[P0 - 즉시]** JSON 파싱 실패 시 기존 파일 백업(`.bak`) 로직 추가 및 즉시 재작성 금지.
3.  **[P1 - 중요]** `save_profiles()` 함수를 원자적 쓰기(Atomic Write) 방식으로 리팩토링하여 중간 오류 시 데이터 손실 방지.
4.  **[P2 - 개선]** `DEFAULT_PROFILE`의 하드코딩된 경로를 동적 경로로 변경하거나, 앱 설치 위치 변경 시 마이그레이션 로직 추가.
5.  **[P3 - 보안]** `app.py`의 `self_update` 로직을 외부 스크립트 의존성에서 벗어나 Python 내장 모듈 기반으로 재구축하여 안정성 확보.

---
## 청크별 1차 분석 원본

### [분석 청크 1: config.py (Part 1/1)]
# config.py 정밀 분석 보고서

## 1. 주요 함수/컴포넌트 및 핵심 역할
*   **`ConfigManager` 클래스**: 앱 설정(`app_settings.json`)과 백업 프로필(`profiles.json`)의 CRUD(생성, 읽기, 업데이트, 삭제)를 담당하는 정적 메서드 모음.
*   **`get_profiles()` (L76-89)**: `profiles.json`을 로드하는 핵심 함수. 파일이 없거나 비어있을 때 기본 프로필 주입 로직 포함.
*   **`save_profiles()` (L91-94)**: 메모리의 프로필 리스트를 `profiles.json`으로 직렬화하여 저장하는 함수.
*   **`DEFAULT_PROFILE` (L12-30)**: 초기 상태의 백업 프로필 템플릿.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **데이터 바인딩**: `get_profiles()`는 파일 시스템(`PROFILES_FILE`)과 메모리 객체 간에 직접적인 읽기/쓰기 연동을 수행함.
*   **상태 관리**: `save_profile()`와 `delete_profile()`은 항상 `get_profiles()`를 호출하여 최신 상태를 로드한 후, 수정된 전체 리스트를 다시 `save_profiles()`로 덮어쓰는 방식(Read-Modify-Write)을 취함.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **잠재적 데이터 손실 리스크 (경쟁 조건)**: `save_profile()`와 `delete_profile()`이 동시 실행되거나, 다른 프로세스가 파일을 수정하는 중이라면 마지막 쓰기가 전체 파일을 덮어써 중간에 추가된 프로필이 사라질 수 있음. 파일 잠금(File Locking) 미구현.
*   **예외 처리의 불완전성**: `get_profiles()`의 `except Exception` 블록(L87-88)에서 JSON 파싱 실패 시 기존 파일을 백업하지 않고 단순히 기본값을 반환함. 이후 어떤 저장 작업이 일어나면 손상된 파일 내용이 영구적으로 사라짐.
*   **하드코딩 경로**: `DEFAULT_PROFILE`의 `sources`와 `repo_dir`가 모듈 로드 시점에 절대경로로 고정됨. 앱 설치 위치가 바뀌면 기존 프로필의 경로가 무효화될 수 있음.

## 4. 사용자 질문 관련 핵심 발견점 (초압축 헤더)

### 원인 분석: profiles.json 초기화/덮어쓰기 트리거

| 위치 (파일:라인) | 코드 로직 | 문제점 및 수정 방법 |
| :--- | :--- | :--- |
| **config.py: L78-81** | `if not os.path.exists(PROFILES_FILE): ... save_profiles([default_p])` | **원인 1**: 파일이 물리적으로 삭제되거나 경로가 잘못 인식되면 기본값으로 재초기화됨. <br>**수정**: 파일 존재 확인 시 권한 오류나 경로 오류를 별도 처리하도록 로직 강화 필요. |
| **config.py: L83-85** | `if not profiles: profiles = [dict(DEFAULT_PROFILE)]; cls.save_profiles(profiles)` | **원인 2 (주범)**: JSON 파일이 존재하지만 내용이 빈 리스트 `[]`이거나 비어있는 경우, 이를 "초기 상태"로 판단하여 **기본 프로필로 강제 덮어쓰기**함. 사용자가 의도적으로 프로파일을 모두 삭제한 상태가 기본값으로 리셋되는 현상의 직접적 원인. <br>**수정**: 빈 리스트인 경우에도 기존 파일 상태를 유지하거나, 명시적인 초기화 플래그를 도입해야 함. |
| **config.py: L87-88** | `except Exception: return [dict(DEFAULT_PROFILE)]` | **원인 3**: JSON 파싱 오류(형식 깨짐) 시 기본값을 반환하지만 파일은 그대로 둠. 이후 다른 저장 로직(`save_profile`)이 이 기본값 리스트를 받아 전체 파일을 덮어쓰면, 이전에 존재했던 사용자 데이터가 사라짐. <br>**수정**: 예외 발생 시 손상된 파일을 `.bak`로 백업한 후 기본값으로 대체하는 안전장치 추가 필요. |
| **config.py: L106-123** | `save_profile()` 내 `profiles = cls.get_profiles()` 호출 후 전체 저장 | **원인 4**: 단일 프로필 저장 시에도 전체 리스트를 로드하여 다시 저장함. 만약 이 과정에서 `get_profiles()`가 예외로 기본값을 반환했다면, 사용자 데이터 없이 기본값만 가진 파일이 생성됨. <br>**수정**: 읽기 실패 시 저장을 중단하거나, 원본 데이터를 보존하는 트랜잭션 방식

### [분석 청크 2: app.py (Part 1/2)]
# app.py [1/2] 정밀 분석 리포트

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
*   **FastAPI 애플리케이션 초기화**: `lifespan` 컨텍스트 매니저를 통해 스케줄러 시작, 복제 큐 자동 재개 로직 실행.
*   **프로필 관리 API (`/api/profiles`)**:
    *   `list_profiles()`: `ConfigManager.get_profiles()` 호출하여 프로필 목록 반환.
    *   `save_profile()`: `ConfigManager.save_profile(profile)` 호출하여 프로필 저장 및 로그 기록.
    *   `delete_profile()`: `ConfigManager.delete_profile(profile_id)` 호출하여 삭제 처리.
*   **백업 실행 로직**:
    *   `_background_custom_selection_backup_task`: 사용자 선택 기반 백업 수행. 드라이버 추출, 앱 패키징, 커스텀 폴더 포함.
    *   `_background_backup_task`: 프로필 기반 자동/수동 백업 수행.
*   **저장소 탐지 로직 (`_get_all_candidate_repos`)**: 현재 드라이브, 홈 디렉터리, 프로파일 내 `repo_dir`, 표준 경로(`backup_repository`, `MyBackup_Repository`)를 스캔하여 유효한 저장소 목록 생성.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **API 엔드포인트**:
    *   `GET /api/profiles`: 프로필 조회.
    *   `POST /api/profiles`: 프로필 저장 (신규/수정).
    *   `DELETE /api/profiles/{id}`: 프로필 삭제.
    *   `POST /api/backup/custom-selection`: 커스텀 백업 시작 (배경 태스크로 위임).
*   **데이터 흐름**:
    *   프론트엔드에서 프로필 데이터를 JSON으로 전송 -> `ConfigManager`를 통해 파일 시스템에 영속화.
    *   백업 실행 시 `ConfigManager.get_profile()` 또는 `get_profiles()`로 설정 로드 후 `SnapshotEngine`에 전달.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **핵심 의심 지점: `ConfigManager` 내부 로직 미확인 (Part 2 필요)**
    *   현재 블록(`app.py`)에서는 `profiles.json`을 직접 조작하는 코드가 없습니다. 모든 읽기/쓰기는 `core.config.ConfigManager` 클래스에 위임됩니다.
    *   따라서 **"profiles.json이 초기화되는 원인"은 이 파일의 로직이 아니라, `ConfigManager` 클래스 내부의 `get_profiles()` 또는 `save_profile()` 메서드에서 발생했을 가능성이 99%입니다.**
*   **잠재적 문제점 (app.py 내)**:
    *   `_background_custom_selection_backup_task` 내에서 `profile_id = "prof_custom_selected"`로 하드코딩된 ID를 사용하고 있습니다. 이 ID가 기존 프로필과 충돌하거나, `ConfigManager.save_profile()`가 특정 조건에서 전체 파일을 리셋하는 로직을 가졌다면 문제가 됩니다.
    *   `lifespan`에서 `_get_all_candidate_repos()`가 호출되지만, 이는 저장소 디렉터리를 찾는 용도이지 프로필 파일 자체를 수정하지는 않습니다.

## 4. 사용자의 질문과 관련된 핵심 발견점 (초압축 헤더)

> **결론: `app.py` Part 1에는 `profiles.json`을 직접 덮어쓰거나 초기화하는 코드가 없습니다.**
> 원인은 반드시 **`core/config.py`** 파일의 `ConfigManager` 클래스 내부에 있습니다.

### 🔍 원인 추적 및 수정 방향 (Part 2 분석 전 예측)

| 위치 (예상) | 문제 유형 | 상세 설명 및 수정 방법 |
| :--- | :--- | :--- |
| **`core/config.py`**<br>`ConfigManager.get_profiles()` | **읽기 시 자동 생성/초기화 버그** | 파일이 없거나 파싱 실패 시, 빈 리스트 `[]` 또는 기본값을 반환하면서 **동시에 파일을 다시 쓰는 로직**이 있는지 확인. <br>**수정**: 읽기 전용이어야 함. 파일 부재 시 메모리상만 기본값 반환하거나, 명시적인 초기화 함수로 분리해야 함. |
| **`core/config.py`**<br>`ConfigManager.save_profile()` | **전체 파일 리스크 (Race Condition)** | 단일 프로필 저장 시 전체 리스트를 로드-수정-저장하는 과정에서, 동시 요청이나 예외 발생 시 파일이 깨지거나 빈 파일로 덮어쓰이는 경우. <br>**수정**: 원자적 쓰기(Atomic Write)

### [분석 청크 3: app.py (Part 2/2)]
제공된 `app.py`의 [2/2] 블록(백업 실행, 복원, 검증, 유지보수, 시스템 관리 API)을 정밀 분석한 결과, **profiles.json이 초기화되는 직접적인 원인은 이 파일 내부에 존재하지 않습니다.** 오히려 이 구간은 프로필을 *읽어와서* 백업을 수행하고, 성공/실패 상태만 갱신하는 로직으로 구성되어 있습니다.

그러나 `ConfigManager.save_profile()` 호출 시점과 외부 의존성(`core/config.py` 등)의 상호작용에서 간접적인 리스크를 발견했습니다. 요청하신 4가지 항목에 따라 구조화하여 보고합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
이 블록은 백엔드 API 엔드포인트와 배경 작업(Background Task) 로직으로 구성됩니다.

*   **`_background_backup_task(params)`**: 실제 백업 엔진(`SnapshotEngine`)을 호출하는 비동기 태스크.
    *   프로필 정보(`sources`, `exclude_patterns`, `compression_level`)를 파라미터 또는 프로파일에서 추출합니다.
    *   백업 성공 시 `profile["last_run"]`, `profile["last_status"]` 등을 갱신하고 **`ConfigManager.save_profile(profile)`** 을 호출합니다.
*   **`run_backup(req, background_tasks)`**: `/api/backup/run` 엔드포인트. 현재 작업이 실행 중인지 확인 후 배경 태스크를 큐에 추가합니다.
*   **`_background_restore_task(params)`**: 복원 엔진(`RestoreEngine`)을 호출하는 비동기 태스크. 프로필 저장소 경로를 자동 탐색(`_find_snapshot_repo`)합니다.
*   **`run_verify(req)`**: `/api/verify/run`. 스냅샷 무결성 검증 및 SQLite DB 업데이트 로직 포함.
*   **`self_update(request)`**: `/api/system/self-update`. 원격에서 받은 ZIP 파일을 추출하고 `.bat` 스크립트를 통해 프로세스를 재시작하는 위험한 시스템 관리 API입니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **데이터 흐름 (프로필 관련)**:
    1.  클라이언트가 `RunBackupRequest`로 요청.
    2.  `_background_backup_task`에서 `profile_id`를 기반으로 프로필 객체를 참조합니다. *(참고: 이 블록에는 프로필을 DB/JSON에서 로드하는 로직이 보이지 않으므로, 이는 Part 1이나 호출자 쪽에서 전달된 것으로 추정됩니다.)*
    3.  백업 완료 후 프로파일의 메타데이터(마지막 실행 시간, 상태)만 수정합니다.
    4.  `ConfigManager.save_profile(profile)`을 통해 변경 사항을 영속화합니다.
*   **상태 관리**:
    *   전역 변수 `current_task`와 `task_lock`을 사용하여 동시성 문제를 방지합니다.
    *   `on_progress` 콜백을 통해 진행도를 `current_task["progress"]`에 실시간으로 바인딩합니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
**[핵심 발견: profiles.json 초기화 원인은 이 파일이 아님]**
*   **직접적 원인 부재**: 이 코드 블록 어디에도 `profiles.json` 파일을 삭제하거나, 빈 리스트/기본값으로 덮어쓰는 로직(`json.dump`, `open(..., 'w')` 등)이 없습니다.
*   **잠재적 리스크 포인트 (간접적 원인 가능성)**:
    1.  **`ConfigManager.save_profile()`의 구현 의존성**: 이 함수가 내부적으로 "전체 파일을 읽어서 수정 후 다시 쓰는" 방식이라면, 동시 쓰기 시 경쟁 조건(Race Condition)으로 파일이 깨지거나 초기화될 수 있습니다. 하지만 이는 `core/config.py`의 문제입니다.
    2.  **`self_update` 로직의 위험성**:
        *   `tar -xf "{temp_zip}" -C "{BASE_DIR}"` 명령을 사용합니다. 만약 업데이트 패키지에 `profiles.json`이 포함되어 있지 않다면 기존 파일은 유지됩니다. 하지만, 업데이트 패키지가 불완전하거나 추출 과정에서 권한 문제가 발생하면 설정 파일이 손상될 수 있습니다.
        *   **버그**: `tar` 명령어 사용은 Windows 기본 환경에서 실패할 수 있습니다 (Windows 10/11의 경우 `tar`가 내장되어 있지만, 경로에 공백이 있거나 인코딩 문제 시 실패). 더 안전한 방법은 Python의 `zipfile` 모듈을 직접 사용하는 것입니다.
    3.  **하드코딩 및 보안 취약

### [분석 청크 4: run.py (Part 1/1)]
# run.py 정밀 분석 보고서

## 1. 주요 함수/컴포넌트 및 핵심 역할
*   **`ensure_dependencies()`**: 실행 시 필수 패키지(`uvicorn`, `fastapi` 등) 존재 여부를 확인하고, 누락 시 `requirements.txt` 기반 자동 설치를 수행합니다.
*   **`main()`**: 앱의 진입점입니다. `ConfigManager`를 통해 포트/호스트 설정을 로드하고, 해당 포트가 이미 사용 중인지(`is_port_in_use`) 판단하여 서버 기동 또는 브라우저 열기만 수행하는 로직을 제어합니다.
*   **`open_browser(port)`**: 서버 포트 연결 성공 대기 후, Windows 환경에서는 `os.startfile`, 그 외에는 `webbrowser.open`으로 기본 브라우저를 실행시킵니다.
*   **에러 처리 유틸**: `show_error_dialog`(Windows 네이티브 메시지박스), `log_startup_error`(로그 파일 기록)가 포함되어 있습니다.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **설정 로드**: `ConfigManager.get_settings()`를 통해 서버 포트(기본 8765), 호스트, 자동 브라우저 오픈 여부를 읽어옵니다.
*   **서버 기동**: `uvicorn.Config` 및 `uvicorn.Server` 인스턴스를 생성하여 `web.app:app`을 비동기 이벤트 루프(`server.run()`)로 실행합니다.
*   **데이터 바인딩**: 이 파일 자체에는 `profiles.json`에 대한 직접적인 읽기/쓰기 로직이 **존재하지 않습니다.**

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **프로필 초기화 원인의 부재**: 현재 제공된 `run.py` 코드 블록(4083자) 내에는 `profiles.json` 파일 생성, 덮어쓰기, 기본값 주입 관련 코드가 **전혀 없습니다.**
*   **잠재적 리스크 (참고)**: `ensure_dependencies()`에서 패키지 설치 실패 시 예외를 다시 던지지만, 네트워크 문제 등으로 인한 반복 실패 시 앱이 즉시 종료됩니다.

## 4. 사용자의 질문과 관련된 핵심 발견점 및 수정 방향
**핵심 결론:** `run.py`는 **프로필 초기화 원인이 아닙니다.** 이 파일은 오직 서버 프로세스의 생명주기(기동/종료)와 의존성 관리만 담당합니다.

**원인 추적 및 수정 가이드 (초압축 헤더):**

1.  **진짜 원인 위치 탐색**:
    *   `profiles.json` 조작 로직은 `run.py`가 로드하는 실제 애플리케이션 모듈인 **`web/app.py`** 또는 그 하위 서비스/모델 레이어(예: `core/profile_service.py`, `models/profile.py`)에 있을 가능성이 99%입니다.
    *   `ConfigManager` 클래스 정의 파일(`core/config.py`)에서 설정 로드 시 부수적으로 프로필 파일을 초기화하는 로직이 있는지 확인해야 합니다.

2.  **초기화 트리거 조건 분석 (추정)**:
    *   **버전 체크**: 앱 시작 시 저장된 버전과 현재 코드 버전을 비교하여 불일치 시 `profiles.json`을 삭제 후 재생성하는 로직이 `web/app.py`의 `lifespan` 또는 `startup_event`에 있을 수 있습니다.
    *   **파일 무결성/존재 체크**: 파일이 없거나 파싱 오류(JSON Decode Error) 발생 시 예외 핸들러에서 파일을 기본값으로 덮어쓰는 로직이 의심됩니다.

3.  **수정 방법 (추정된 코드 위치 기준)**:
    *   `web/app.py` 또는 프로필 관리 모듈에서 `profiles.json`을 열 때 파일 존재 여부를 확인하는 로직을 찾습니다.
    *   **버그 수정**: 파일이 이미 존재하고 유효한 JSON이라면 절대 덮어쓰지 않도록 조건문을 수정합니다. (예: `if not os.path.exists(profiles_path) or is_corrupted(): write_defaults()`)
    *   **버전 변경 대응**: 버전 불일치 시 전체 초기화가 아닌, 기존 데이터를 유지하면서 누락된 필드만 기본값으로 채우는 **마이그레이션(Migration)** 로직으로 교체해야 합니다.

**다음 단계 제안:** `web/app.py` 또는 `core/` 디렉터리 내 프로필 관련 파일의 코드 블록을 제공해 주시면 정확한 라인 번호와 수정 코드를 제시할 수 있습니다.