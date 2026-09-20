# Qwen 대용량 자동 분할 분석 전체 산출물

## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]: 시스템 중단, 보안 결함, 규정 위반 위험**
*   **UI/UX 치명적 결함 (Critical UX Bug):** `backup_auth.js`의 `openAuthChangeModal()` 함수에서 **로그인 모달(`modal-auth-login`)을 표시하고, 비밀번호 변경 모달(`modal-auth-change`)을 숨기는** 로직 오류가 존재합니다.
    *   **현상:** 사용자가 "비밀번호 변경"을 클릭하면, 비밀번호 변경 입력 필드가 있는 모달이 아닌 **로그인 모달**이 뜹니다.
    *   **결과:** 사용자는 비밀번호 변경을 시도할 수 없으며, 이는 "비밀번호 변경이 작동 안한다"는 제보의 **가장 직접적인 원인**입니다.
    *   **보안 영향:** 간접적 보안 위협은 없으나, 인증 관리 기능의 완전한 마비로 인해 비밀번호 유실 시 복구 불가능한 상태가 될 수 있습니다.

**[BUG]: 발견된 구체적 결함**
1.  **`backup_auth.js` - `openAuthChangeModal()` 함수 로직 오류:**
    *   `loginModal.classList.remove('hidden')` (로그인 모달 표시)
    *   `changeModal.classList.add('hidden')` (변경 모달 숨김)
    *   **수정 필요:** `loginModal`은 `add('hidden')`, `changeModal`은 `remove('hidden')`으로 수정해야 합니다.
2.  **`core/auth.py` - 세션 무효화 후 프론트엔드 미처리:**
    *   `change_master_password()` 실행 시 `_sessions.clear()`로 모든 세션이 즉시 무효화됩니다.
    *   `backup_auth.js`의 `submitAuthChangePassword()`는 성공 후 `alert`와 `openAuthLoginModal()`을 호출하지만, **브라우저 쿠키(`backup_session`)가 여전히 유효한 것처럼 보이는 상태**에서 API 호출 시 401 에러가 발생할 수 있습니다.
    *   **수정 필요:** 성공 시 `document.cookie`를 명시적으로 삭제하거나, 서버가 새 세션 토큰을 반환하도록 `app.py` 엔드포인트를 수정해야 합니다.

**[RISK]: 성능 병목, 사이드 이펙트, 환경 의존성**
*   **파일 권한 의존성:** `core/auth.py`의 `_save_auth_config()`가 `data/auth_config.json`을 수정할 때, 해당 디렉토리에 쓰기 권한이 없으면 `PermissionError`가 발생하여 500 에러로 전파됩니다. (예: Windows에서 읽기 전용 폴더로 실행 시)
*   **경로 하드코딩:** `app.py` 및 `index.html` 내 `D:\MyBackup_Repository` 등 하드코딩된 경로는 사용자 환경에 따라 백업 실패를 유발할 수 있으나, 이는 비밀번호 변경과는 무관한 별도 이슈입니다.

**[ACTION]: 구체적인 해결 제안 및 수정 가이드**
1.  **`backup_auth.js` 수정 (최우선):**
    ```javascript
    function openAuthChangeModal() {
        toggleAuthDropdown();
        const overlay = document.getElementById('auth-modal-overlay');
        const setupModal = document.getElementById('modal-auth-setup');
        const loginModal = document.getElementById('modal-auth-login');
        const changeModal = document.getElementById('modal-auth-change');
        
        if (overlay) overlay.classList.remove('hidden');
        if (setupModal) setupModal.classList.add('hidden');
        if (loginModal) loginModal.classList.add('hidden');   // 수정: 로그인 모달 숨김
        if (changeModal) changeModal.classList.remove('hidden'); // 수정: 변경 모달 표시
        
        // 에러 메시지 초기화
        const errDiv = document.getElementById('change-error');
        if (errDiv) {
            errDiv.innerText = '';
            errDiv.classList.add('hidden');
        }
        
        setTimeout(() => document.getElementById('change-current')?.focus(), 100);
    }
    ```
2.  **`web/app.py` 엔드포인트 수정 (세션 관리):**
    *   `POST /api/auth/change-password` 엔드포인트에서 `change_master_password()` 호출 후, **새 세션 토큰을 생성하여 응답에 포함**하거나, 기존 세션을 유지하도록 `core/auth.py`를 수정합니다.
    *   **권장안:** `core/auth.py`의 `change_master_password()`에서 `_sessions.clear()` 대신, **현재 요청의 세션 토큰만 유지**하거나, `app.py`에서 변경 성공 시 `create_session()`을 호출하여 새 쿠키를 설정합니다.
3.  **`backup_auth.js` - 성공 후 처리 강화:**
    *   성공 시 `alert` 후 `closeAuthModal()`과 `openAuthLoginModal()` 호출 전, **브라우저 쿠키를 명시적으로 삭제**하거나, 서버가 새 세션을 발급하도록 `app.py`를 수정하여 재로그인 없이 세션을 갱신합니다.

**[DECISION REQUIRED]: Antigravity 및 사용자가 최종 승인해야 할 핵심 의사결정**
*   **세션 전략 선택:**
    *   **옵션 A (보안 강화):** 비밀번호 변경 시 모든 세션 무효화 + 즉시 재로그인 유도 (현재 로직 유지, 프론트엔드 UX 개선).
    *   **옵션 B (UX 최적화):** 비밀번호 변경 시 현재 세션만 유지하거나, 새 세션 토큰을 발급하여 재로그인 없이 계속 사용 가능.
    *   **권장:** 옵션 B를 채택하여 사용자 경험을 개선하되, `app.py`에서 새 세션 ��큰을 반환하도록 수정해야 합니다.

---

## PART 2. [COMPREHENSIVE AUDIT & ARCHITECTURE REPORT]

### 1. 전체 파일 구조 및 데이터 흐름
*   **Frontend:** `index.html` (UI 구조), `backup_auth.js` (인증 로직)
*   **Backend:** `web/app.py` (FastAPI 엔드포인트), `core/auth.py` (인증 코어 로직)
*   **데이터 흐름:**
    1.  사용자: `index.html`의 "비밀번호 변경" 버튼 클릭 → `openAuthChangeModal()` 호출.
    2.  `backup_auth.js`: 모달 표시 및 입력 필드 포커스.
    3.  사용자: 입력 후 제출 → `submitAuthChangePassword(event)` 호출.
    4.  `backup_auth.js`: `fetch('/api/auth/change-password', { body: { old_password, new_password } })` 호출.
    5.  `web/app.py`: Pydantic 모델(`AuthChangePasswordRequest`)로 검증 → `core.auth.change_master_password()` 호출.
    6.  `core/auth.py`: `auth_config.json` 수정, `_sessions.clear()` 실행.
    7.  `web/app.py`: 성공 응답 반환.
    8.  `backup_auth.js`: 성공 알림, 모달 닫기, 로그인 모달 표시.

### 2. 청크별 세부 분석 종합

#### [청크 1: backup_auth.js]
*   **핵심 발견:** `openAuthChangeModal()` 함수에서 **로그인 모달을 표시하고 변경 모달을 숨기는 치명적 버그** 발견.
*   **API 호출:** `POST /api/auth/change-password`에 `{ old_password, new_password }` 전송.
*   **DOM 의존성:** `change-current`, `change-new`, `change-new-confirm`, `change-error` ID 사용.

#### [청크 2: app.py (Part 1/5)]
*   **핵심 발견:** `AuthChangePasswordRequest` Pydantic 모델 정의 확인 (`old_password`, `new_password`).
*   **엔드포인트:** `POST /api/auth/change-password` 존재 확인.
*   **세션 문제:** `change_master_password()` 호출 후 세션 처리 누락 가능성 지적.

#### [청크 3~6: app.py (Part 2~5/5)]
*   **분석 결과:** 비밀번호 변경 관련 로직 없음. 백업, 복원, 시스템 관리 로직만 포함.
*   **확인 사항:** `app.py` 전체에서 `/api/auth/change-password` 엔드포인트가 Part 1/5에 정의되어 있음을 확인.

#### [청크 7: core/auth.py]
*   **핵심 발견:** `change_master_password()` 함수에서 `_sessions.clear()`로 모든 세션 무효화.
*   **파일 권한:** `data/auth_config.json` 쓰기 권한 문제 가능성.
*   **판단:** 백엔드 로직 자체는 정상 작동하나, 세션 무효화로 인한 프론트엔드 401 에러 가능성 높음.

#### [청크 8~14: index.html (Part 1~7/7)]
*   **핵심 발견:**
    *   Part 1/7: `openAuthChangeModal()` 트리거 버튼 존재.
    *   Part 6/7: `modal-auth-change` 모달 구조 정의 (`change-current`, `change-new`, `change-new-confirm` input 필드 존재).
    *   Part 7/7: `form-auth-change`의 `onsubmit="submitAuthChangePassword(event)"` 확인.
*   **판단:** HTML 구조는 정상적이며, `backup_auth.js`와 ID가 일치함. 문제는 `backup_auth.js`의 모달 전환 로직에 있음.

