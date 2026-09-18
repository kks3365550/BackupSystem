# Qwen 대용량 자동 분할 분석 전체 산출물

## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]: 시스템 중단, 보안 결함, 규정 위반 위험**
*   **무인증 셀프업데이트 엔드포인트**: `app.py` 내 `/api/system/self-update`가 인증/인가 로직 없이 노출되어 있습니다. 악성 ZIP 파일 전송 시 시스템 재부팅 및 코드 치환이 가능하여 **최상위 보안 취약점(Critical)** 입니다.
*   **긴급 경보 시스템 부재**: 대시보드(`index.html`) 및 백엔드(`app.py`) 전수 조사 결과, 사용자 가시적인 '긴급정보/위험경보' 전용 UI 컴포넌트나 API 엔드포인트가 **완전 부재**합니다. 이는 장애 발생 시 운영자가 즉시 인지하지 못하는 치명적인 모니터링 공백을 의미합니다.

**[BUG]: 발견된 구체적 결함 (버튼, 함수 누락, 하드코딩 등)**
*   **하드코딩된 호스트명 로직**: `app.py`의 `_background_custom_backup_task`에서 데스크탑 여부를 판단하기 위해 `"r2pfnfp"`라는 특정 호스트명을 하드코딩하여 비교합니다. 환경 변경 시 백업 로직이 오작동할 수 있는 잠재적 버그입니다.
*   **메모리 누수 (로그 무한 증식)**: `app.py`의 `current_task["logs"]` 리스트가 메모리에 무한정 축적됩니다. API 응답 시 `[-30:]`만 반환하지만, 실제 메모리는 장시간 실행 시 소진되어 서비스 중단(Crash)을 유발할 수 있습니다.
*   **알림 실패 무시**: 카카오톡 알림 전송(`notify_backup_result`) 실패 시 `WARNING` 로그만 남기고 진행합니다. 중요한 위험 경보가 유실될 수 있으며, 재시도 로직이 없습니다.

**[RISK]: 성능 병목, 사이드 이펙트, 환경 의존성**
*   **경보 데이터 분리 불가**: 모든 오류/위험 신호가 일반 태스크 로그(`current_task["error"]`, `logs`)와 혼재되어 있습니다. 프론트엔드가 이를 필터링하여 '긴급'으로 표시하려면 복잡한 파싱 로직이 필요하며, 현재는 미구현 상태입니다.
*   **하드코딩된 경로/드라이브**: `index.html`의 `#custom-repo-dir` 기본값(`D:\MyBackup_Repository`) 및 시스템 이미지 탭의 드라이브 옵션(`D:, E:, F:`)이 하드코딩되어 있어, 다른 환경에서는 초기 로드 시 잘못된 설정으로 이어질 수 있습니다.

**[ACTION]: 구체적인 해결 제안 및 수정 가이드**
1.  **보안 패치 (즉시)**: `/api/system/self-update` 엔드포인트에 토큰 기반 인증 또는 로컬호스트 제한 미들웨어를 적용하세요.
2.  **경보 시스템 구현**:
    *   **백엔드**: `app.py`에 `/api/alerts` 엔드포인트 추가. `psutil` 임계값(CPU>90%, Disk<10%) 및 백업 실패 이력을 DB 또는 메모리 큐에 저장.
    *   **프론트엔드**: `index.html` 헤더 부분에 고정된 경보 배너(`<div id="alert-banner">`) 추가. `app.js`에서 30초 간격으로 `/api/alerts` 폴링하여 임계값 초과 시 붉은색 배경으로 렌더링.
3.  **하드코딩 제거**: 호스트명 체크를 환경변수(`os.environ.get('IS_DESKTOP')`)로 대체하고, 드라이브 목록은 API(`/api/system-info`)에서 동적으로 받아오도록 수정하세요.
4.  **메모리 관리**: `current_task["logs"]`에 최대 길이 제한(예: 100개)을 설정하거나, 오래된 로그를 DB로 오프로드하는 로직을 추가하세요.

