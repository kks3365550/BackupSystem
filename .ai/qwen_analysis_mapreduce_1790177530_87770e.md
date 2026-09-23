# Qwen 대용량 자동 분할 분석 전체 산출물

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

---
## 청크별 1차 분석 원본

### [분석 청크 1: index.html (Part 1/7)]
제공된 `index.html`의 [1/7] 블록(헤더 및 사이드바, 대시보드 일부)을 정밀 분석한 결과, **`auth-pw-btn` 버튼 클릭 시 모달이 뜨지 않는 현상**의 원인은 **이벤트 버블링(Event Bubbling)과 전역 클릭 리스너의 충돌**에 있으며, 이는 HTML 마크업 구조와 JavaScript 로직(후속 블록에 존재할 것으로 추정) 간의 상호작용으로 인해 발생합니다.

아래는 요청하신 4가지 항목에 대한 구조화 요약입니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

*   **`#auth-badge-wrapper` (Relative Container)**:
    *   드롭다운(`#auth-dropdown`)의 위치를 결정하는 기준점입니다. `position: relative`가 적용되어 내부의 `absolute` 요소가 이 컨테이너를 기준으로 배치됩니다.
*   **`#auth-badge-btn` (Trigger Button)**:
    *   `onclick="toggleAuthDropdown()"`: 드롭다운의 `hidden` 클래스를 토글하여 열림/닫힘을 제어합니다.
*   **`#auth-dropdown` (Dropdown Menu)**:
    *   초기 상태: `hidden` 클래스 보유 (표시 안 됨).
    *   내부에 `#auth-pw-btn`, `#auth-bypass-toggle-btn`, 로그아웃 버튼 포함.
*   **`#auth-pw-btn` (Target Button)**:
    *   `onclick="handleAuthPasswordClick()"`: 마스터 비밀번호 설정/변경 모달(`#modal-auth-setup`)을 호출하는 핵심 버튼.
    *   상태: `hidden` 상태의 드롭다운 내부에 위치하므로, 드롭다운이 열려야만 클릭 가능합니다.
*   **`#modal-auth-setup` (Modal)**:
    *   *참고: 현재 1/7 블록에는 모달의 HTML 마크업이 보이지 않습니다.* 이는 후속 블록(2/7~7/7)에 정의될 것으로 추정됩니다. 하지만 `handleAuthPasswordClick()` 함수가 이 모달을 조작한다는 전제 하에 분석합니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **`toggleAuthDropdown()`**:
    *   `#auth-dropdown`의 `classList.toggle('hidden')`을 수행할 것으로 추정됩니다.
*   **`handleAuthPasswordClick()`**:
    *   `#modal-auth-setup`의 `hidden` 클래스를 제거하거나 `display`를 변경하여 모달을 표시하는 로직을 포함할 것입니다.
    *   **중요**: 이 함수가 실행되기 위해서는 `#auth-pw-btn`의 `click` 이벤트가 정상적으로 처리되어야 합니다.
*   **전역 `document` Click Listener (외부 클릭 감지)**:
    *   일반적으로 드롭다운/모달 패턴에서는 `document.addEventListener('click', ...)`를 사용하여 **드롭다운 외부**를 클릭하면 드롭다운을 닫는 로직을 구현합니다.
    *   *가정*: 후속 JS 블록에서 `document.addEventListener('click', (e) => { if (!e.target.closest('#auth-badge-wrapper')) { closeDropdown(); } })`와 유사한 로직이 존재할 것입니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

#### 🔴 핵심 버그: 이벤트 버블링과 전역 클릭 리스너의 충돌 (Race Condition)

**현상**: `#auth-pw-btn`을 클릭했을 때 모달이 뜨지 않음.

**원인 분석**:
1.  **클릭 순서**:
    *   사용자가 `#auth-pw-btn`을 클릭합니다.
    *   `handleAuthPasswordClick()`이 실행되어 모달(`#modal-auth-setup`)이 **열립니다** (DOM 조작).
    *   이 `click` 이벤트는 버블링(Bubbling)을 통해 `document` 레벨까지 전파됩니다.