### 3. 최종 결론 및 패치 요약

**원인:** `backup_auth.js`의 `openAuthChangeModal()` 함수에서 모달 전환 로직 오류로 인해 **비밀번호 변경 모달이 표시되지 않고 로그인 모달이 표시됨**.

**해결 방안:**
1.  `backup_auth.js`의 `openAuthChangeModal()` 함수 수정 (로그인 모달 숨김, 변경 모달 표시).
2.  (선택) `web/app.py` 및 `core/auth.py` 수정으로 세션 관리 최적화 (재로그인 없이 세션 유지 또는 새 세션 발급).

**검증 절차:**
1.  `backup_auth.js` 수정 후, 브라우저 개발자 도구에서 `openAuthChangeModal()` 호출 시 `modal-auth-change`가 `hidden` 클래스를 제거되고 `modal-auth-login`이 `hidden` 클래스를 추가되는지 확인.
2.  비밀번호 변경 제출 시, 네트워크 탭에서 `POST /api/auth/change-password` 요청이 200 OK를 반환하는지 확인.
3.  성공 후, 대시보드에서 API 호출이 401 에러 없이 정상 작동하는지 확인.

---
## 청크별 1차 분석 원본

### [분석 청크 1: backup_auth.js (Part 1/1)]
# `backup_auth.js` 정밀 분석 보고서

## 1. 주요 함수/컴포넌트 및 핵심 역할

| 함수명 | 역할 |
|--------|------|
| `checkAuthStatus()` | `/api/auth/status` 호출하여 인증 상태 확인 및 UI 업데이트 |
| `updateAuthBadgeUI()` | 인증 상태에 따라 배지 라벨/아이콘/색상 변경 |
| `openAuthSetupModal()` | 최초 비밀번호 설정 모달 표시 |
| `openAuthLoginModal()` | 로그인 모달 표시 |
| `openAuthChangeModal()` | **비밀번호 변경 모달 표시** |
| `closeAuthModal()` | 모달 오버레이 숨김 |
| `submitAuthSetup(e)` | 최초 비밀번호 설정 제출 |
| `submitAuthLogin(e)` / `submitAuthLoginDirect(pw)` | 로그인 제출 |
| `submitAuthLogout()` | 로그아웃 처리 |
| `submitAuthChangePassword(e)` | **비밀번호 변경 제출** |
| `toggleLocalhostBypass()` | 로컬호스트 자동인증 토글 |

---

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

### `submitAuthChangePassword(e)` 상세 분석

```javascript
async function submitAuthChangePassword(e) {
    e.preventDefault();
    const oldP = document.getElementById('change-current').value;
    const newP1 = document.getElementById('change-new').value;
    const newP2 = document.getElementById('change-new-confirm').value;
    const errDiv = document.getElementById('change-error');

    if (newP1 !== newP2) {
        errDiv.innerText = '새 비밀번호가 서로 일치하지 않습니다.';
        errDiv.classList.remove('hidden');
        return;
    }

    try {
        const res = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldP, new_password: newP1 })
        });
        const data = await res.json();
        if (!res.ok) {
            errDiv.innerText = data.error || '비밀번호 변경 실패';
            errDiv.classList.remove('hidden');
            return;
        }
        alert('비밀번호가 성공적으로 변경되었습니다. 다시 로그인해주세요.');
        closeAuthModal();
        openAuthLoginModal();
    } catch (err) {
        errDiv.innerText = '통신 오류가 발생했습니다.';
        errDiv.classList.remove('hidden');
    }
}
```

**API 호출:**
- 엔드포인트: `POST /api/auth/change-password`
- 페이로드: `{ old_password: string, new_password: string }`

**DOM 요소 ID 의존성:**
- `change-current` (현재 비밀번호)
- `change-new` (새 비밀번호)
- `change-new-confirm` (새 비밀번호 확인)
- `change-error` (에러 메시지 표시)

---

## 3. 발견된 버그 및 문제점

### 🔴 **치명적 버그: `openAuthChangeModal()` 함수의 모달 전환 로직 오류**

```javascript
function openAuthChangeModal() {
    toggleAuthDropdown();
    const overlay = document.getElementById('auth-modal-overlay');
    const setupModal = document.getElementById('modal-auth-setup');
    const loginModal = document.getElementById('modal-auth-login');
    const changeModal = document.getElementById('modal-auth-change');
    if (overlay) overlay.classList.remove('hidden');
    if (setupModal) setupModal.classList.add('hidden');
    if (loginModal) loginModal.classList.remove('hidden');  // ❌ BUG: loginModal을 표시
    if (changeModal) changeModal.classList.add('hidden');   // ❌ BUG: changeModal을 숨김
    setTimeout(() => document.getElementById('change-current')?.focus(), 100);
}
```

**문제점:**
1. `loginModal`에 `classList.remove('hidden')` → **로그인 모달이 표시됨**
2. `changeModal`에 `classList.add('hidden')` → **비밀번호 변경 모달이 숨김**
3. 결과: 사용자가 "비밀번호 변경"을 클릭하면 **로그인 모달이 뜨고**, 비밀번호 변경 입력 필드(`change-current`, `change-new`, `change-new-confirm`)는 DOM에 존재하지만 **모달이 숨겨져 있어 접근 불가**
4. `setTimeout`으로 `change-current`에 포커스를 시도하지만, 해당 요소가 숨겨진 모달 안에 있으므로 포커스 실패

**비교: 다른 모달 함수들의 올바른 패턴**

### [분석 청크 2: app.py (Part 1/5)]
# `app.py` [1/5] 블록 정밀 분석 보고서

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록은 FastAPI 애플리케이션의 **초기화, 인증 시스템, 그리고 기본 시스템/스토리지 API**를 정의합니다.

*   **애플리케이션 설정**: `FastAPI` 인스턴스 생성, `lifespan` 컨텍스트 매니저를 통한 스케줄러 및 복제 큐 초기화.
*   **인증 모델 (Pydantic)**:
    *   `AuthSetupRequest`: 마스터 비밀번호 설정 요청.
    *   `AuthLoginRequest`: 로그인 요청.
    *   **`AuthChangePasswordRequest`**: **비밀번호 변경 요청 모델**. 필드: `old_password`, `new_password`.
    *   `AuthBypassRequest`: 로컬 우회 설정.
*   **인증 미들웨어 (`auth_middleware`)**:
    *   `/static`, `/api/auth/`, `/favicon.ico`는 인증 없이 통과.
    *   마스터 비밀번호 미설정 시 진입 허용 (UI에서 셋업 유도).
    *   로컬 IP 바이패스 검사.
    *   세션 토큰(쿠키 `backup_session` 또는 Bearer 헤더) 검증.
    *   API 요청 실패 시 401 JSON 반환, 일반 페이지는 프론트엔드 모달 표시를 위해 통과.
*   **인증 엔드포인트**:
    *   `GET /api/auth/status`: 인증 상태 및 세션 유효성 확인.
    *   `POST /api/auth/setup`: 마스터 비밀번호 최초 설정.
    *   `POST /api/auth/login`: 로그인 및 세션 토큰 발급(쿠키 설정).
    *   `POST /api/auth/logout`: 세션 폐기 및 쿠키 삭제.
    *   **`POST /api/auth/change-password`**: **비밀번호 변경 처리**. `change_master_password` 함수 호출.
    *   `POST /api/auth/toggle-bypass`: 로컬 우회 토글.
*   **시스템/스토리지 API**:
    *   `GET /api/system-info`: CPU(백그라운드 샘플링), 메모리, 디스크 정보.
    *   `GET /api/storage-stats`: 저장소 통계(블롭 수, 중복 제거율 등).
    *   `POST /api/browse-dir`: 디렉터리 탐색.
    *   `GET/POST/DELETE /api/profiles`: 백업 프로필 관리.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API 호출**:
    *   `change_master_password(req.old_password, req.new_password)`가 `POST /api/auth/change-password`에서 호출됨.
    *   `verify_master_password`, `create_session`, `validate_session`, `revoke_session` 등 `core.auth` 모듈 함수들이 인증 흐름에서 사용됨.
*   **데이터 바인딩**:
    *   Pydantic 모델 `AuthChangePasswordRequest`가 JSON 페이로드의 `old_password`와 `new_password` 키를 검증하고 바인딩함.
    *   `req.old_password`와 `req.new_password`가 `change_master_password` 함수의 인자로 전달됨.
*   **세션 관리**:
    *   로그인 시 `create_session()`으로 토큰 생성, `backup_session` 쿠키에 저장.
    *   미들웨어에서 `validate_session(token)`으로 세션 유효성 확인.
    *   로그아웃 시 `revoke_session(token)` 호출 및 쿠키 삭제.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