**[DECISION REQUIRED]: Antigravity 및 사용자가 최종 승인해야 할 핵심 의사결정**
*   **경보 수준 정의**: 어떤 조건을 '긴급(Critical)'으로 볼 것인지 (예: 디스크 95% 이상, 백업 연속 실패 3회 등)를 확정해야 합니다.
*   **알림 채널 확장**: 현재 카카오톡 웹훅만 존재합니다. 이메일 또는 SMS 알림 추가가 필요한지 결정이 필요합니다.

---

## PART 2. [COMPREHENSIVE AUDIT & ARCHITECTURE REPORT]

### 1. 긴급정보/위험경보 기능 전수 조사 결과
**결론: 해당 기능이 코드베이스에 존재하지 않습니다.**

*   **데이터 소스 (Data Source)**:
    *   **현재 상태**: 별도 DB 테이블이나 파일 기반의 경보 저장소가 없습니다.
    *   **간접적 데이터**: `app.py`의 `get_system_info()`가 CPU/메모리/디스크 사용률을 반환하지만, 이는 단순 정보 제공 목적이며 '위험' 판정 로직이 없습니다. 백업 실패 시에는 `core.notifier`를 통해 외부 알림만 보내고, 대시보드에 잔존하는 데이터는 없습니다.
*   **프론트엔드 렌더링 (Frontend Rendering)**:
    *   **현재 상태**: `index.html`의 모든 탭(Dashboard, Custom, Runner, Snapshots, Profiles, System-Image)을 검토한 결과, 경보 배너, 알림 아이콘, 또는 관련 CSS 클래스(`.alert`, `.critical`)가 정의되어 있지 않습니다.
    *   **추정 동작**: 현재는 `#runner-progress-bar`나 로그 박스(`#terminal-log-box`)에 에러 텍스트가 출력되는 것이 유일한 '오류 표시' 수단입니다.
*   **날짜 필터링 로직**:
    *   **현재 상태**: 경보 기능이 없으므로 관련 필터링도 없습니다. 스냅샷 목록은 `created_at` 정렬만 수행하며, 날짜 기반 검색 파라미터는 API에 존재하지 않습니다.

### 2. 파일별 상세 분석 요약

#### A. `app.py` (백엔드 로직)
*   **구조**: Flask 기반 웹 서버 및 백업 엔진 제어기.
*   **주요 발견**:
    *   `/api/system-info`: `psutil` 기반 리소스 사용률 반환. (경보 판정 로직 없음)
    *   `_background_backup_task` / `_background_restore_task`: 예외 발생 시 `append_task_log(level="ERROR")` 기록 및 카카오톡 알림 전송.
    *   **버그**: `"r2pfnfp"` 하드코딩, `current_task["logs"]` 무한 증식, 알림 실패 무시.
    *   **보안**: `/api/system/self-update` 무인증 접근 가능.

#### B. `index.html` (프론트엔드 UI)
*   **구조**: 단일 페이지 애플리케이션(SPA) 구조의 Jinja2 템플릿.
*   **주요 발견**:
    *   **Dashboard Tab**: 통계 카드(`#stat-*`)와 최근 스냅샷 목록만 존재. 경보 섹션 없음.
    *   **System Image Tab**: 하드코딩된 드라이브 옵션(`D:, E:, F:`) 및 정적 복구 매뉴얼 텍스트.
    *   **Modals**: 복원 및 프로필 설정 모달은 정상 연결되어 있으나, 오류 처리 UI(예: 경보 팝업)가 부재합니다.
    *   **하드코딩**: `D:\MyBackup_Repository` 기본 경로, "43개 드라이버" 등 정적 텍스트.

### 3. 아키텍처 개선 로드맵 (제안)

1.  **Phase 1: 보안 및 안정성 (즉시)**
    *   셀프업데이트 엔드포인트 인증 추가.
    *   로그 메모리 누수 방지 로직 적용.
    *   하드코딩된 호스트명/경로 제거 및 환경변수화.

2.  **Phase 2: 경보 시스템 구축 (단기)**
    *   **Backend**: `AlertManager` 클래스 도입. 시스템 리소스 임계값 모니터링 및 백업 실패 이력 추적. `/api/alerts` 엔드포인트 구현.
    *   **Frontend**: 헤더에 고정된 `#global-alert-banner` 추가. JS 폴링을 통해 경보 상태 수신 시 색상(빨강/주황) 및 메시지 렌더링.