2.  **전역 리스너의 오작동**:
    *   `document`에 걸린 클릭 리스너가 트리거됩니다.
    *   리스너 내부에서 `e.target.closest('#auth-badge-wrapper')` 또는 `e.target.closest('#auth-dropdown')`를 확인합니다.
    *   **문제점**: 만약 전역 리스너가 **"드롭다운 외부 클릭"**을 감지하는 로직이라면, `#auth-pw-btn`은 `#auth-badge-wrapper` *내부*에 있으므로 드롭다운을 닫지 않아야 합니다.
    *   **그러나**, 만약 전역 리스

### [분석 청크 2: index.html (Part 2/7)]
제공된 코드 블록(`index.html` Part 2/7)은 **대시보드(Dashboard)** 및 **커스텀 백업 항목 선택(Custom Item Selector)** 탭의 UI 마크업으로 구성되어 있습니다.

사용자가 질문하신 `auth-pw-btn`, `auth-dropdown`, `auth-modal-overlay`, `modal-auth-setup` 및 관련 이벤트 핸들러는 **이 블록(2/7)에 포함되어 있지 않습니다.**

따라서, 이 블록 내에서 발견할 수 있는 것은 다음과 같습니다:

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할
*   **대시보드 통계 카드**: `stat-logical-bytes`, `stat-dedup-saved` 등 용량 관련 통계 표시 영역.
*   **최근 스냅샷 목록**: `recent-snapshots-list` (JS에 의해 동적 주입 예정).
*   **시스템 드라이브 현황**: `system-drives-list` (JS에 의해 동적 주입 예정).
*   **백업 프로필 관리**: `stat-active-profiles` 및 프로필 관리 탭 전환 버튼.
*   **OS 베어메탈 백업 배너**: `switchTab('system-image')` 호출 버튼.
*   **커스텀 백업 선택기 (Tab: Custom)**:
    *   **드라이버 선택**: `custom-include-drivers` 체크박스.
    *   **응용 프로그램 선택**: `app-search-input` (검색), `installed-apps-container` (목록), `toggleAllApps()` 버튼.
    *   **개인 프로젝트 선택**: `ai-projects-container` (목록), `toggleAllProjects()` 버튼.
    *   **추가 폴더 선택**: (코드 절단으로 일부만 보임).

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태
*   **onclick 이벤트**:
    *   `switchTab('snapshots')`: 스냅샷 탭으로 전환.
    *   `switchTab('profiles')`: 프로필 관리 탭으로 전환.
    *   `switchTab('system-image')`: OS 이미지 관리 탭으로 전환.
    *   `loadCustomSelectionData()`: 커스텀 선택 데이터 로드.
    *   `toggleAllApps(true/false)`: 앱 전체 선택/해제.
    *   `toggleAllProjects(true/false)`: 프로젝트 전체 선택/해제.
    *   `filterAppsList()`: 앱 목록 필터링 (oninput).
*   **데이터 바인딩**:
    *   `id="stat-logical-bytes"`, `id="stat-dedup-saved"`, `id="stat-active-profiles"` 등은 JS에서 값을 채워 넣기 위한 placeholder입니다.
    *   `id="recent-snapshots-list"`, `id="system-drives-list"`, `id="installed-apps-container"`, `id="ai-projects-container"`는 JS에 의해 동적으로 생성될 리스트 컨테이너입니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소
*   **하드코딩된 텍스트**: "43개 드라이버 자동 감지"와 같은 텍스트가 하드코딩되어 있어 실제 감지된 드라이버 수와 다를 수 있습니다.
*   **초기 상태 텍스트**: "설치된 프로그램 목록을 검색 중입니다...", "프로젝트 목록 로드 중..." 등은 JS가 로드되기 전까지 표시되는 초기 상태입니다.
*   **이 블록 내 인증 관련 요소 부재**: 질문하신 인증 관련 요소는 이 블록에 없습니다.