*   **`change_master_password` 함수의 세션 처리 누락 (중요)**:
    *   `POST /api/auth/change-password` 엔드포인트에서 `change_master_password` 호출 후 **현재 세션 토큰을 폐기하거나 갱신하지 않음**.
    *   `core/auth.py`의 `change_master_password` 구현에 따라, 비밀번호 변경 시 기존 세션이 무효화되거나 유지될 수 있음. 만약 무효화되면, 사용자는 비밀번호 변경 후 즉시 로그아웃 상태가 되어 "변경이 작동 안한다"고 느낄 수 있음 (실제로는 변경은 성공했으나 세션이 끊김).
    *   **해결**: 비밀번호 변경 성공 시, 현재 세션을 폐기하고 새 세션을 발급하거나, 기존 세션을 유지하도록 `core/auth.py`를 수정해야 함.
*   **`AuthChangePasswordRequest`의 `new_password` 길이

### [분석 청크 3: app.py (Part 2/5)]
제공된 `app.py` 코드 블록 (Part 2/5)은 **프로필 관리, 스냅샷 조회/삭제, 설치된 앱/프로젝트 탐색, 그리고 커스텀 백업 실행 로직**을 포함하고 있습니다.

사용자가 제보한 **'비밀번호 변경이 작동 안한다'** 문제와 관련하여, 이 코드 블록 내에는 **`/api/auth/change-password` 엔드포인트가 존재하지 않습니다.**

따라서, 이 블록만으로는 비밀번호 변경 API의 서버 측 로직을 직접 확인하기 어렵습니다. 하지만, **클라이언트(`backup_auth.js`)와 서버(`app.py`) 간의 데이터 흐름을 추론하여, 문제의 원인을 파악하고 해결 방안을 제시할 수 있습니다.**

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할 (이 블록 기준)

*   **Profiles API**:
    *   `list_profiles()`: 저장된 백업 프로필 목록 반환.
    *   `save_profile(profile)`: 새 프로필 저장 및 로그 기록.
    *   `delete_profile(profile_id)`: 프로필 삭제.
*   **Snapshots API**:
    *   `_get_all_candidate_repos()`: 모든 드라이브와 프로필에서 유효한 백업 저장소를 자동 발견하는 헬퍼 함수.
    *   `list_snapshots()`: 모든 저장소의 스냅샷을 조회하고, 오프사이트 복제 상태(`ReplicationQueueManager`)를 포함하여 반환.
    *   `get_snapshot()`: 특정 스냅샷 메타데이터 조회 (대용량 `entries` 배열을 제외하여 성능 최적화).
    *   `browse_snapshot()`, `get_snapshot_tree()`: 스냅샷 내부 파일 탐색.
    *   `delete_snapshot()`: 스냅샷 삭제.
*   **Backup Execution API**:
    *   `RunBackupRequest`, `RunCustomSelectionBackupRequest`: Pydantic 모델 정의.
    *   `_background_custom_backup_task()`: 백그라운드에서 실행되는 커스텀 백업 로직. 드라이버 추출, 프로젝트/앱/커스텀 폴더 수집, 레지스트리 백업 등을 수행.

> **핵심 관찰**: 이 블록에는 **인증(Auth) 관련 API가 전혀 없습니다.** 비밀번호 변경 API는 `app.py`의 다른 부분(예: Part 1/5 또는 Part 3/5)에 있을 가능성이 높습니다.

---

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API 호출**:
    *   `GET /api/profiles`, `POST /api/profiles`, `DELETE /api/profiles/{id}`
    *   `GET /api/snapshots`, `GET /api/snapshots/{id}`, `DELETE /api/snapshots/{id}`
    *   `GET /api/apps/installed`, `GET /api/projects/list`
*   **데이터 바인딩**:
    *   `RunBackupRequest`와 `RunCustomSelectionBackupRequest`는 Pydantic 모델을 사용하여 요청 본문을 검증합니다.
    *   `profile: Dict[str, Any]`는 타입 힌트가 느슨하여, 클라이언트가 보내는 JSON 구조가 서버의 `ConfigManager.save_profile()` 기대값과 일치하지 않으면 런타임 오류가 발생할 수 있습니다.

---

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

1.  **하드코딩된 경로**:
    *   `repo_dir = "D:\\MyBackup_Repository" if os.path.exists("D:\\") else ...`
    *   `candidates.add(os.path.abspath(os.path.join(os.path.expanduser("~"), "MyBackup_Repository")))`
    *   이러한 하드코딩된 경로는 사용자 환경에 따라 실패할 수 있습니다.
2.  **예외 처리의 과다 포괄**:
    *   `except Exception: pass` 또는 `except Exception as e: append_task_log(..., level="WARNING")`
    *   특히 `_background_custom_backup_task`에서 `InterruptedError`를 `Exception`으로 잡지 않고 `raise`하지만, 상위 호출부에서 이를 제대로 처리하지 않으면 백그라운드 태스크가 조용히 실패할 수 있습니다.
3.  **`current_task` 전역 변수 경쟁 조건**:
    *   `global current_task`를 사용하며 `task_lock`으로 보호하지만, `cancel_evt` 체크와 `current_task["progress"]` 업데이트 사이에 경쟁 조건이 발생할 수 있습니다.
4.  **`_get_all_candidate_repos`의 성능 문제**:
    *   모든 마운트된 드라이브를 스캔하고, 각 드라이브에서 `snapshots`와 `blobs` 디

### [분석 청크 4: app.py (Part 3/5)]
제공된 `app.py`의 [3/5] 블록은 **백업(Backup) 로직**에 집중되어 있으며, 사용자가 제보한 **'비밀번호 변경' 기능과 직접적인 관련이 없습니다.**

이 블록에는 `/api/backup/custom-selection` 엔드포인트와 `_background_custom_backup_task` 함수가 포함되어 있으며, 이는 `SnapshotEngine`, `ConfigManager`, `VSS` 등을 사용하여 파일 백업 스냅샷을 생성하고 정리하는 과정입니다.

따라서, **이 코드 블록 내에서 '비밀번호 변경' 관련 버그를 발견할 수 없습니다.**

하지만, 분석 목적에 따라 **전체 시스템 관점에서 '비밀번호 변경이 작동하지 않는' 원인을 추론하고, 이 블록이 간접적으로 영향을 줄 수 있는 부분(세션/인증 상태)을 점검**한 결과를 요약합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할 (본 블록 기준)

*   **`_background_custom_backup_task` (부분 포함)**:
    *   **역할**: 사용자 선택 폴더에 대한 백업 작업을 백그라운드에서 실행합니다.
    *   **핵심 로직**:
        1.  `ConfigManager`에서 프로필(`prof_custom_selected`)을 로드하거나 생성합니다.
        2.  `SnapshotEngine.create_snapshot`을 호출하여 실제 백업 스냅샷을 생성합니다.
        3.  `SnapshotEngine.prune_snapshots`로 오래된 스냅샷을 정리합니다.
        4.  `ConfigManager.save_profile`로 마지막 실행 상태(`last_run`, `last_status`)를 업데이트합니다.
        5.  `notify_backup_result`로 카카오톡 알림을 전송합니다.
*   **`run_custom_selection_backup` (API 엔드포인트)**:
    *   **역할**: `POST /api/backup/custom-selection` 요청을 받아 백업 태스크를 시작합니다.
    *   **핵심 로직**: `current_task`의 `running` 상태를 확인하여 중복 실행을 방지하고, `BackgroundTasks`에 백업 태스크를 등록합니다.

> **결론**: 이 블록은 **백업 도메인**에만 해당하며, 인증(Auth)이나 비밀번호 변경 로직은 포함하지 않습니다.

---

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API 엔드포인트**: `POST /api/backup/custom-selection`
*   **입력 모델**: `RunCustomSelectionBackupRequest` (Pydantic 모델, 이 블록에 정의되지 않음)
*   **데이터 흐름**:
    1.  클라이언트 -> `run_custom_selection_backup`
    2.  `current_task` 상태 업데이트 (Locking)
    3.  `background_tasks.add_task(_background_custom_backup_task, req.dict())`
    4.  백그라운드에서 `ConfigManager`, `SnapshotEngine` 호출
*   **데이터 바인딩**:
    *   `params` (dict)에서 `sources`, `repo_dir`, `exclude_patterns`, `compression_level` 등을 추출합니다.
    *   `ConfigManager.get_profile("prof_custom_selected")`를 통해 기존 설정을 로드하고, 없으면 기본값으로 생성합니다.

---

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

이 블록 자체의 버그는 다음과 같습니다:

1.  **하드코딩된 경로**:
    *   `repo_dir = "D:\\MyBackup_Repository" if os.path.exists("D:\\") else ...`
    *   **문제**: `D:` 드라이브가 존재하지 않거나 권한이 없는 경우 폴백 로직이 작동하지만, `D:` 드라이브가 존재하지만 백업 저장소로 적합하지 않은 경우(예: 시스템 드라이브)에도 무조건 `D:`를 우선시하는 경향이 있습니다.
2.  **프로필 ID 하드코딩**:
    *   `profile_id = "prof_custom_selected"`
    *   **문제**: 모든 '사용자 선택 백업'이 동일한 프로필 ID를 공유합니다. 사용자가 여러 개의 다른 선택 백업 프로필을 만들 수 없습니다.
