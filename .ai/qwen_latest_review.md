## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]: 시스템 중단, 보안 결함, 규정 위반 위험**
*   **보안 취약점 (Critical)**: `auth-pw-btn` 클릭 시 모달이 열리지 않는 현상은 단순 UI 버그가 아니라, **인증 우회(Auth Bypass) 또는 인증 상태 동기화 실패**의 신호일 수 있습니다. 만약 `handleAuthPasswordClick()`이 실패하여 모달이 안 뜨는 대신, 백그라운드에서 인증 상태가 "설정됨"으로 오인되거나, 반대로 "미설정" 상태가 유지되면서도 보호 기능이 비활성화되는 경우, 데이터 무결성과 기밀성이 심각하게 훼손됩니다.
*   **기능 마비**: 마스터 비밀번호 설정은 시스템의 첫 번째 보안 게이트입니다. 이 기능이 작동하지 않으면 신규 사용자 온보딩이 불가능하며, 기존 사용자의 비밀번호 변경/재설정 경로가 차단되어 계정 잠금(Account Lockout) 리스크가 발생합니다.

**[BUG]: 발견된 구체적 결함**
1.  **이중 `hidden` 클래스 충돌 (Double Hidden State)**:
    *   `#auth-modal-overlay` (Part 6/7)와 그 내부의 `#modal-auth-setup` (Part 6/7) 모두 초기 상태에 `hidden` 클래스를 가지고 있습니다.
    *   **결함**: `handleAuthPasswordClick()` 함수가 오버레이(`#auth-modal-overlay`)의 `hidden`만 제거하고, 내부 모달(`#modal-auth-setup`)의 `hidden`은 제거하지 않는 경우, **오버레이(반투명 배경)만 뜨고 실제 입력 폼은 보이지 않는 "빈 모달" 상태**가 됩니다. 사용자가 클릭해도 반응이 없어 "모달이 안 뜬다"고 인식하게 됩니다.
2.  **이벤트 버블링과 전역 클릭 리스너의 경쟁 상태 (Race Condition)**:
    *   `#auth-pw-btn` 클릭 시 `handleAuthPasswordClick()`이 실행되어 모달을 열지만, 이 `click` 이벤트가 `document` 레벨로 버블링됩니다.
    *   `document`에 등록된 외부 클릭 감지 리스너(`document.addEventListener('click', ...)`)가 `e.target.closest('#auth-badge-wrapper')`를 검사하여 드롭다운을 닫는 로직을 수행합니다.
    *   **결함**: 만약 전역 리스너가 드롭다운을 닫는 과정에서 DOM 조작(클래스 변경)을 수행하거나, `stopPropagation()`이 누락되어 이벤트가 계속 전파되면, 모달 오픈 로직과 드롭다운 클로징 로직이 동시에 실행되어 DOM 상태가 불안정해지고 모달이 즉시 닫히거나 렌더링이 깨질 수 있습니다.
3.  **스크립트 로드 순서 및 함수 정의 시점 문제**:
    *   `index.html` Part 7/7에서 스크립트 로드 순서가 `backup_auth.js` → `app.js` 순임을 확인했습니다.
    *   `auth-pw-btn`의 `onclick` 핸들러가 `app.js`에 정의된 함수를 호출하는데, `app.js`가 `DOMContentLoaded` 이후에 초기화되거나, 함수가 `window` 객체에 제대로 노출되지 않으면 `ReferenceError`가 발생하여 모달이 열리지 않습니다.

**[RISK]: 성능 병목, 사이드 이펙트, 환경 의존성**
*   **DOM 조작 과다**: 드롭다운 토글, 모달 오픈/클로즈, 전역 클릭 감지 로직이 모두 `classList` 조작과 `document` 이벤트 리스너에 의존합니다. 이 로직이 `app.js`와 `backup_auth.js`에 분산되어 있으면, 상태 관리(State Management)가 비동기적으로 깨질 수 있습니다.
*   **브라우저 호환성**: `e.target.closest()`는 최신 브라우저에서 지원되지만, 구형 브라우저나 특정 웹뷰 환경에서는 `null`을 반환하거나 에러를 일으켜 드롭다운/모달 로직이 전체적으로 멈출 수 있습니다.
*   **하드코딩된 UI 상태**: Part 1/7에서 `#auth-dropdown`의 초기 `hidden` 상태와 Part 6/7의 모달 `hidden` 상태가 하드코딩되어 있습니다. JS 초기화 로직이 이 상태를 올바르게 오버라이드하지 않으면, 초기 렌더링 시 UI가 깨집니다.