### 4. 사용자의 질문과 관련된 핵심 발견점
**결론: 이 코드 블록(2/7)에는 `auth-pw-btn`, `auth-dropdown`, `auth-modal-overlay`, `modal-auth-setup` 및 관련 이벤트 핸들러가 포함되어 있지 않습니다.**

따라서, **마스터 비밀번호 미설정 상태에서 버튼을 클릭했을 때 모달이 안 뜨는 원인**을 찾기 위해서는 **다른 코드 블록(1/7, 3/7, 4/7, 5/7, 6/7, 7/7)**을 확인해야 합니다. 특히 다음을 포함하는 블록을 찾아야 합니다:
1.  `id="auth-pw-btn"` 또는 `id="auth-dropdown"`가 정의된 HTML 마크업.
2.  `id="auth-modal-overlay"` 또는 `id="modal-auth-setup"`가 정의된 HTML 마크업.
3.  `document.addEventListener('click', ...)` 또는 `window.addEventListener('click', ...)`로 외부 클릭을 감지하는 JS 코드.
4.  `auth-pw-btn`의 `onclick` 핸들러 또는

### [분석 청크 3: index.html (Part 3/7)]
제공된 코드 블록(`index.html` Part 3/7)은 **백업 대상 선택(Tab 1의 하단부), 실시간 백업 러너(Tab 2), 스냅샷 타임머신(Tab 3), 백업 프로필(Tab 4의 상단부)**에 해당하는 UI 마크업입니다.

사용자가 질문하신 `auth-pw-btn`, `auth-dropdown`, `auth-modal-overlay`, `modal-auth-setup` 및 관련 이벤트 핸들러는 **이 코드 블록(3/7)에 포함되어 있지 않습니다.**

따라서, 이 블록 내에서 해당 요소들의 충돌 가능성이나 모달이 안 뜨는 원인을 직접적으로 확인하는 것은 불가능합니다. 하지만, 이 블록의 구조와 일반적인 SPA(단일 페이지 애플리케이션) 패턴을 바탕으로 **가능성 있는 원인 분석**과 **확인해야 할 사항**을 구조화하여 요약해 드립니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할 (본 블록 기준)

*   **Tab 1 (Custom Selection) 하단부:**
    *   `#ai-projects-container`: AI 프로젝트 목록 표시 영역.
    *   `#custom-folders-list`: 사용자 정의 추가 폴더 목록.
    *   `openDirectoryPickerForCustom()`: 커스텀 폴더 선택 버튼 클릭 시 호출.
    *   `#custom-repo-dir`, `#custom-profile-name`: 백업 저장소 경로 및 프로필 이름 입력 필드.
    *   `startCustomSelectionBackup()`: "선택한 항목 지금 백업 시작" 버튼 클릭 시 호출되는 핵심 백업 실행 함수.
    *   `#summary-*` 배지들: 선택된 드라이버, 앱, 프로젝트, 커스텀 폴더 수를 요약 표시.
*   **Tab 2 (Live Runner):**
    *   `#runner-status-badge`, `#runner-cancel-btn`: 백업 상태 표시 및 작업 취소 버튼.
    *   `#runner-progress-bar`, `#runner-percent-text`: 진행률 바 및 텍스트.
    *   `#terminal-log-box`: 실시간 로그 출력 영역.
    *   `cancelCurrentTask()`: 작업 취소 버튼 클릭 시 호출.
*   **Tab 3 (Snapshots):**
    *   `#snapshots-table-body`: 스냅샷 목록 테이블 바디 (JS로 동적 삽입).
    *   `loadSnapshots()`: 스냅샷 목록 새로고침 버튼 클릭 시 호출.
*   **Tab 4 (Profiles):**
    *   `openCreateProfileModal()`: 새 프로필 추가 버튼 클릭 시 호출.

> **참고:** 이 블록에는 인증(Auth) 관련 UI가 없습니다. 인증 UI는 보통 헤더(Header)나 초기화면(Onboarding)에 위치하므로, **Part 1/7 또는 Part 2/7**에 있을 가능성이 높습니다.