3.  **예외 처리 누락**:
    *   `ConfigManager.get_profile` 또는 `save_profile`에서 발생할 수 있는 파일 I/O 오류가 `try-except` 블록 내에서 포착되지 않을 수 있습니다 (이 블록의 `try`는 `SnapshotEngine` 호출 전후를 감싸지만, 프로필 저장 실패 시 `manifest` 생성 전에 실패할 수 있음).
4.  **메모리 누수 가능성**:

### [분석 청크 5: app.py (Part 4/5)]
제공된 `app.py`의 [4/5] 블록은 **백업/복원 실행, 무결성 검증, Windows 스케줄러, 시스템 이미지, 시스템 종료, 그리고 원격 자가 업데이트(Self-Update)** 로직을 포함하고 있습니다.

사용자가 제보한 **'비밀번호 변경이 작동 안한다'** 는 문제와 관련하여, 이 코드 블록 내에는 **`/api/auth/change-password` 엔드포인트가 존재하지 않습니다.**
따라서 이 블록 자체에는 비밀번호 변경 로직이 없으므로, 원인은 다른 블록(보통 `app.py`의 앞부분 또는 `core/auth.py`)에 있을 가능성이 높습니다.

하지만, 요청하신 5가지 항목에 대해 **이 블록의 내용과 전체 시스템 맥락**을 고려하여 정밀 분석 및 해결 방안을 제시합니다.

---

### 1. `index.html`에서 비밀번호 변경 모달 분석 (전제 조건 기반 추론)
*이 블록에는 HTML이 없으므로, 일반적인 구조와 `backup_auth.js`와의 정합성을 위해 표준적인 구현을 가정하여 분석합니다.*

*   **Input ID**: 일반적으로 `change-current`, `change-new`, `change-new-confirm` 또는 `old-password`, `new-password`, `confirm-password` 형태입니다.
*   **Form onsubmit**: `submitAuthChangePassword(event)` 함수를 호출해야 합니다.
*   **필드명**: JS에서 `FormData` 또는 `JSON.stringify`로 전송할 때 사용하는 키 이름입니다.

> **핵심 체크포인트**: `index.html`의 input `id`와 `backup_auth.js`에서 `document.getElementById()`로 접근하는 ID가 **완전히 일치**해야 합니다. (예: HTML에 `id="old_pwd"`인데 JS에서 `getElementById('old_password')`를 호출하면 `null`이 되어 에러가 발생합니다.)

### 2. `backup_auth.js`의 함수 및 HTML 요소 ID 일치성 분석
*이 블록에는 JS가 없으므로, `app.py`의 API 스펙을 기준으로 JS가 보내야 할 페이로드를 역추적합니다.*

*   **`openAuthChangeModal`**: 모달을 열고 input 필드를 초기화(빈 값으로 설정)하는 함수입니다.
*   **`submitAuthChangePassword(event)`**:
    1.  `event.preventDefault()` 호출.
    2.  HTML input 값(`old_password`, `new_password`)을 수집.
    3.  `fetch('/api/auth/change-password', { method: 'POST', body: JSON.stringify({...}) })` 호출.
*   **일치성 검증**:
    *   만약 `backup_auth.js`가 `old_password` 키를 보내는데, `app.py`의 Pydantic 모델이 `current_password`를 기대하면 **422 Unprocessable Entity** 에러가 발생합니다.
    *   **발견점**: `app.py` [4/5] 블록에는 auth 관련 코드가 없으므로, **`app.py`의 다른 블록(1~3) 또는 `core/auth.py`에서 정의된 Pydantic 모델의 필드명**을 확인해야 합니다.

### 3. `web/app.py`의 `POST /api/auth/change-password` 엔드포인트 및 Pydantic 모델 필드명
*이 블록(4/5)에는 해당 엔드포인트가 없습니다. 하지만 자가 업데이트(`self_update`) 부분에서 `Request` 객체를 직접 처리하는 방식을 볼 수 있습니다.*

*   **일반적인 FastAPI Auth 엔드포인트 패턴**:
    ```python
    class ChangePasswordRequest(BaseModel):
        old_password: str
        new_password: str
        # confirm_password: str (클라이언트 측 검증용, 서버는 보통 무시하거나 확인)

    @app.post("/api/auth/change-password")
    def change_password(req: ChangePasswordRequest):
        # core.auth.change_master_password 호출
    ```
*   **불일치 가능성**:
    *   `backup_auth.js`가 `{"old_password": "...", "new_password": "..."}`를 보내는데,
    *   `app.py`의 Pydantic 모델이 `{"current_password": "...", "new_password": "..."}`를 정의했다면 **필드명 불일치**로 인해 요청이 실패합니다.
    *   **해결**: `app.py`의 `ChangePasswordRequest` 모델 필드명과 `backup_auth.js`의 JSON 키를 **완전히 일치**시켜야 합니다.

### 4. `core/auth.py`의 `change_master_password` 로직 및 세션/파일 권한 문제
*이 블록에는 `core/auth.py` 코드가 없지만, `app.py`의 자가 업데이트 부분에서 `BASE_DIR`과 `keys` 폴더를 참조하는 것을 볼 수

### [분석 청크 6: app.py (Part 5/5)]
제공된 `app.py`의 [5/5] 블록은 **업데이트 패키지 검증/적용 로직**과 **실시간 알림 요약 API**를 포함하고 있습니다.

사용자가 제보하신 **'비밀번호 변경이 작동 안한다'** 문제는 이 코드 블록(5/5)에 직접적인 원인이 포함되어 있지 않습니다. 이 블록은 `POST /api/update` (전자서명 검증 및 재시작)와 `GET /api/alerts/summary` (백업 실패, 디스크 용량, 복제 대기열 상태 조회)만을 처리합니다.

따라서, 요청하신 5가지 항목에 대해 이 블록의 관점에서 분석한 결과는 다음과 같습니다.

### 1. `index.html`에서 비밀번호 변경 모달의 input id, 폼 onsubmit 핸들러, 필드명
*   **분석 결과:** 이 `app.py` 블록에는 `index.html`의 DOM 구조나 `submitAuthChangePassword` 이벤트 핸들러에 대한 참조가 **없습니다**.
*   **판단:** HTML/JS 계층의 문제는 이 Python 백엔드 블록에서 확인 불가합니다. `index.html`과 `backup_auth.js` 파일을 별도로 확인해야 합니다.

### 2. `backup_auth.js`의 `openAuthChangeModal` 및 `submitAuthChangePassword` 함수와 HTML 요소 ID 일치 여부
*   **분석 결과:** 이 `app.py` 블록에는 `backup_auth.js`의 함수 정의나 HTML ID(`change-current`, `change-new` 등)에 대한 참조가 **없습니다**.
*   **판단:** 프론트엔드 로직의 불일치는 이 블록에서 확인 불가합니다.

### 3. `web/app.py`의 `POST /api/auth/change-password` 엔드포인트 및 Pydantic 모델 필드명 일치 여부
*   **분석 결과:** 제공된 [5/5] 블록에는 `/api/auth/change-password` 엔드포인트가 **정의되어 있지 않습니다**.
*   **판단:**
    *   이 블록은 `/api/update` (부분적으로)와 `/api/alerts/summary`만 포함합니다.
    *   **핵심 의심점:** `app.py`의 다른 블록(1~4)에 `/api/auth/change-password` 엔드포인트가 존재할 가능성이 높습니다. 만약 해당 엔드포인트가 `app.py` 전체에서 **전혀 정의되지 않았다면**, `backup_auth.js`가 전송하는 요청은 `404 Not Found` 또는 `405 Method Not Allowed` 에러를 반환할 것입니다.
    *   **확인 필요:** `app.py`의 앞선 블록(1~4)에서 `@app.post("/api/auth/change-password")` 또는 유사한 라우터가 존재하는지 확인해야 합니다.

### 4. `core/auth.py`의 `change_master_password` 로직 및 세션 검증/파일 권한 문제
*   **분석 결과:** 이 `app.py` 블록에는 `core.auth` 모듈의 `change_master_password` 함수 호출이 **없습니다**.
*   **판단:**
    *   `app.py`의 다른 블록에서 `core.auth.change_master_password`를 호출하는 엔드포인트가 있을 것입니다.
    *   만약 `app.py`에서 해당 함수를 호출하지 않거나, `core/auth.py` 내부에서 파일 권한(예: `master_password.json` 쓰기 권한)이나 세션 검증 로직에 버그가 있다면, 이는 `app.py`의 [5/5] 블록과 무관합니다.

### 5. 정확한 원인과 구체적인 해결 패치 방안

**이 [5/5] 블록 자체는 '비밀번호 변경' 기능과 무관합니다.**
그러나, 전체 시스템의 맥락에서 '비밀번호 변경이 작동 안한다'는 문제를 해결하기 위해 **이 블록과 다른 블록을 연결하여** 다음과 같은 가능성을 점검해야 합니다.

#### 🔍 핵심 발견점 및 원인 추정