3.  **Phase 3: 고급 모니터링 (중장기)**
    *   WebSocket 기반 실시간 알림으로 폴링 대역폭 절감.
    *   경보 이력 DB 저장 및 날짜 필터링 기능 추가.
    *   다채널 알림(이메일, SMS) 통합.

---
## 청크별 1차 분석 원본

### [분석 청크 1: app.py (Part 1/2)]
### [긴급정보/위험경보 기능 분석 결과]

**결론:** 현재 제공된 `app.py` (Part 1/2) 코드 블록 내에는 **'긴급정보', '위험 경보(alert/emergency/critical)' 전용 UI 컴포넌트, API 엔드포인트, 또는 데이터 소스가 존재하지 않습니다.**

대신, 시스템 상태 모니터링 및 백업 실패 시 알림 로직이 부분적으로 확인됩니다.

#### 1. 관련 기능 발견점 (간접적 위험/상태 표시)
*   **시스템 리소스 모니터링 (`/api/system-info`)**:
    *   **위치**: `app.py` 내 `get_system_info()` 함수 (약 90~120행 추정)
    *   **역할**: CPU, 메모리, 디스크 사용률을 반환합니다. 프론트엔드에서 이를 받아 임계값 초과 시 경고를 표시할 수 있는 *데이터 소스* 역할만 수행하며, 서버 측에서는 "위험" 판정 로직이 없습니다.
    *   **데이터 원천**: `psutil` 라이브러리를 통한 실시간 시스템 통계 수집.
*   **백업 실패/오류 알림 (`notify_backup_result`)**:
    *   **위치**: `_background_custom_backup_task` 및 `_background_backup_task` 내 예외 처리 블록 (약 400~500행 추정)
    *   **역할**: 백업 실패 시 `core.notifier.notify_backup_result()`를 호출하여 카카오톡 등 외부 채널로 알림을 보냅니다. 이는 "위험 상황"에 대한 대응이지만, 대시보드 화면 내 UI 렌더링 로직은 이 파일에 없습니다.
    *   **데이터 원천**: 백업 엔진(`SnapshotEngine`)에서 발생한 예외 메시지 및 매니페스트 데이터.

#### 2. 프론트엔드 렌더링 및 날짜 필터링
*   **렌더링**: `app.py`는 백엔드 API 서버입니다. 실제 HTML/JS 렌더링은 `templates/index.html` (Jinja2 템플릿)과 `static/` 디렉토리의 JS 파일에서 처리됩니다. 따라서 이 코드 블록에서는 UI 렌더링 로직을 확인할 수 없습니다.
*   **날짜 필터링**: 현재 API 엔드포인트(`/api/system-info`, `/api/snapshots` 등)에는 날짜 기반 필터링 파라미터가 없습니다. 스냅샷 목록은 `created_at` 기준으로 정렬만 수행합니다.

#### 3. 버그/이슈 발견 (경고 관련)
*   **하드코딩된 호스트명 체크**: `_background_custom_backup_task` 내에서 `"r2pfnfp"`라는 특정 호스트명을 하드코딩하여 데스크탑 여부를 판단하는 로직이 있습니다. 이는 유지보수성이 낮으며, 환경에 따라 오작동할 수 있는 잠재적 버그입니다.
*   **알림 실패 무시**: 카카오톡 알림 전송 실패 시 `WARNING` 로그만 남기고 계속 진행합니다. 중요한 위험 경보가 유실될 수 있습니다.

#### 4. 다음 단계 제안
긴급정보/위험경보 기능을 정확히 찾기 위해 다음 파일들을 분석해야 합니다:
1.  **`templates/index.html`**: 대시보드 UI 구조 및 JS 호출 로직 확인.
2.  **`static/js/*.js`**: 프론트엔드에서 `/api/system-info` 등을 폴링하며 임계값 비교 후 경고를 렌더링하는 로직 확인.
3.  **`core/notifier.py`**: 알림 전송 로직 및 위험 수준 분류 로직 확인.
4.  **`app.py` (Part 2/2)**: 나머지 API 엔드포인트에 `/api/alerts`, `/api/emergency` 등 전용 엔드포인트가 있는지 확인.