**[ACTION]: 구체적인 해결 제안 및 수정 가이드**
1.  **모달 오픈 로직 수정 (Double Hidden Fix)**:
    *   `handleAuthPasswordClick()` 함수 내에서 `#auth-modal-overlay`와 `#modal-auth-setup` **둘 다**의 `hidden` 클래스를 제거하도록 수정해야 합니다.
    *   ```javascript
        function handleAuthPasswordClick() {
            const overlay = document.getElementById('auth-modal-overlay');
            const modal = document.getElementById('modal-auth-setup');
            if (overlay && modal) {
                overlay.classList.remove('hidden');
                modal.classList.remove('hidden'); // 핵심: 내부 모달도 표시
            }
        }
        ```
2.  **이벤트 버블링 차단 및 전역 리스너 최적화**:
    *   `#auth-pw-btn`의 클릭 핸들러에서 `event.stopPropagation()`을 호출하여 이벤트가 `document` 레벨로 전파되는 것을 방지해야 합니다.
    *   ```javascript
        function handleAuthPasswordClick(e) {
            e.stopPropagation(); // 전역 클릭 리스너와의 충돌 방지
            // ... 모달 오픈 로직
        }
        ```
    *   전역 `document` 클릭 리스너에서 드롭다운/모달 상태를 확인하기 전에, `e.target`이 모달 내부인지 확인하는 로직을 추가해야 합니다.
3.  **스크립트 로드 및 함수 정의 검증**:
    *   `app.js` 또는 `backup_auth.js`에서 `handleAuthPasswordClick` 함수가 `window` 객체에 올바르게 노출되는지 확인하세요.
    *   `DOMContentLoaded` 이벤트 리스너에서 드롭다운/모달의 초기 상태(`hidden` 클래스)를 명시적으로 설정하는 로직을 추가하여 HTML 하드코딩에 대한 의존성을 줄이세요.
4.  **드롭다운과 모달의 상태 분리**:
    *   드롭다운(`#auth-dropdown`)은 `#auth-badge-wrapper` 내부의 로컬 상태이며, 모달(`#auth-modal-overlay`)은 전역 상태입니다. 이 둘을 독립적으로 관리하도록 로직을 분리해야 합니다. 드롭다운을 닫는 로직이 모달의 상태를 영향을 주지 않도록 해야 합니다.

**[DECISION REQUIRED]: Antigravity 및 사용자가 최종 승인해야 할 핵심 의사결정**
1.  **모달 구조 재설계 승인**: `#auth-modal-overlay`와 `#modal-auth-setup`의 이중 `hidden` 구조를 유지할지, 아니면 오버레이만 `hidden`을 제어하고 내부 모달은 항상 표시되도록 CSS를 수정할지 결정해야 합니다. (권장: 오버레이만 제어)
2.  **이벤트 처리 전략**: `stopPropagation()`을 사용하여 전역 클릭 리스너와의 충돌을 방지하는 방식을 승인할지, 아니면 전역 리스너에서 모달/드롭다운 상태를 더 정교하게 검사하는 방식을 선택할지 결정해야 합니다.
3.  **스크립트 로드 순서 변경**: `backup_auth.js`가 `app.js`보다 먼저 로드되므로, `handleAuthPasswordClick` 함수가 `backup_auth.js`에 정의되어야 하는지, 아니면 `app.js`에 정의되어야 하는지 아키텍처를 확정해야 합니다. (권장: 인증 관련 로직은 `backup_auth.js`에 집중)

## PART 2. [COMPREHENSIVE AUDIT & ARCHITECTURE REPORT]

### 1. 전체 파일 구조 및 관련 요소 매핑

*   **`index.html` (Part 1/7)**:
    *   `#auth-badge-wrapper`: 드롭다운의 위치 기준점 (`position: relative`).
    *   `#auth-badge-btn`: 드롭다운 토글 버튼 (`onclick="toggleAuthDropdown()"`).
    *   `#auth-dropdown`: 드롭다운 메뉴 (`hidden` 클래스 기본값).
    *   `#auth-pw-btn`: 마스터 비밀번호 설정 버튼 (`onclick="handleAuthPasswordClick()"`).
*   **`index.html` (Part 6/7)**:
    *   `#auth-modal-overlay`: 인증 모달 공통 오버레이 (`hidden` 클래스 기본값).
    *   `#modal-auth-setup`: 마스터 비밀번호 설정 모달 (`hidden` 클래스 기본값).
    *   `#modal-auth-login`: 로그인 모달.
    *   `#modal-auth-change`: 비밀번호 변경 모달.
*   **`index.html` (Part 7/7)**:
    *   스크립트 로드 순서: `backup_utils.js` → `backup_auth.js` → ... → `app.js`.
    *   `closeAuthModal()` 함수 호출 확인.