1.  **엔드포인트 누락 가능성 (가장 유력)**
    *   `app.py`의 [5/5] 블록에는 인증 관련 API가 없습니다.
    *   **확인 사항:** `app.py`의 [1/5]~[4/5] 블록에서 `@app.post("/api/auth/change-password")` 또는 `@app.post("/api/auth/password")` 라우터가 존재하는지 확인하세요.
    *   **만약 없다면:** `backup_auth.js`가 `fetch('/api/auth/change-password', ...)`를 호출해도 서버가 404를 반환합니다.
    *   **패치:** `app.py`에 엔드포인트 추가.
        ```python
        from pydantic import BaseModel
        from core.auth import change_master_password

        class ChangePasswordRequest(Base

### [분석 청크 7: auth.py (Part 1/1)]
# `core/auth.py` 정밀 분석 보고서

## 1. 주요 함수/컴포넌트 및 핵심 역할

`core/auth.py`는 웹 대시보드의 마스터 비밀번호 인증 및 세션 관리를 담당하는 백엔드 코어 모듈입니다.

*   **암호화 엔진**: `PBKDF2-HMAC-SHA256` (100,000 iterations)을 사용하여 비밀번호를 해시화합니다.
*   **설정 관리**: `data/auth_config.json` 파일을 통해 비밀번호 해시, 솔트, 세션 TTL 등을 관리합니다.
*   **세션 관리**: 인메모리 딕셔너리(`_sessions`)를 사용하여 64바이트 URL-Safe 토큰을 발행하고 만료 시간을 추적합니다.
*   **핵심 함수**:
    *   `change_master_password(old_password, new_password)`: 기존 비밀번호 검증 후 새 비밀번호로 교체하고, **모든 활성 세션을 만료시킵니다**.
    *   `verify_master_password(password)`: 입력된 비밀번호와 저장된 해시를 비교합니다.
    *   `create_session()` / `validate_session(token)`: 세션 토큰의 생성과 유효성 검사.

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API 엔드포인트 연동**: 이 파일은 직접 HTTP 요청을 처리하지 않으며, `web/app.py`의 `POST /api/auth/change-password` 엔드포인트에서 호출되는 백엔드 로직입니다.
*   **데이터 흐름**:
    1.  프론트엔드(`backup_auth.js`)가 `old_password`, `new_password`를 JSON으로 전송.
    2.  `web/app.py`가 Pydantic 모델로 검증 후 `change_master_password()` 호출.
    3.  `change_master_password()`가 `auth_config.json`을 수정하고 `_sessions.clear()`를 실행.
*   **상태 변경**: 비밀번호 변경 성공 시, 현재 로그인된 사용자의 세션 토큰은 즉시 무효화됩니다.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

### [중요] 세션 무효화 로직의 의도적 동작 (버그가 아닌 설계)
`change_master_password` 함수의 마지막 부분:
```python
        _save_auth_config(config)
        # 비밀번호 변경 시 기존 모든 활성 세션 만료
        _sessions.clear()
        return True
```
*   **분석**: 비밀번호 변경 성공 시 **모든 활성 세션이 즉시 삭제**됩니다.
*   **영향**: 사용자가 비밀번호를 변경한 직후, 현재 브라우저 탭의 세션 토큰은 더 이상 유효하지 않게 됩니다. 이후 API 호출 시 `validate_session`이 `False`를 반환하여 401 Unauthorized 에러가 발생할 수 있습니다.
*   **판단**: 이는 보안상 권장되는 동작이지만, 프론트엔드가 이를 처리하지 못하면 "비밀번호 변경 후 대시보드가 멈춘다"는 현상으로 이어질 수 있습니다.

### [잠재적 문제] 파일 권한 및 원자적 교체
*   `_save_auth_config`에서 `os.replace(temp_path, path)`를 사용합니다.
*   **리스크**: `data` 디렉토리에 쓰기 권한이 없거나, `auth_config.json`이 읽기 전용으로 설정되어 있으면 `PermissionError`가 발생합니다. 이 예외는 `change_master_password`에서 잡히지 않아 API 레벨에서 500 에러로 전파됩니다.

### [잠재적 문제] `old_password` 검증 누락
*   `change_master_password`에서 `old_password`가 비어있거나 `None`인 경우를 명시적으로 체크하지 않습니다.
*   `test_hash = _hash_password(old_password, salt)`에서 `old_password`가 `None`이면 `AttributeError`가 발생할 수 있습니다 (Pydantic 모델이 `str` 타입으로 강제하지 않는다면).

## 4. 사용자의 질문과 관련된 핵심 발견점

**사용자 제보: "비밀번호 변경이 작동 안한다"**

이 코드를 분석한 결과, **백엔드 로직 자체는 정상적으로 작동**합니다. 그러나 다음과 같은 시나리오에서 "작동 안한다"는 현상이 발생할 수 있습니다:

1.  **세션 만료로 인한 401 에러**:
    *   비밀번호 변경 성공 → `_sessions.clear()` → 현재 세션 무효화.
    *   프론트엔드가 비밀번호 변경 성공 후 **자동으로 재로그인**하거나 **새 세션 ������

### [분석 청크 8: index.html (Part 1/7)]
제공된 `index.html`의 [1/7] 블록(12,984자)을 정밀 분석한 결과, **비밀번호 변경 모달의 실제 DOM 구조(HTML 태그)는 이 블록에 포함되어 있지 않습니다.**

이 블록은 주로 **헤더(Header)**, **사이드바(Sidebar)**, **대시보드 통계 카드(Stat Cards)** 및 **전역 알림 배너**를 정의하고 있습니다.

사용자가 제보한 "비밀번호 변경이 작동 안한다"는 문제를 해결하기 위해, 이 블록에서 발견된 **관련 이벤트 핸들러**와 **결정적 단서**를 분석하고, 나머지 블록(2~7)에서 확인해야 할 핵심 사항을 명시합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할 (Part 1/7 기준)

*   **보안 인증 드롭다운 (`#auth-dropdown`)**:
    *   **역할**: 비밀번호 변경, 로컬 자동로그인 토글, 로그아웃 기능을 제공하는 메뉴.
    *   **핵심 버튼**: `onclick="openAuthChangeModal()"`
        *   이 버튼이 클릭되면 `backup_auth.js`의 `openAuthChangeModal()` 함수가 호출됩니다.
        *   **중요**: 이 함수가 모달을 생성하거나 기존 모달을 표시하는 로직을 포함해야 합니다.
*   **대시보드 통계 (`#tab-dashboard`)**:
    *   `#stat-total-snaps`, `#stat-stored-bytes` 등 ID를 가진 요소들이 있습니다.
    *   이는 백업 상태와 직접적인 연관은 없으나, API 호출 성공 여부에 따라 값이 갱신되는 UI입니다.
*   **전역 알림 배너 (`#global-alert-banner`)**:
    *   `dismissAlertBanner()` 핸들러를 가집니다.
    *   비밀번호 변경 실패 시, 이 배너를 통해 에러 메시지를 표시할 가능성이 높습니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **`openAuthChangeModal()`**:
    *   **위치**: `index.html` Part 1/7의 헤더 드롭다운 버튼.
    *   **동작**: `backup_auth.js`에서 정의된 함수를 호출합니다.
    *   **상태**: 이 함수가 실행될 때, HTML에 존재하는 모달 요소(예: `#auth-change-modal`)를 `hidden` 클래스를 제거하여 표시하거나, 동적으로 DOM을 생성해야 합니다.
*   **`submitAuthChangePassword(event)`**:
    *   **위치**: **Part 1/7에 없음.**
    *   **추정 위치**: Part 2~7 중 모달 HTML이 정의된 블록 또는 `backup_auth.js` 내부.
    *   **기대 동작**: 폼 제출 시 `event.preventDefault()`를 호출하고, `fetch`로 `/api/auth/change-password`에 POST 요청을 보내야 합니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

**Part 1/7 자체에서는 버그가 발견되지 않았습니다.** 그러나 **문제의 원인은 Part 1/7 이후의 블록(모달 HTML)과 `backup_auth.js`의 불일치**에서 찾을 가능성이 높습니다.

*   **결정적 단서**: `openAuthChangeModal()`이 호출되지만, 모달이 나타나지 않거나, 모달이 나타나도 제출 버튼이 반응하지 않는다면:
    1.  **모달 HTML 누락**: `index.html`의 나머지 블록(2~7)에 `id="auth-change-modal"` 또는 유사한 ID를 가진 `<div>`가 존재하지 않거나, `hidden` 클래스가 제거되지 않는 경우.
    2.  **ID 불일치**: `backup_auth.js`가 `document.getElementById('change-current')` 등을 참조하는데, HTML의 input ID가 `current-password` 등으로 다른 경우.
    3.  **JS 로드 순서**: `backup_auth.js`가 `index.html`의 `<body>` 끝부분에서 로드되지 않거나, `tailwind.js`/`lucide.min.js` 로드 실패로 인해 UI가 깨진 경우.

### 4. 사용자의 질문과 관련된 핵심 발견점 및 다음 단계 분석 계획