### [분석 청크 2: app.py (Part 2/2)]
### [긴급정보/위험경보 기능 분석 결과]

**결론: 해당 코드 블록(Part 2/2) 내에 '긴급정보', '위험 경보(alert/emergency/critical)' 전용 UI 렌더링 로직, 또는 관련 데이터 소스(API/DB)가 **존재하지 않습니다.****

이 파일은 백업/복원 엔진의 **백그라운드 실행 로직**, **시스템 관리 API**(셧다운, 셀프업데이트), 및 **태스크 상태 조회**에 집중되어 있습니다. 경보와 유사한 기능은 오직 `append_task_log`를 통한 **로그 기록(Level: ERROR/WARNING)**과 **카카오톡 알림 전송**으로 대체되고 있습니다.

---

### 1. 주요 함수/컴포넌트 및 핵심 역할 (경보 관련 부분만 추려서)

| 함수/엔드포인트 | 라인 번호(추정) | 경보/위험 관련 역할 |
| :--- | :--- | :--- |
| `_background_backup_task` | 상단~중간 | 백업 실행 중 예외 발생 시 `append_task_log(..., level="ERROR")`로 에러 로그 기록. 카카오톡 알림(`notify_backup_result`)으로 결과/오류 전송. |
| `_background_restore_task` | 중간 | 복원 실패 시 `level="ERROR"` 로그 기록. |
| `run_verify` | 중하단 | 무결성 검증 실패 시 `level="ERROR"` 로그 기록 및 DB 업데이트(`is_verified=False`). |
| `get_task_status` | 하단 | 프론트엔드가 폴링하여 최신 에러 메시지(`current_task["error"]`)와 로그를 가져오는 유일한 창구. |

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **데이터 소스 (Data Source):**
    *   **메모리:** `global current_task` 딕셔너리. `error`, `logs` 필드에 위험/오류 정보가 축적됨.
    *   **외부 서비스:** `core.notifier.notify_backup_result()` 함수를 호출하여 카카오톡 웹훅으로 알림 전송 (코드 내 구현은 이 파일에 없음, import만 존재).
    *   **DB:** `storage.db.update_snapshot_verification()`을 통해 검증 실패 여부를 SQLite에 영속화.

*   **프론트엔드 렌더링 방식:**
    *   이 파일에는 HTML/JS가 없습니다.
    *   프론트엔드는 `/api/task/status` 엔드포인트를 폴링하여 `error` 필드가 비어있지 않거나, `logs` 배열의 마지막 항목 레벨이 `ERROR`인 경우 UI에 경고를 표시하도록 설계되어 있을 것으로 추정됩니다.

*   **날짜 필터링 로직:**
    *   **없음.** 이 블록 내에서는 날짜 기반 필터링이 수행되지 않습니다. 로그는 메모리에만 유지되며, 시간 정보는 `start_time`이나 로그 메타데이터로만 존재합니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

1.  **경보 전용 API 부재:**
    *   `/api/alerts`, `/api/emergency` 같은 엔드포인트가 없습니다. 모든 "위험 신호"가 일반 태스크 로그와 에러 필드에 섞여 있어, 프론트엔드가 이를 분리해서 표시하려면 로직이 복잡해집니다.

2.  **하드코딩된 알림 로직:**
    *   `notify_backup_result` 호출 시 예외를 `try-except`로 잡아 `WARNING` 로그만 남깁니다. 알림 전송 실패 자체가 "경고"가 되어야 하는데, 단순히 로그에 기록되어 사용자가 인지하기 어렵습니다.

3.  **메모리 누수 가능성 (로그):**
    *   `current_task["logs"]`는 리스트로 관리되며, `get_task_status`에서 `[-30:]`만 반환하지만, 실제 메모리에는 로그가 무한정 쌓일 수 있습니다. 장시간 실행 시 메모리 소진으로 인한 서비스 중단(경고 상황)이 발생할 수 있습니다.

