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