---

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **인라인 onclick 핸들러:**
    *   `openDirectoryPickerForCustom()`
    *   `openDirectoryPicker('custom-repo-dir')`
    *   `startCustomSelectionBackup()`
    *   `cancelCurrentTask()`
    *   `loadSnapshots()`
    *   `openCreateProfileModal()`
*   **데이터 바인딩:**
    *   `#summary-drivers-badge`, `#summary-apps-count`, `#summary-projects-count`, `#summary-custom-count`: JS에서 선택 상태에 따라 동적으로 업데이트되어야 하는 요소들.
    *   `#runner-progress-bar`의 `style="width: 0%"`: JS에서 백업 진행률에 따라 `style.width`을 수정해야 함.
    *   `#terminal-log-box`: 백업 진행 중 로그를 실시간으로 추가해야 함.

> **중요:** 이 블록 자체에는 `auth` 관련 이벤트 핸들러가 없으므로, 인증 로직과의 직접적인 충돌은 이 블록에서 판단할 수 없습니다.

---

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

**본 블록 내에서 발견된 잠재적 문제:**

1.  **하드코딩된 텍스트:**
    *   `D: 드라이브 (여유: 908 GB 넉넉함)`: 실제 시스템의 D: 드라이브 용량과 무관하게 하드코딩되어 있습니다. 실제 시스템 정보와 다를 수 있어 혼란을 줄 수 있습니다.
    *   `포함 (43개)`: `#summary-drivers-badge`의 초기 텍스트가 하드코딩되어 있습니다. 실제 드라이버 수와 다를 수 있으며, JS가 초기화 전에 이 값을 업데이트하지 않으면

### [분석 청크 4: index.html (Part 4/7)]
제공된 코드 블록(`index.html` Part 4/7)은 **백업 프로필 관리**, **Windows Task Scheduler 등록**, **시스템 이미지(베어메탈) 백업** 탭의 UI 마크업으로 구성되어 있습니다.

사용자가 질문하신 `auth-pw-btn`, `auth-dropdown`, `auth-modal-overlay`, `modal-auth-setup` 및 관련 이벤트 핸들러는 **이 코드 블록(4/7) 내에 존재하지 않습니다.**

따라서 이 블록 내에서 해당 요소들의 충돌 가능성이나 모달이 안 뜨는 원인을 직접적으로 확인하는 것은 불가능합니다. 하지만, 이 블록의 구조와 일반적인 SPA(Single Page Application) 패턴을 바탕으로 **가능성 있는 원인**과 **확인해야 할 사항**을 분석해 드립니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할 (Part 4/7)

이 블록은 인증(Auth)과 무관한 **백업 기능** UI입니다.

*   **백업 프로필 & 자동 스케줄 탭**:
    *   `openCreateProfileModal()`: 새 백업 프로필 생성 모달을 여는 버튼.
    *   `registerWindowsTaskFromUI()` / `unregisterWindowsTaskFromUI()`: Windows OS 작업 스케줄러 등록/해제 버튼.
    *   `#profiles-list-container`: JS에 의해 동적으로 주입되는 프로필 목록 컨테이너.
*   **시스템 이미지 백업 탭 (`#tab-system-image`)**:
    *   `loadSystemImageStatus()`: 시스템 이미지 상태 새로고침.
    *   `startSystemImageBackup()` / `stopSystemImageBackup()`: `wbadmin` 기반 OS 전체 백업 시작/중단.
    *   `#sysimg-console`: 실시간 콘솔 로그 출력 영역.
    *   `#sysimg-drive-select`: 백업 저장 드라이브 선택 드롭다운 (D:, E:, F: 하드코딩).

> **결론**: 이 블록에는 `auth-pw-btn`나 `modal-auth-setup`이 없습니다. 따라서 이 블록 자체에서 모달이 안 뜨는 직접적인 원인은 찾을 수 없습니다.