### 2. 청크별 세부 분석 종합

#### [청크 1: index.html Part 1/7] - 드롭다운 트리거 구조
*   **핵심 발견**: `#auth-pw-btn`은 `#auth-dropdown` 내부에 위치하며, `#auth-dropdown`는 `hidden` 클래스를 가지고 있습니다.
*   **충돌 가능성**: `#auth-pw-btn` 클릭 시 `handleAuthPasswordClick()`이 실행되고, 이 이벤트가 `document` 레벨로 버블링됩니다. 전역 클릭 리스너가 `#auth-badge-wrapper` 외부 클릭을 감지하여 드롭다운을 닫는 로직을 수행할 때, 모달 오픈 로직과 충돌할 수 있습니다.

#### [청크 2~4: index.html Part 2/7 ~ 4/7] - 비인증 영역
*   **핵심 발견**: 이 블록들은 대시보드, 커스텀 백업, 시스템 이미지 백업 UI를 포함하며, 인증 관련 요소가 없습니다.
*   **관련성**: 인증 모달 문제와 직접적인 관련은 없으나, 전체 SPA 구조에서 모달 관리 패턴(`closeModal`, `openModal`)의 일관성을 확인하는 데 참고할 수 있습니다.

#### [청크 5: index.html Part 5/7] - 기존 모달 구조
*   **핵심 발견**: `explorer-modal`, `restore-modal`, `profile-modal`은 모두 `fixed inset-0 ... hidden` 클래스를 사용합니다.
*   **관련성**: `closeModal('modal-id')` 함수가 존재하며, 이는 `hidden` 클래스를 추가하는 방식으로 구현될 가능성이 높습니다. `auth` 모달도 동일한 패턴을 따를 것으로 추정됩니다.

#### [청크 6: index.html Part 6/7] - 인증 모달 마크업 (핵심)
*   **핵심 발견**: `#auth-modal-overlay`와 `#modal-auth-setup` 모두 `hidden` 클래스를 가지고 있습니다.
*   **버그 원인**: `handleAuthPasswordClick()`이 오버레이만 `hidden`을 제거하고 내부 모달은 제거하지 않으면, 오버레이만 표시되고 실제 모달은 보이지 않게 됩니다.
*   **이벤트 핸들러**: `submitAuthSetup(event)`, `submitAuthLogin(event)`, `submitAuthChangePassword(event)` 등 폼 제출 핸들러가 정의되어 있습니다.

#### [청크 7: index.html Part 7/7] - 스크립트 로드 및 함수 호출
*   **핵심 발견**: `closeAuthModal()` 함수가 호출되며, 스크립트 로드 순서가 `backup_auth.js` → `app.js`입니다.
*   **버그 원인**: `handleAuthPasswordClick()` 함수가 `app.js`에 정의되어 있고, `app.js`가 로드되기 전에 버튼이 클릭되면 `ReferenceError`가 발생할 수 있습니다. 또는 `app.js`에서 `DOMContentLoaded` 이후에 함수를 정의하는 경우, 초기 클릭 시 에러가 발생할 수 있습니다.

### 3. 최종 결론 및 수정 가이드

**마스터 비밀번호 미설정 상태에서 모달이 안 뜨는 원인**:
1.  **이중 `hidden` 클래스**: `#auth-modal-overlay`와 `#modal-auth-setup` 모두 `hidden` 상태이며, JS가 오버레이만 해제하고 내부 모달은 해제하지 않아 "빈 모달" 상태가 됩니다.
2.  **이벤트 버블링 충돌**: `#auth-pw-btn` 클릭 이벤트가 `document` 레벨로 전파되어 전역 클릭 리스너와 충돌, 드롭다운/모달 상태가 불안정해집니다.
3.  **스크립트 로드 순서**: `handleAuthPasswordClick()` 함수가 정의되지 않은 상태에서 버튼이 클릭되면 에러가 발생하여 모달이 열리지 않습니다.

**수정 가이드**:
1.  `handleAuthPasswordClick()` 함수에서 `#auth-modal-overlay`와 `#modal-auth-setup`의 `hidden` 클래스를 모두 제거하도록 수정.
2.  `handleAuthPasswordClick()` 함수에서 `event.stopPropagation()`을 호출하여 전역 클릭 리스너와의 충돌을 방지.
3.  `handleAuthPasswordClick()` 함수가 `backup_auth.js`에 정의되도록 이동하거나, `app.js`에서 `DOMContentLoaded` 이전에 함수를 정의하도록 확인.
4.  전역 `document` 클릭 리스너에서 `#auth-modal-overlay` 내부 클릭을 감지하여 모달을 닫지 않도록 로직을 수정.