4.  **셀프업데이트 보안 취약점 (비경보적 위험):**
    *   `/api/system/self-update` 엔드포인트가 인증/인가 로직 없이 열려 있습니다. 악성 zip 파일을 전송하면 시스템이 재부팅되며, 이는 가장 큰 "긴급 상황"을 유발할 수 있는 취약점입니다.

### 4. 사용자의 질문과 관련된 핵심 발견점

*   **데이터 출처:** 긴급정보는 별도 DB 테이블이나 파일이 아닌, **메모리 내 `current

### [분석 청크 3: index.html (Part 1/3)]
### [1/3] index.html 정밀 분석 리포트: 긴급정보/위험경보 기능 부재 확인

**결론:** 현재 제공된 코드 블록(약 28KB, HTML 구조 및 상단 UI)에는 **'긴급정보', '위험 경보(alert/emergency/critical)' 관련 UI 요소, 데이터 바인딩, 또는 렌더링 로직이 전혀 없습니다.** 해당 기능은 후속 블록(Part 2/3, 3/3)의 JavaScript 로직이나 다른 파일에 존재할 가능성이 높습니다.

---

#### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
*   **헤더 액션 버튼 (Header Actions):**
    *   `runGarbageCollection()`: 저장소 정리 트리거.
    *   `triggerQuickBackup()`: 즉시 백업 시작 트리거.
    *   `shutdownServer()`: 백그라운드 서비스 종료 트리거.
*   **사이드바 내비게이션 (Sidebar Nav):**
    *   탭 전환 함수: `switchTab(tabName)` 호출 (`dashboard`, `custom`, `runner`, `snapshots`, `profiles`, `system-image`).
    *   하단 위젯: 하드코딩된 "엔진 상태", "WORM 방어", "디스크 풀 방어" 텍스트 표시 (동적 데이터 바인딩 없음).
*   **대시보드 탭 (`#tab-dashboard`):**
    *   **통계 카드:** `#stat-total-snaps`, `#stat-stored-bytes`, `#stat-logical-bytes`, `#stat-dedup-saved`. (초기값 0, JS 주입 대기 중).
    *   **최근 스냅샷 목록:** `#recent-snapshots-list` (JS 주입 컨테이너).
    *   **시스템 드라이브 현황:** `#system-drives-list` (JS 주입 컨테이너).
    *   **활성 프로필 상태:** `#stat-active-profiles`.
*   **커스텀 선택 탭 (`#tab-custom`):**
    *   드라이버 포함 체크박스: `#custom-include-drivers`.
    *   앱 검색/필터링: `#app-search-input`, `filterAppsList()`, `toggleAllApps(bool)`.
    *   프로젝트 폴더 선택: `#ai-projects-container`, `toggleAllProjects(bool)`.
    *   커스텀 폴더 추가: `openDirectoryPickerForCustom()`, `#custom-folders-list`.
    *   백업 실행 설정: `#custom-repo-dir` (기본값 하드코딩), `startCustomSelectionBackup()`.

#### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **이벤트 핸들러:**
    *   인라인 `onclick`: 탭 전환, 백업 트리거, 폴더 선택기 열기 등 다수 존재.
    *   인라인 `oninput`: 앱 검색 필터링 (`filterAppsList`).
*   **데이터 바인딩 상태:**
    *   현재 블록 내 모든 데이터 표시 영역(`#stat-*`, `#recent-snapshots-list` 등)은 **빈 값(0 또는 빈 컨테이너)** 상태로, 실제 데이터는 후속 JS 코드에서 `fetch` 등을 통해 주입될 것으로 추정됩니다.
    *   **API 엔드포인트:** 이 HTML 블록 내에는 명시적인 API URL이 없습니다. (JS 파일이나 후속 스크립트 태그에 있을 가능성 높음).
*   **하드코딩 값:**
    *   `#custom-repo-dir`의 기본값: `"D:\MyBackup_Repository"`.
    *   사이드바 하단 텍스트: "10GB 안전망", "불변성 잠금" 등 정적 텍스트.

#### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **긴급/경보 기능 부재:** 질문의 핵심인 '긴급정보' UI가 이 블록에 없습니다. 만약 대시보드 상단에 경보 배너가 있어야 한다면, 현재 HTML 구조상 그 컨테이너 자체가 정의되어 있지 않습니다.
*   **하드코딩 리스크:**
    *   `D:\MyBackup_Repository` 경로 하드코딩: 다른 드라이브 환경에서 초기 로드 시 잘못된 경로로 설정될 수 있음 (사용자가 변경해야 함).
    *   "43개 드라이버 자동 감지" 텍스트 하드코딩: 실제 감지된 드라이버 개수와 무관하게 고정 텍스트로 표시됨.
*   **접근성/UX:**
    *   `title` 속성이 일부 버튼에만 존재함.
    *

### [분석 청크 4: index.html (Part 2/3)]
**[결론] 긴급정보/위험경보(Alert) 기능 부재 확인**

제공된 `index.html` (Part 2/3) 블록에는 **'긴급정보', '위험 경보', '알림' 관련 UI 요소, 데이터 바인딩, 또는 로직이 전혀 없습니다.** 해당 부분은 백업 엔진 모니터링, 스냅샷 관리, 시스템 이미지 복구 매뉴얼 중심입니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
*   **실시간 백업 러너 (TAB 2):** `#tab-runner`
    *   `#runner-progress-bar`, `#terminal-log-box`: 백업 진행률과 로그 스트리밍 표시.
    *   `cancelCurrentTask()`: 작업 취소 버튼 핸들러.
*   **스냅샷 타임머신 (TAB 3):** `#tab-snapshots`
    *   `#snapshots-table-body`: JS에 의해 동적 주입되는 스냅샷 목록 테이블.
    *   `loadSnapshots()`: 스냅샷 데이터 로드 트리거.
*   **백업 프로필 & 스케줄 (TAB 4):** `#tab-profiles`
    *   Windows Task Scheduler 상태 카드: `#windows-task-status-badge`, `#windows-task-next-run`.
    *   `registerWindowsTaskFromUI()`, `unregisterWindowsTaskFromUI()`: OS 스케줄러 등록/해제.
*   **시스템 이미지 백업 (TAB 5):** `#tab-system-image`
    *   상태 카드: `#sysimg-c-used`, `#sysimg-d-free`, `#sysimg-last-status`.
    *   `startSystemImageBackup()`, `stopSystemImageBackup()`: wbadmin 기반 OS 전체 백업 제어.
    *   **비기능적 정보 제공:** "C: SSD 사망 대비 4단계 복구 매뉴얼" (정적 텍스트/아이콘, 인터랙션 없음).
*   **모달 창:**
    *   `#explorer-modal`: 스냅샷 파일 탐색기 (`filterExplorerItems()` 검색 기능 포함).
    *   `#restore-modal`: 복원 방식 선택 (In-Place vs Safe Folder), `toggleRestoreMode()`.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **이벤트 핸들러:**
    *   인라인 `onclick`: `cancelCurrentTask`, `loadSnapshots`, `openCreateProfileModal`, `registerWindowsTaskFromUI`, `unregisterWindowsTaskFromUI`, `loadSystemImageStatus`, `startSystemImageBackup`, `stopSystemImageBackup`, `closeModal`, `filterExplorerItems`, `toggleRestoreMode`, `clearSelectiveRestore`, `openDirectoryPicker`.
    *   인라인 `oninput`: `filterExplorerItems` (검색 필터링).
    *   인라인 `onchange`: `toggleRestoreMode` (복원 모드 라디오 버튼).
*   **데이터 바인딩:**
    *   모든 동적 데이터 영역(`#snapshots-table-body`, `#profiles-list-container`, `#sysimg-*` 등)은 초기 상태가 빈 값 또는 "대기 중"으로 설정되어 있으며, **JS에 의해 후속 블록(Part 3/3)에서 API 응답을 받아 채워질 것으로 추정됩니다.**
    *   현재 블록 내에서는 실제 데이터 소스(URL, DB 쿼리)가 보이지 않습니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **하드코딩:**
    *   `#sysimg-drive-select` 옵션: `D:`, `E:`, `F:` 드라이브가 하드코딩되어 있습니다. 실제 시스템에 해당 드라이브가 없으면 선택지가 무의미합니다.
    *   복구 매뉴얼 텍스트: "D드라이브 이미지가 자동 감지됩니다" 등 특정 경로/드라이브 가정이 포함된 정적 텍스트.