---

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **인라인 onclick 핸들러**:
    *   `openCreateProfileModal()`, `registerWindowsTaskFromUI()`, `unregisterWindowsTaskFromUI()`, `loadSystemImageStatus()`, `startSystemImageBackup()`, `stopSystemImageBackup()`
    *   이 함수들은 다른 JS 파일(또는 다른 HTML 블록)에서 정의되어야 합니다.
*   **데이터 바인딩**:
    *   `#windows-task-status-badge`, `#windows-task-next-run`, `#sysimg-c-used`, `#sysimg-d-free`, `#sysimg-last-status` 등은 JS에 의해 동적으로 업데이트되는 요소입니다.
    *   `#sysimg-drive-select`는 하드코딩된 옵션(D:, E:, F:)을 가지고 있으며, 실제 시스템 드라이브 목록과 일치하지 않을 수 있습니다.

---

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

이 블록 내에서 발견된 문제점:

1.  **하드코딩된 드라이브 목록**:
    *   `#sysimg-drive-select`에 `D:`, `E:`, `F:`가 하드코딩되어 있습니다.
    *   **문제**: 사용자가 `C:` 드라이브에 백업하려는 경우나, `D:` 드라이브가 없는 시스템에서는 선택지가 잘못 표시됩니다.
    *   **해결**: JS에서 `navigator.storage` 또는 API를 통해 실제 드라이브 목록을 동적으로 생성해야 합니다.

2.  **`#sysimg-console` 초기 상태**:
    *   초기 HTML에 `<div class="text-slate-500">[대기] ...</div>`가 있습니다.
    *   **문제**: `startSystemImageBackup()`이 실행될 때, 이 초기 텍스트를 제거하거나 교체하는 로직이 JS에 없으면 콘솔에 오래된 메시지가 남아 있을 수 있습니다.

3.  **`#btn-stop-sysimg`의 `hidden` 클래스**:
    *   초기 상태에서는 `hidden` 클래스가 적용되어 있습니다.
    *   **문제**: `startSystemImageBackup()`이 실행되면 `hidden`을 제거하고, `stopSystemImageBackup()`이 실행되면 다시 `hidden`을 추가하는 로직이 JS에 정확히 구현되어야 합니다. 이 로직이 누락되면 중단 버튼이 영원히 숨겨지거나, 시작 버튼이 영원히 숨겨질 수 있습니다.

---

### 4. 사용자의 질문과 관련된 핵심 발견점 (Auth 모달 문제

### [분석 청크 5: index.html (Part 5/7)]
제공된 코드 블록(`index.html` Part 5/7)은 **스냅샷 파일 탐색기(explorer-modal)**, **복원(restore-modal)**, **프로필 설정(profile-modal)**의 HTML 마크업으로 구성되어 있습니다.

사용자가 질문하신 `auth-pw-btn`, `auth-dropdown`, `auth-modal-overlay`, `modal-auth-setup` 및 관련 이벤트 핸들러는 **이 블록(5/7)에 포함되어 있지 않습니다.**

따라서, 이 블록 내에서 발견할 수 있는 것은 **기존 모달들의 구조적 문제점**과 **전체적인 모달 관리 패턴**에 대한 분석이며, 이는 `auth` 모달이 안 뜨는 원인을 간접적으로 추론하는 데 중요한 단서가 됩니다.

---

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

이 블록에는 3개의 주요 모달이 정의되어 있습니다.

| ID | 이름 | 역할 |
| :--- | :--- | :--- |
| `explorer-modal` | 스냅샷 파일 탐색 | 백업된 파일 목록을 탐색하고 검색하는 UI |
| `restore-modal` | 스냅샷 복원 | 복원 방식(원위치/안전 폴더)을 선택하고 복원을 시작하는 UI |
| `profile-modal` | 백업 프로필 설정 | 백업 대상 경로와 저장소 경로를 설정하는 UI |