**현재 Part 1/7 분석 결과:**
*   `openAuthChangeModal()` 트리거는 정상적으로 정의되어 있습니다.
*   **비밀번호 변경 모달의 실제 input 필드(`change-current`, `change-new`, `change-new-confirm`)는 이 블록에 없습니다.**

**다음 블록(2~7) 및 `backup_auth.js`,

### [분석 청크 9: index.html (Part 2/7)]
제공된 `index.html`의 [2/7] 블록은 대시보드의 **홈 탭(Overview)**과 **백업 항목 직접 선택 탭(Custom Item Selector)**의 UI 구조를 포함하고 있습니다.

사용자가 제보한 **'비밀번호 변경이 작동 안한다'** 문제와 관련하여, 이 블록 내에는 **비밀번호 변경 모달(Modal)이나 관련 폼(Form)이 존재하지 않습니다.**

따라서 이 블록 자체에는 버그가 없으며, 문제의 원인은 다른 블록(모달 정의 부분) 또는 백엔드/JS 로직에 있을 가능성이 높습니다. 하지만 요청하신 5가지 항목에 대해 현재 코드 컨텍스트 내에서 확인 가능한 범위와, **이 블록이 전체 시스템에서 차지하는 위치를 고려한 분석**을 수행합니다.

---

### 1. `index.html`에서 비밀번호 변경 모달의 input id, 폼 onsubmit 핸들러, 필드명
**분석 결과: 해당 블록 내 미발견**

*   **현재 블록 내용:**
    *   `#tab-overview` (홈 탭): 통계 카드(`stat-logical-bytes`, `stat-dedup-saved`), 최근 스냅샷 목록(`recent-snapshots-list`), 시스템 드라이브 현황(`system-drives-list`), 활성 백업 프로필 상태(`stat-active-profiles`), OS 베어메탈 백업 배너.
    *   `#tab-custom` (백업 항목 직접 선택 탭): 드라이버 체크박스(`custom-include-drivers`), 설치된 앱 검색/목록(`app-search-input`, `installed-apps-container`), 개인 AI 프로젝트 목록(`ai-projects-container`).
*   **결론:**
    *   `change-current`, `change-new`, `change-new-confirm`과 같은 ID를 가진 `<input>` 태그가 **이 블록에 없습니다.**
    *   `submitAuthChangePassword(event)`와 같은 `onsubmit` 핸들러도 **이 블록에 없습니다.**
    *   **추정:** 비밀번호 변경 모달은 `index.html`의 다른 블록(예: Part 1/7의 헤더/설정 메뉴, 또는 Part 3~7의 모달 정의 섹션)에 정의되어 있을 것입니다.

### 2. `backup_auth.js`의 `openAuthChangeModal` 및 `submitAuthChangePassword` 함수와 HTML 요소 ID 일치 여부
**분석 결과: 현재 블록으로 검증 불가, 그러나 UI 구조상 간접적 단서 제공**

*   **현재 블록의 UI 패턴:**
    *   이 블록은 `onclick` 이벤트 핸들러를 통해 JS 함수를 호출하는 패턴을 사용합니다.
        *   예: `onclick="switchTab('snapshots')"`, `onclick="loadCustomSelectionData()"`, `onclick="toggleAllApps(true)"`.
    *   **잠재적 문제점:** 만약 `backup_auth.js`의 `openAuthChangeModal`이 모달을 열 때, 모달 내부의 input ID가 HTML 정의와 다르면 `document.getElementById('change-current')` 등이 `null`을 반환하여 `TypeError`가 발생할 수 있습니다.
    *   **확인 필요 사항:** `index.html`의 **모달 정의 블록**(아직 제공되지 않음)에서 `id="change-current"`, `id="change-new"`, `id="change-new-confirm"`이 정확히 존재하는지 확인해야 합니다.

### 3. `web/app.py`의 `POST /api/auth/change-password` Pydantic 모델 필드명과 `backup_auth.js` JSON 페이로드 일치 여부
**분석 결과: 현재 블록으로 검증 불가**

*   **현재 블록의 API 호출:**
    *   이 블록은 직접적인 `fetch` 또는 `axios` 호출을 포함하지 않습니다. 모든 데이터 로딩은 `loadCustomSelectionData()`와 같은 JS 함수를 통해 간접적으로 수행됩니다.
*   **추정:**
    *   `backup_auth.js`의 `submitAuthChangePassword` 함수가 `fetch('/api/auth/change-password', { method: 'POST', body: JSON.stringify({ old_password: ..., new_password: ... }) })`를 호출할 것입니다.
    *   **잠재적 버그:** `web/app.py`의 Pydantic 모델이 `old_password` 대신 `current_password`를 요구하거나, `new_password` 대신 `password`를 요구하는 경우 422 Unprocessable Entity 에러가 발생합니다.

### 4. `core/auth.py`의 `change_master_password` 로직 및 세션 검증/파일 권한 문제
**분석 결과: 현재 블록으로 검증 불가**

*   **현재 블록의 관련성:** 없음.
*   **잠재적 문제점 (일반적 패턴 기반 추론):**
    *   **

### [분석 청크 10: index.html (Part 3/7)]
제공된 `index.html`의 [3/7] 블록은 **백업 실행 설정(Tab 1의 우측 패널), 실시간 백업 러너(Tab 2), 스냅샷 타임머신(Tab 3), 백업 프로필(Tab 4의 일부)** 영역을 포함하고 있습니다.

사용자가 제보한 **'비밀번호 변경이 작동 안한다'** 문제와 관련하여, 이 블록 내에는 **비밀번호 변경 모달(Modal)이나 관련 Input 요소가 포함되어 있지 않습니다.**

따라서 이 블록 자체에서는 비밀번호 변경 로직의 버그를 직접 발견할 수 없으며, 분석 목적에 따라 **이 블록이 전체 시스템에서 차지하는 역할**과 **비밀번호 변경 문제 해결을 위해 다른 블록(특히 `backup_auth.js`, `web/app.py`, `core/auth.py`)에서 확인해야 할 사항**을 구조화하여 요약합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할 (본 블록 기준)

이 블록은 **백업 실행 및 모니터링 UI**를 담당합니다.

| UI 요소 ID / 클래스 | 역할 | 관련 함수 (onclick) |
| :--- | :--- | :--- |
| `custom-repo-dir` | 백업 저장소 경로 입력 | `openDirectoryPicker('custom-repo-dir')` |
| `custom-profile-name` | 백업 프로필 이름 입력 | - |
| `custom-save-profile` | 프로필 저장 체크박스 | - |
| `startCustomSelectionBackup()` | **백업 실행 버튼** | `startCustomSelectionBackup()` |
| `tab-runner` | 실시간 백업 진행 상태 탭 | - |
| `runner-status-badge` | 백업 상태 표시 (대기/진행/완료) | - |
| `runner-cancel-btn` | 백업 작업 취소 버튼 | `cancelCurrentTask()` |
| `runner-progress-bar` | 백업 진행률 바 | - |
| `terminal-log-box` | 실시간 로그 출력 영역 | - |
| `tab-snapshots` | 스냅샷 목록 탭 | - |
| `snapshots-table-body` | 스냅샷 테이블 본문 (JS로 주입) | `loadSnapshots()` |
| `tab-profiles` | 백업 프로필 관리 탭 | - |
| `openCreateProfileModal()` | 새 프로필 생성 모달 열기 | `openCreateProfileModal()` |

> **핵심 관찰:** 이 블록은 **인증(Auth)과 무관한 백업 기능 UI**입니다. 비밀번호 변경 모달은 일반적으로 `index.html`의 다른 블록(예: 설정 탭, 사용자 관리 탭, 또는 페이지 하단 모달 영역)에 위치할 가능성이 높습니다.

---

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태 (본 블록 기준)

- **이벤트 핸들러:**
  - `openDirectoryPickerForCustom()`: 사용자 정의 폴더 추가
  - `openDirectoryPicker('custom-repo-dir')`: 저장소 폴더 선택
  - `startCustomSelectionBackup()`: 백업 시작 (API 호출 예상: `POST /api/backup/start` 등)
  - `cancelCurrentTask()`: 백업 취소 (API 호출 예상: `POST /api/backup/cancel`)
  - `loadSnapshots()`: 스냅샷 목록 로드 (API 호출 예상: `GET /api/snapshots`)
  - `openCreateProfileModal()`: 프로필 생성 모달 열기

- **데이터 바인딩:**
  - `summary-drivers-badge`, `summary-apps-count`, `summary-projects-count`, `summary-custom-count`: 백업 대상 요약 정보 표시
  - `runner-current-file`, `runner-percent-text`, `runner-stats-text`: 실시간 백업 상태 업데이트 (WebSocket 또는 폴링)

> **비밀번호 변경 관련:** 이 블록에는 `submitAuthChangePassword` 또는 `change-password` 관련 이벤트 핸들러가 **존재하지 않습니다.**

---

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소 (본 블록 기준)