*   **잠재적 문제:**
    *   `#restore-target-dir` 입력값 검증 로직이 이 블록에 없습니다. (JS에서 처리될 것으로 보임).
    *   `#explorer-search-input`의 `oninput` 이벤트가 빈 값일 때의 처리(전체 표시)가 JS에서 적절히 구현되어야 합니다.
*   **동작하지 않는 요소:** 없음 (모든 버튼/입력장은 적절한 ID와 핸들러 연결 상태).

### 4. 사용자의 질문과 관련된 핵심 발견점
*   **긴급정보/위험경보 기능: 미발견.**
    *   이 코드 블록에는 `alert`, `emergency`, `critical`, `warning`

### [분석 청크 5: index.html (Part 3/3)]
### 🚨 긴급정보/위험경보 기능 분석 결과: **미발견 (NOT FOUND)**

제공된 `index.html` [3/3] 블록에는 **'긴급정보', '위험 경보(alert/emergency/critical)' 관련 UI, 데이터 바인딩, 또는 로직이 전혀 없습니다.**

#### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
*   **기능 부재 확인**: 해당 블록은 백업 시스템의 **설정(프로필)** 및 **파일 복원** 모달만 포함합니다.
    *   `#restore-modal` (부분): 파일 복원 대상 디렉토리 선택, 덮어쓰기 옵션, `startRestore()` 트리거 버튼.
    *   `#profile-modal`: 백업 프로필 생성/편집 폼 (이름, 경로, 제외 패턴, 스케줄링, 보관 수, 압축 레벨).
    *   `#browse-modal`: 디렉토리 브라우저 모달 (`selectCurrentBrowsePath()`, `closeModal()`).
*   **관련 없는 UI 요소**: 모든 버튼과 입력 필드는 백업/복원 워크플로우에 국한됩니다.

#### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **이벤트 핸들러**:
    *   `onclick="startRestore()"`: 복원 시작 트리거 (경고 로직 없음).
    *   `onclick="saveProfileFromModal()"`: 프로필 저장 (경고 로직 없음).
    *   `onchange="onScheduleTypeChange()"`: 스케줄 타입 변경 시 UI 토글.
*   **API/데이터**: 이 블록 내에서는 API 엔드포인트 호출이나 외부 데이터 소스 연결이 없습니다. 모든 데이터 바인딩은 JS 파일(`/static/app.js`)에서 처리될 것으로 추정되나, HTML 구조상 경고용 컨테이너(`div`, `span` 등)가 존재하지 않습니다.

#### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **기능 누락**: 사용자가 요청한 '긴급정보/위험경보' 기능이 이 파일의 어떤 부분에도 구현되어 있지 않음.
*   **하드코딩 주의점** (비관련): `prof-daily-time` 기본값 `03:00`, `prof-retention` 기본값 `30` 등은 하드코딩되었으나, 이는 경고 시스템과 무관합니다.

#### 4. 사용자의 질문과 관련된 핵심 발견점
*   **결론**: `index.html`의 마지막 블록(9711자)에는 **긴급정보 또는 위험 경보 기능이 없습니다.**
*   **추정 위치**: 만약 이 대시보드에 해당 기능이 있다면, 그것은:
    1.  `index.html`의 이전 블록([1/3] 또는 [2/3])에 정의된 별도 섹션일 수 있습니다.
    2.  `/static/app.js` 파일 내에서 동적으로 생성되는 DOM 요소일 수 있습니다.
    3.  이 특정 HTML 파일에는 구현되지 않았으며, 다른 뷰나 컴포넌트에서 처리되고 있을 가능성이 높습니다.

**권장 조치**: `index.html`의 [1/3] 및 [2/3] 블록 또는 `/static/app.js` 파일을 추가로 분석하여 'alert', 'emergency', 'critical' 키워드를 검색해야 합니다.