**공통 구조:**
- 모든 모달은 `fixed inset-0 ... hidden` 클래스를 사용하여 기본적으로 숨겨져 있습니다.
- 각 모달 내부에는 `closeModal('modal-id')` 함수를 호출하는 닫기 버튼이 있습니다.
- `z-50` z-index를 사용하여 가장 위에 표시되도록 설정되어 있습니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

- **닫기 버튼:** `onclick="closeModal('explorer-modal')"` 등.
- **검색 입력:** `oninput="filterExplorerItems()"` (explorer-modal)
- **복원 모드 변경:** `onchange="toggleRestoreMode()"` (restore-modal)
- **폴더 선택:** `onclick="openDirectoryPicker('restore-target-dir')"` 등.
- **복원 시작:** `onclick="startRestore()"` (restore-modal)

**데이터 바인딩:**
- `#restore-snapshot-id`, `#restore-selected-paths`: 복원 대상 정보를 저장하는 hidden input.
- `#prof-id`, `#prof-name`, `#prof-sources`, `#prof-repo`: 프로필 정보를 저장하는 input/textarea.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

**[중요] `closeModal` 함수의 구현 방식에 따른 잠재적 충돌**

이 블록에서 `closeModal('modal-id')`이 호출되는 것을 볼 수 있습니다. 만약 `closeModal` 함수가 단순히 `document.getElementById(id).classList.add('hidden')`만 수행한다면, **외부 클릭(overlay click)으로 모달을 닫는 로직이 제대로 작동하지 않을 수 있습니다.**

**일반적인 모달 외부 클릭 닫기 패턴의 문제:**
```javascript
// 일반적인 패턴
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal('current-modal-id');
    }
});
```
**문제점:**
1. **다중 모달 충돌:** `explorer-modal`, `restore-modal`, `profile-modal`이 모두 `z-50`을 사용하므로, 동시에 여러 모달이 열려 있을 경우(예: explorer에서 restore를 열기 위해) z-index가 겹쳐서 클릭 이벤트가 잘못 전달될 수 있습니다.
2. **`e.target` vs `e.currentTarget`:** 만약 `document`에 걸린 리스너가 `e.target`을 검사하는데, 모달 내부 요소(버튼, input 등)를 클릭하면 `e.target`이 모달 내부 요소가 되어 `modal-overlay` 클래스를 가지지 않으므로 닫히지 않습니다. 이는 정상 동작이지만, **모달 배경(overlay)을 클릭했을 때** `e.target`이 overlay div 자체여야 합니다.
3. **`hidden` 클래스와 `display: none`:** Tailwind의 `hidden` 클래스는 `display: none`을 적용합니다. 만약 `closeModal`이 `hidden`을 추가하는데, `openModal`이 `hidden`을 제거하는 방식으로 구현되어 있다면, **CSS transition이나 애니메이션이 적용되지 않을 수 있습니다.**

**[특정 버그] `restore-modal`의 `#restore-target-dir-container`**
- `toggleRestoreMode()` 함수가 `inplace`와 `safe` 모드를 전환할 때, `#

### [분석 청크 6: index.html (Part 6/7)]
제공된 코드 블록(`index.html` Part 6/7)은 주로 **프로필 설정 모달**, **디렉토리 브라우저 모달**, 그리고 **인증(Auth) 관련 모달(설정, 로그인, 변경)**의 HTML 마크업으로 구성되어 있습니다.

사용자가 요청한 `auth-pw-btn`, `auth-dropdown`, `document` click 리스너와의 충돌 및 "마스터 비밀번호 미설정 시 모달이 안 뜨는" 원인에 대한 분석 결과는 다음과 같습니다.

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

*   **Profile Modal (프로필 설정):**
    *   `#prof-sources`, `#prof-repo`, `#prof-excludes` 등 백업 경로 및 제외 패턴 입력 필드.
    *   `#prof-schedule-type` (Interval/Daily 선택) 및 `onScheduleTypeChange()` 호출.
    *   `saveProfileFromModal()`: 프로필 저장 버튼.