- **하드코딩:**
  - `value="D:\MyBackup_Repository"`: 백업 저장소 기본 경로가 하드코딩되어 있음. 사용자 환경에 따라 오류 발생 가능.
  - `value="내 맞춤형 선택 백업"`: 프로필 이름 기본값 하드코딩.
  - `D: 드라이브 (여유: 908 GB 넉넉함)`: 디스크 용량 정보가 하드코딩되어 있음. 실제 시스템과 불일치 가능.

- **예외 누락:**
  - `startCustomSelectionBackup()` 호출 시 백업 �����

### [분석 청크 11: index.html (Part 4/7)]
제공된 `index.html`의 [4/7] 블록은 **백업 프로필 관리**, **Windows OS 작업 스케줄러**, **시스템 이미지(베어메탈) 백업** 탭의 UI 구조를 포함하고 있습니다.

사용자가 제보한 **'비밀번호 변경이 작동 안한다'** 문제는 이 블록(4/7)에 직접적으로 존재하지 않습니다. 이 블록은 백업 관련 UI이며, 인증/비밀번호 변경 모달은 다른 블록(보통 초기화면 또는 설정 탭)에 위치할 가능성이 높습니다.

하지만, 요청하신 분석 목적에 따라 **이 블록 내에서 발견된 잠재적 문제점**과 **비밀번호 변경 문제와 연관될 수 있는 구조적 단서**를 정밀 분석하여 요약합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록은 `tab-system-image` (시스템 이미지 백업)와 백업 프로필 관리 영역을 다룹니다.

| 요소 ID / 클래스 | 역할 | 관련 함수 (onclick) |
| :--- | :--- | :--- |
| `profiles-list-container` | 백업 프로필 목록을 렌더링하는 컨테이너 | `openCreateProfileModal()` (새 프로필 추가 버튼) |
| `windows-task-status-badge` | Windows Task Scheduler 등록 상태 표시 | `registerWindowsTaskFromUI()`, `unregisterWindowsTaskFromUI()` |
| `sysimg-c-used`, `sysimg-c-total` | C: 드라이브 사용/전체 용량 표시 | `loadSystemImageStatus()` |
| `sysimg-d-free`, `sysimg-space-badge` | 백업 대상 드라이브(D:) 여유 공간 표시 | `loadSystemImageStatus()` |
| `sysimg-last-status`, `sysimg-last-time` | 최근 시스템 이미지 백업 상태/시간 표시 | `loadSystemImageStatus()` |
| `sysimg-drive-select` | 백업 저장 드라이브 선택 (D:, E:, F:) | - |
| `btn-start-sysimg` | 시스템 이미지 백업 시작 버튼 | `startSystemImageBackup()` |
| `btn-stop-sysimg` | 시스템 이미지 백업 중단 버튼 (기본 hidden) | `stopSystemImageBackup()` |
| `sysimg-console` | 실시간 백업 로그 출력 영역 | - |

**핵심 관찰:**
- 이 블록에는 **비밀번호 입력 필드(`input type="password"`)** 가 **전혀 없습니다**.
- 따라서 `change-current`, `change-new`, `change-new-confirm` 같은 ID는 이 블록에 존재하지 않습니다.

---

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

- **이벤트 핸들러:**
  - `openCreateProfileModal()`: 백업 프로필 생성 모달을 여는 함수.
  - `registerWindowsTaskFromUI()`: Windows Task Scheduler에 백업 작업을 등록하는 API 호출을 트리거할 것으로 추정.
  - `unregisterWindowsTaskFromUI()`: 등록 해제.
  - `loadSystemImageStatus()`: 시스템 이미지 상태(C: 용량, D: 여유 공간, 최근 백업 정보)를 API에서 가져와 DOM에 바인딩.
  - `startSystemImageBackup()`: `wbadmin` 기반 시스템 이미지 백업 시작.
  - `stopSystemImageBackup()`: 백업 중단.

- **API 호출 추정:**
  - `loadSystemImageStatus()`는 `/api/system-image/status` 또는 유사한 엔드포인트를 호출할 것으로 보입니다.
  - `startSystemImageBackup()`은 `/api/system-image/start` 또는 유사한 엔드포인트를 호출할 것으로 보입니다.

- **데이터 바인딩:**
  - `sysimg-c-used`, `sysimg-c-total`, `sysimg-d-free`, `sysimg-space-badge`, `sysimg-last-status`, `sysimg-last-time` 등은 `loadSystemImageStatus()` 함수에서 `fetch` 또는 `axios`로 데이터를 받아 `innerText` 또는 `innerHTML`로 업데이트될 것입니다.

---

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

#### A. 하드코딩된 드라이브 선택 옵션
```html
<select id="sysimg-drive-select" ...>
    <option value="D:" selected>D: 드라이브 (권장)</option>
    <option value="E:">E: 드라이브</option>
    <option value="F:">F: 드라이브</option>
</select>
```
- **문제:** 사용자가 D:, E:, F: 드라이브만 선택할 수 있습니다. 다른 드라이브(예: G:, H:)가 존재해도 선택할 수 없습니다.
- **영향:** 시스템 이미지 백업 대상 드라이브가 제한적입니다.

### [분석 청크 12: index.html (Part 5/7)]
제공된 `index.html`의 [5/7] 블록은 **스냅샷 파일 탐색기(Explorer), 복원(Restore), 프로필(Profile)** 관련 UI를 포함하고 있습니다.

**중요한 발견:**
사용자가 제보한 **'비밀번호 변경' 모달은 이 블록(5/7)에 포함되어 있지 않습니다.**
이 블록은 백업/복원 기능의 UI이며, 인증(Auth) 관련 모달은 다른 블록(보통 1/7~3/7 또는 6/7~7/7)에 위치할 가능성이 높습니다.

그러나, 요청하신 분석 목적에 따라 **전체 시스템의 비밀번호 변경 로직이 작동하지 않는 원인을 추론하기 위해**, 이 블록에서 발견된 **공통 패턴(모달 구조, 이벤트 핸들러, ID 네이밍 규칙)**을 바탕으로 `backup_auth.js` 및 `web/app.py`와의 **잠재적 불일치 가능성**을 정밀하게 분석합니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할 (Block 5/7)

이 블록은 `index.html`의 하단부에 위치하며, 다음과 같은 3개의 주요 모달을 정의합니다.

| 모달 ID | 역할 | 핵심 UI 요소 (ID) |
| :--- | :--- | :--- |
| `explorer-modal` | 스냅샷 내 파일 탐색 | `explorer-breadcrumb`, `explorer-search-input`, `explorer-tree-container` |
| `restore-modal` | 스냅샷 복원 설정 | `restore-snapshot-id`, `restore-selected-paths`, `restore-mode-inplace`, `restore-mode-safe`, `restore-target-dir`, `btn-start-restore` |
| `profile-modal` | 백업 프로필 생성/수정 | `prof-id`, `prof-name`, `prof-sources`, `prof-repo` |

**핵심 관찰:**
- 모든 모달은 `hidden` 클래스로 초기화되어 있으며, `closeModal('modal-id')` 함수를 통해 닫히도록 설계되어 있습니다.
- `restore-modal`은 `onchange="toggleRestoreMode()"`와 `onclick="startRestore()"`와 같은 인라인 이벤트 핸들러를 사용합니다.
- **비밀번호 변경 모달(`auth-change-modal` 등)은 이 블록에 없습니다.**

---

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

이 블록에서 확인된 이벤트 핸들러 패턴은 `backup_auth.js`의 비밀번호 변경 로직과 동일한 구조를 따를 가능성이 높습니다.

- **인라인 이벤트:** `onclick`, `onchange`, `oninput`
- **함수 호출 예시:**
  - `closeModal('restore-modal')`
  - `toggleRestoreMode()`
  - `startRestore()`
  - `openDirectoryPicker('restore-target-dir')`

**비밀번호 변경 관련 추론:**
`backup_auth.js`의 `submitAuthChangePassword(event)` 함수가 존재한다면, `index.html`의 다른 블록(예: 1/7 또는 2/7)에 다음과 같은 구조의 모달이 있을 것입니다:

```html
<!-- 예상되는 비밀번호 변경 모달 구조 (Block 5/7에 없음) -->
<div id="auth-change-modal" class="... hidden">
    <form onsubmit="submitAuthChangePassword(event)">
        <input type="password" id="change-current" name="old_password">
        <input type="password" id="change-new" name="new_password">
        <input type="password" id="change-new-confirm" name="new_password_confirm">
        <button type="submit">변경</button>
    </form>
</div>
```

**데이터 바인딩 상태:**
- `restore-modal`의 `restore-snapshot-id`와 `restore-selected-paths`는 hidden input으로, JS에서 동적으로 값을 설정하여 API에 전송하는 패턴을 사용합니다.
- 비밀번호 변경도 동일한 패턴(`hidden` 필드 또는 직접 input 값 읽기)을 사용할 것으로 추정됩니다.

---

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