*   **Browse Modal (디렉토리 선택):**
    *   `#browse-modal`: 디렉토리 탐색 UI.
    *   `selectCurrentBrowsePath()`: 현재 경로 선택 버튼.
*   **Auth Modals (인증 모달 그룹):**
    *   `#auth-modal-overlay`: **공통 오버레이**. `hidden` 클래스를 기본값으로 가지고 있으며, 내부에 3개의 서브 모달을 포함합니다.
    *   `#modal-auth-setup`: **최초 마스터 비밀번호 설정 모달**. `#form-auth-setup`과 `submitAuthSetup(event)` 핸들러를 가집니다.
    *   `#modal-auth-login`: **로그인 모달**. `#form-auth-login`과 `submitAuthLogin(event)` 핸들러를 가집니다.
    *   `#modal-auth-change`: **비밀번호 변경 모달**. `#form-auth-change`와 `submitAuthChangePassword(event)` 핸들러를 가집니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **Form Submit Events:**
    *   `onsubmit="submitAuthSetup(event)"`: `#form-auth-setup`에서 트리거.
    *   `onsubmit="submitAuthLogin(event)"`: `#form-auth-login`에서 트리거.
    *   `onsubmit="submitAuthChangePassword(event)"`: `#form-auth-change`에서 트리거.
*   **Button Click Events:**
    *   `onclick="closeModal('profile-modal')"`, `onclick="closeModal('browse-modal')"`: 기존 모달 닫기.
    *   `onclick="closeAuthModal()"`: 인증 모달 닫기 (변경 모달의 X 버튼).
    *   `onclick="openDirectoryPicker('prof-repo')"`: 디렉토리 피커 열기.
*   **Data Binding:**
    *   `#prof-schedule-type`의 `onchange="onScheduleTypeChange()"`: 스케줄 타입 변경 시 UI 토글(시간/일시 입력 필드 표시/숨김)을 제어할 것으로 추정.
    *   `#setup-remember`: 체크박스 상태는 JS에서 `localStorage` 또는 세션에 저장될 것으로 추정.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

**[핵심 발견: 마스터 비밀번호 미설정 시 모달이 안 뜨는 원인]**

1.  **`auth-pw-btn` 및 `auth-dropdown`의 부재:**
    *   제공된 코드 블록(6/7)에는 `id="auth-pw-btn"` 또는 `id="auth-dropdown"`가 **존재하지 않습니다**.
    *   이는 이 버튼들이 다른 블록(예: 헤더/네비게이션 영역, Part 1~5)에 위치해 있음을 의미합니다.
    *   **추정된 충돌 원인:** `auth-pw-btn`의 `onclick` 핸들러가 `#auth-modal-overlay`를 `hidden` 클래스를 제거하여 표시하는 로직을 가지고 있을 것입니다. 만약 이 버튼의 이벤트 핸들러가 `document`의 외부 클릭 리스너와 충돌하거나, `#auth-modal-overlay`의 자식 요소(`#modal-auth-setup`)가 `hidden` 상태인 채로 오버레이만 표시되면, **오버레이는 보이지만 실제 모달 콘텐츠는 보이지 않는 상태**가 됩니다.

2.  **`#auth-modal-overlay`와 `#modal-auth-setup`의 이중 `hidden` 클래스:**
    *   `#auth-modal-overlay`는 `class="hidden ..."`
    *   `#modal-auth-setup`도 `class="hidden ..."`
    *   **버그 가능성:** JS에서 `#auth-modal

### [분석 청크 7: index.html (Part 7/7)]
제공된 `index.html`의 마지막 블록(7/7)은 **비밀번호 변경 모달의 하단부**와 **스크립트 로드 순서**를 포함하고 있습니다.

사용자가 질문하신 `auth-pw-btn`, `auth-dropdown`, `auth-modal-overlay`, `modal-auth-setup`의 **HTML 마크업 자체는 이 블록에 포함되어 있지 않습니다** (이들은 앞선 블록 1~6에 위치할 가능성이 높음). 하지만, 이 블록에 포함된 `closeAuthModal()` 함수 호출과 스크립트 로드 순서를 바탕으로 **모달이 안 뜨는 원인**과 **충돌 가능성**을 정밀하게 추론할 수 있습니다.

### 1. 주요 함수/컴포넌트/UI 요소 및 핵심 역할

*   **비밀번호 변경 폼 (`#form-auth-change`)**:
    *   현재 비밀번호, 새 비밀번호, 확인 입력 필드 포함.
    *   `onsubmit="submitAuthChangePassword(event)"` 이벤트 핸들러를 통해 제출 처리.
    *   `#change-error` 영역을 통해 오류 메시지 표시.
*   **닫기 버튼**:
    *   헤더의 X 버튼과 폼 하단의 '취소' 버튼 모두 `onclick="closeAuthModal()"`을 호출.
*   **스크립트 로드 순서**:
    *   `backup_utils.js` → `backup_auth.js` → `backup_snapshots.js` → `backup_custom.js` → `backup_sysimage.js` → `app.js` 순으로 로드.
    *   **핵심**: `app.js`가 가장 마지막에 로드되므로, `closeAuthModal`, `submitAuthChangePassword` 등 전역 함수는 `app.js`에서 정의되어야 합니다.

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **`closeAuthModal()`**:
    *   이 블록에서 두 번 호출됨 (헤더 X 버튼, 취소 버튼).
    *   이 함수는 `app.js` 또는 `backup_auth.js`에서 정의되어야 하며, 모달 오버레이(`#auth-modal-overlay`)의 `display`를 `none`으로 설정하거나 클래스를 제거하는 로직을 포함할 것으로 추정.
*   **`submitAuthChangePassword(event)`**:
    *   폼 제출 시 호출.
    *   `event.preventDefault()`를 호출해야 하며, 비밀번호 검증 및 API 호출(또는 로컬 저장소 업데이트)을 수행할 것으로 추정.
*   **외부 클릭 감지 (Document Click Listener)**:
    *   이 블록에는 직접적으로 `document.addEventListener('click', ...)` 코드가 보이지 않습니다.
    *   그러나 `auth-modal-overlay`가 존재한다면, 일반적으로 `app.js`에서 `document.addEventListener('click', (e) => { if (e.target === overlay) closeAuthModal(); })` 형태의 로직이 구현되어 있을 가능성이 높습니다.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

#### 🔴 핵심 문제: 마스터 비밀번호 미설정 상태에서 모달이 안 뜨는 원인

이 블록만으로는 `auth-pw-btn`의 `onclick` 핸들러를 직접 확인할 수 없으나, **스크립트 로드 순서**와 **함수 정의 위치**를 통해 원인을 추론할 수 있습니다.

1.  **함수 정의 시점 문제 (가장 유력한 원인)**:
    *   `auth-pw-btn`의 `onclick` 핸들러(예: `onclick="openAuthModal()"`)는 HTML 마크업(블록 1~6)에 있습니다.
    *   이 버튼이 클릭될 때 호출되는 함수(`openAuthModal` 또는 유사한 이름)가 `app.js`에서 정의되어 있다면, **`app.js`가 로드되기 전에 버튼이 클릭되면 `ReferenceError: openAuthModal is not defined`** 에러가 발생하여 모달이 뜨지 않습니다.
    *   **해결책**: `app.js`의 `DOMContentLoaded` 이벤트 리스너에서 모달 관련 초기화 로직을 실행하거나, `auth-pw-btn`의 `onclick`을 인라인(`onclick="..."`)이 아닌 `addEventListener`로 `app.js` 내에서 바인딩해야 합니다.

2.  **외부 클릭 감지와의 충돌**:
    *   만약 `app.js`에서 `document.addEventListener('click', ...)`를 사용하여 외부 클릭 시 모달을 닫는 로직을 구현했다면, **모달이 열리기 전에** 이 리스너가 이미 활성화되어 있을 수 있습니다.
    *   **충돌 시나리오**:
        1.  사용자가 `auth-pw-btn`을 클릭.
        2