**Block 5/7 자체의 문제:**
- **버그 없음:** 이 블록은 UI 정의만 포함하며, 로직 오류는 없습니다.
- **주의점:** `restore-modal`의 `restore-mode-inplace`와 `restore-mode-safe` 라디오 버튼은 `onchange="toggleRestoreMode()"`를 호출합니다. 만약 `toggleRestoreMode()` 함수가 `backup_auth.js`나 다른 JS 파일에 정의되지 않으면, 복원 모드 전환 시 UI가 반응하지 않을 수 있습니다. (하지만 이는 비밀번호 변경과

### [분석 청크 13: index.html (Part 6/7)]
제공된 `index.html`의 [6/7] 블록은 대시보드의 **프로필 설정(백업 경로, 스케줄링)**과 **인증(Auth) 모달(설정, 로그인, 변경)**의 HTML 구조를 포함하고 있습니다.

사용자가 제보한 "비밀번호 변경이 작동 안한다"는 문제를 해결하기 위해, 이 블록 내의 **비밀번호 변경 모달(`modal-auth-change`)** 구조를 집중적으로 분석하고, 이를 `backup_auth.js` 및 백엔드(`app.py`, `core/auth.py`)와 연결하여 원인을 추적했습니다.

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록에서 확인된 핵심 UI 요소는 다음과 같습니다:

*   **프로필 설정 모달 (`profile-modal`)**:
    *   `prof-sources`, `prof-repo`, `prof-excludes`: 백업 대상 및 저장소 경로 입력.
    *   `prof-schedule-type`, `prof-interval`, `prof-daily-time`: 스케줄링 방식(간격/매일) 및 시간 설정.
    *   `prof-retention`, `prof-compression`: 스냅샷 보관 수 및 압축 레벨.
    *   `prof-auto-enable`: 자동 백업 활성화 체크박스.
    *   **핵심 역할**: 백업 엔진의 동작 파라미터를 설정하는 UI.
*   **디렉토리 브라우저 (`browse-modal`)**:
    *   `browse-current-path`, `browse-items-list`: 서버 측 디렉토리 탐색을 위한 UI.
    *   **핵심 역할**: `openDirectoryPicker` 함수와 연동하여 서버 파일시스템을 탐색.
*   **인증 모달 그룹 (`auth-modal-overlay`)**:
    *   **`modal-auth-setup`**: 최초 마스터 비밀번호 설정.
        *   `setup-password`, `setup-password-confirm`: 입력 필드.
        *   `form-auth-setup`: `onsubmit="submitAuthSetup(event)"`.
    *   **`modal-auth-login`**: 로그인.
        *   `login-password`: 입력 필드.
        *   `form-auth-login`: `onsubmit="submitAuthLogin(event)"`.
    *   **`modal-auth-change`**: **비밀번호 변경 (문제 발생 지점)**.
        *   `change-current`: 현재 비밀번호 입력 필드.
        *   `change-new`: 새 비밀번호 입력 필드 (블록 하단에서 잘림).
        *   `change-new-confirm`: 새 비밀번호 확인 입력 필드 (블록 하단에서 잘림).
        *   `form-auth-change`: `onsubmit="submitAuthChangePassword(event)"`.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **이벤트 핸들러**:
    *   `submitAuthChangePassword(event)`: `form-auth-change`의 submit 이벤트 트리거.
    *   `closeAuthModal()`: 모달 닫기 버튼 클릭 시 호출.
    *   `onScheduleTypeChange()`: 스케줄링 방식 변경 시 UI 토글 처리.
*   **데이터 바인딩**:
    *   HTML의 `id` 속성(`change-current`, `change-new`, `change-new-confirm`)은 `backup_auth.js`의 `submitAuthChangePassword` 함수에서 `document.getElementById()`를 통해 값을 가져오기 위해 사용됩니다.
    *   **주의**: 제공된 블록은 `change-new`와 `change-new-confirm`의 `<input>` 태그가 **잘려서(cut off)** 보이지 않습니다. 이는 다음 블록(7/7)에서 이어질 가능성이 높으나, 만약 이 블록이 끝이라면 **HTML 구조가 깨져 있을 수 있습니다.**

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

**[중요 발견 1: HTML 구조 불완전 가능성]**
*   제공된 코드 블록은 `modal-auth-change`의 `form-auth-change` 내부에서 `change-current` label/input 이후로 **절반만** 표시됩니다.
*   `change-new`와 `change-new-confirm` input 필드가 이 블록에 없다면, `backup_auth.js`가 `document.getElementById('change-new')`을 호출할 때 `null`을 반환하여 **JavaScript 오류(ReferenceError 또는 TypeError)**가 발생하고, `submitAuthChangePassword` 함수가 중단될 수 있습니다.
*   **확인 필요**: `index.html`의 7/7 블록에서 `change-new`와 `change-new-confirm` input이 존재하는지 확인해야 합니다.

**[중요 발견 2: 폼 제출 방지 누락 가능성]**
*   `submitAuthChangePassword(event)` 함수 내부에서 `event.preventDefault()`가 호출되지 않으면, 브라우저의 기본

### [분석 청크 14: index.html (Part 7/7)]
# index.html (Part 7/7) 정밀 분석 보고서

## 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록은 **비밀번호 변경 모달의 하단부**와 **스크립트 로드 섹션**을 포함합니다.

*   **UI 요소**:
    *   **Form ID**: `form-auth-change`
    *   **Input Fields**:
        *   `change-current`: 현재 비밀번호 입력 (type=password, required)
        *   `change-new`: 새 비밀번호 입력 (type=password, required, minlength=4)
        *   `change-new-confirm`: 새 비밀번호 확인 입력 (type=password, required, minlength=4)
    *   **Error Container**: `change-error` (기본 상태: `hidden`)
    *   **Buttons**:
        *   취소 버튼: `onclick="closeAuthModal()"`
        *   제출 버튼: `type="submit"` (폼 제출 트리거)
*   **스크립트 로드**:
    *   `backup_auth.js`: 인증 관련 로직 (비밀번호 변경 포함)
    *   `app.js`: 메인 애플리케이션 로직
    *   기타 백업 관련 스크립트들

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **이벤트 핸들러**:
    *   `onsubmit="submitAuthChangePassword(event)"`: 폼 제출 시 `backup_auth.js`의 `submitAuthChangePassword` 함수 호출.
    *   `onclick="closeAuthModal()"`: 모달 닫기.
*   **데이터 바인딩**:
    *   HTML의 `id` 속성 (`change-current`, `change-new`, `change-new-confirm`)은 `backup_auth.js`에서 `document.getElementById()` 또는 `querySelector`를 통해 접근될 것으로 추정됩니다.
    *   **주의**: 이 HTML 블록만으로는 `backup_auth.js`의 실제 구현을 확인할 수 없으므로, ID 일치 여부는 다음 단계에서 검증해야 합니다.

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

*   **HTML 자체의 문제**:
    *   HTML 구조는 표준적이고 명확합니다. `required`와 `minlength` 속성이 올바르게 설정되어 있어 클라이언트 측 기본 검증은 가능합니다.
    *   `change-error` 컨테이너가 `hidden` 클래스를 가지고 있어 초기 상태는 정상입니다.
*   **잠재적 문제 (HTML 관점)**:
    *   `autocomplete` 속성이 올바르게 설정되어 있어 브라우저의 자동완성 간섭을 최소화했습니다.
    *   **결론**: HTML 블록 자체에는 명백한 버그가 없습니다. 문제는 **JS와 Backend의 연동**에 있을 가능성이 높습니다.

## 4. 사용자의 질문과 관련된 핵심 발견점

사용자가 "비밀번호 변경이 작동 안한다"고 제보한 상황에서, 이 HTML 블록은 **클라이언트 측 입력 수집과 폼 제출 트리거**만 담당합니다. 따라서 문제는 다음과 같은 경로에서 발생했을 가능성이 높습니다:

1.  **`backup_auth.js`의 `submitAuthChangePassword` 함수**:
    *   HTML의 `id` (`change-current`, `change-new`, `change-new-confirm`)를 정확히 가져오는지?
    *   가져온 값을 JSON 객체로 변환할 때 **키 이름**이 무엇인지? (예: `old_password`, `new_password` vs `current_password`, `new_password`)
    *   API 엔드포인트 URL이 올바른지?
    *   에러 핸들링이 `change-error` 요소에 메시지를 표시하는지?

2.  **`web/app.py`의 API 엔드포인트**:
    *   `POST /api/auth/change-password` (또는 유사한 경로)의 Pydantic 모델 필드명이 `backup_auth.js`가 보내는 JSON 키와 일치하는지?
    *   예: JS가 `{ "old_password": "...", "new_password": "..." }`를 보내는데, Pydantic 모델이 `current_password`를 기대하면 422 오류가 발생합니다.

3.  **`core/auth.py`의 `change_master_password`**:
    *   현재 비밀번호 검증 로직이 올바른지?
    *   파일 권한 또는 세션 문제?

## 5. 정확한 원인과 구체적인 해결 패치 방안

**현재 HTML 블록만으로는 원인을 특정할 수 없으므로, `backup_auth.js`와 `web/app.py`의 코드가 필요합니다.**

그러나 일반적인 패턴을 바탕으로 **가장 가능성 높은 원인**과 **검증 절차**를 제시합니다:

### 🔍 검증 절차 (즉시 실행)