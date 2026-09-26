# Qwen 대용량 자동 분할 분석 전체 산출물

## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]**
*   **보안 취약점 (Hardcoded API Key):** `updater.py` 내에 Firebase API Key가 소스 코드에 하드코딩되어 있습니다. 이는 코드베이스가 노출될 경우 Firestore 데이터 무결성 훼손 및 악성 업데이트 주입 공격을 허용하는 치명적 보안 결함입니다.
*   **롤백 불일치 상태 (State Mismatch):** `rollback` 로직이 파일 복원만 수행하고, 직전에 재시작된 프로세스(새 버전 또는 죽은 상태)를 명시적으로 종료/재시작하지 않는 경우, "파일은 구버전, 프로세스는 새버전(또는 Crash)"인 시스템 불일치 상태가 발생합니다. 이는 서비스 중단으로 이어질 수 있습니다.

**[BUG]**
*   **메모리 OOM 리스크:** `download_update` 함수가 `resp.read()`로 전체 파일을 메모리에 로드합니다. 대용량 업데이트(수백 MB) 시 메모리 부족으로 인한 크래시가 발생할 수 있습니다.
*   **플랫폼 의존성 및 인코딩 오류:** `safely_stop_running_backup_server`는 Windows 전용 PowerShell 스크립트를 사용하며, `*백업시스템*` 문자열 매칭은 인코딩(UTF-8 vs ANSI) 문제로 인해 실패할 가능성이 높습니다. Linux/Mac 환경에서는 프로세스 종료 로직이 완전히 무시됩니다.
*   **파일 잠금(PermissionError) 미처리:** 프로세스 종료 후 `time.sleep(1)`만 수행하고 파일 교체를 시도합니다. OS가 파일 핸들을 즉시 해제하지 않으면 `shutil.rmtree` 또는 `copy2`에서 `PermissionError`가 발생하여 업데이트가 실패합니다.

**[RISK]**
*   **헬스체크 타이밍 문제:** 재시작 후 `health_check(timeout=12)`가 실패하면 즉시 롤백을 시도하지만, 프로세스 부팅에 시간이 걸리는 경우를 고려하지 않아 불필요한 롤백이 발생할 수 있습니다.
*   **Zero-Leak 검사 한계:** `verify_update`의 ZIP 내부 민감 파일 검사 로직이 불완전할 경우, 악성 코드가 포함된 업데이트가 설치될 위험이 있습니다.

**[ACTION]**
1.  **API Key 분리:** `FIREBASE_API_KEY`를 환경 변수(`os.environ`) 또는 암호화된 설정 파일로 분리하세요.
2.  **스트리밍 다운로드 구현:** `download_update`를 `shutil.copyfileobj` 또는 `resp.read(chunk_size)` 기반의 스트리밍 방식으로 수정하여 메모리 사용량을 최소화하세요.
3.  **롤백 로직 강화:** `rollback` 함수 내부에서 반드시 **기존 프로세스 종료 -> 파일 복원 -> 구버전 재시작** 순서를 명시적으로 수행하도록 수정하세요.
4.  **파일 잠금 해제 대기 로직 추가:** 프로세스 종료 후 파일 잠금 해제 확인을 위한 재시도(Retry) 로직 또는 더 긴 대기 시간을 설정하세요.
5.  **크로스 플랫폼 지원:** 프로세스 종료 로직을 `psutil` 라이브러리 사용으로 대체하여 Windows/Linux/Mac 모두에서 동작하도록 재설계하세요.

**[DECISION REQUIRED]**
*   **Antigravity 승인 필요:** `psutil` 라이브러리 도입 및 API Key 환경 변수 분리 방안에 대한 최종 승인.
*   **사용자 승인 필요:** 롤백 시 프로세스 강제 종료 및 재시작 로직 변경에 따른 서비스 일시 중단 허용 범위 확인.

## PART 2. [COMPREHENSIVE AUDIT & ARCHITECTURE REPORT]

### 1. 시스템 아키텍처 개요
`updater.py`는 **Artifact Verifier & Safe Installer**의 핵심 오케스트레이터 역할을 수행합니다. 주요 파이프라인은 다음과 같습니다:
1.  **Check:** Firestore에서 최신 릴리스 메타데이터 조회.
2.  **Download:** HTTPS를 통한 ZIP 파일 다운로드.
3.  **Verify:** SHA-256 해시, Ed25519 서명, Zero-Leak 검사.
4.  **Install:** Staging 해제 -> 백업 -> 프로세스 종료 -> 파일 교체 -> 재시작 -> 헬스체크.
5.  **Rollback:** 헬스체크 실패 시 백업 복원 및 재시작.

### 2. 청크별 세부 분석 종합

#### [Part 1/2] 검증 및 전처리 로직
*   **핵심 함수:** `parse_version`, `check_for_update`, `download_update`, `verify_update`, `safely_stop_running_backup_server`, `health_check`, `rollback`.
*   **API 호출:** Firestore REST API (타임아웃 6초), HTTPS 다운로드 (타임아웃 30초).
*   **데이터 바인딩:** `release_info` 딕셔너리(버전, URL, 해시, 서명 등)를 Firestore 문서에서 추출.
*   **발견된 문제:**
    *   하드코딩된 Firebase API Key.
    *   `download_update`의 메모리 OOM 리스크.
    *   `safely_stop_running_backup_server`의 Windows 전용 로직 및 인코딩 문제.
    *   `verify_update`의 Zero-Leak 검사 한계.

#### [Part 2/2] 설치 및 오케스트레이션 로직
*   **핵심 함수:** `install_update`, `perform_full_update_pipeline`.
*   **프로세스 흐름:** Staging -> Backup -> Stop -> Apply -> Restart -> Verify.
*   **발견된 문제:**
    *   `rollback` 함수의 프로세스 처리 누락 (파일 복원만 수행).
    *   프로세스 종료 후 파일 잠금 해제 미확인.
    *   헬스체크 타임아웃과 롤백 타이밍 불일치.

### 3. Phase 3 (Artifact Verifier & Safe Installer) 설계 제안

1.  **보안 강화:**
    *   API Key를 환경 변수로 분리.
    *   Ed25519 서명 검증 로직을 강화하여 서명 불일치 시 즉시 중단.
    *   Zero-Leak 검사를 강화하여 ZIP 내부의 실행 파일, 스크립트, 민감 파일을 명시적으로 차단.

2.  **안정성 향상:**
    *   스트리밍 다운로드 구현.
    *   `psutil` 기반의 크로스 플랫폼 프로세스 종료 로직 도입.
    *   파일 잠금 해제 확인을 위한 재시도 로직 추가.
    *   `rollback` 로직을 "프로세스 종료 -> 파일 복원 -> 재시작" 순서로 재설계.

3.  **관측성(Observability) 강화:**
    *   각 단계별 로그 기록을 강화하여 실패 원인을 명확히 파악할 수 있도록 함.
    *   헬스체크 실패 시 상세 에러 메시지를 기록.

### 4. 최종 결론
기존 `updater.py`는 기본적인 업데이트 파이프라인을 갖추고 있으나, **보안(하드코딩 키)**, **안정성(메모리, 파일 잠금, 롤백 불일치)**, **크로스 플랫폼 지원** 측면에서 치명적인 결함이 존재합니다. Phase 3 설계 시에는 이러한 결함들을 반드시 수정하고, `psutil` 도입 및 API Key 분리 등 보안 및 안정성 강화 조치를 우선적으로 반영해야 합니다.

---
## 청크별 1차 분석 원본

### [분석 청크 1: updater.py (Part 1/2)]
제공된 `updater.py` (Part 1/2) 코드를 Phase 3(Artifact Verifier & Safe Installer) 설계 관점에서 정밀 분석한 결과입니다.

### 1. 주요 함수/컴포넌트 및 핵심 역할

| 함수명 | 핵심 역할 및 Phase 3 관련성 |
| :--- | :--- |
| `parse_version` | 시맨틱 버전 비교를 위한 튜플 변환. **Phase 3 검증 로직의 기준점**으로 사용됨. |
| `check_for_update` | Firestore REST API를 통해 최신 릴리스 메타데이터(버전, URL, 해시, 서명)를 조회. **Artifact 메타데이터 검증의 입력값**을 제공. |
| `download_update` | HTTPS를 통한 ZIP 파일 다운로드. **Artifact의 무결성 검증 전 단계**로, 임시 디렉토리에 저장. |
| `verify_update` | **Phase 3의 핵심 검증 로직.** SHA-256 해시, Ed25519 서명, ZIP 내부 민감 파일(Zero-Leak) 검사를 수행. |
| `safely_stop_running_backup_server` | 포트 8765를 점유한 프로세스를 PowerShell 스크립트로 선별 종료. **Safe Installer의 전제 조건**(파일 잠금 해제). |
| `health_check` | 재시작 후 포트 8765 소켓 연결성 확인. **Safe Installer의 성공/실패 판정 기준**. |
| `rollback` | 헬스체크 실패 시 백업 디렉토리에서 원복 및 재시작. **Safe Installer의 Fail-Safe 메커니즘**. |
| `install_update` | Staging 해제, 백업, 프로세스 종료, 파일 교체, 재시작, 헬스체크를 순차 수행. **Safe Installer의 메인 오케스트레이터**. |

### 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API 호출**:
    *   `check_for_update`: `urllib.request`를 사용하여 Firestore REST API (`https://firestore.googleapis.com/...`)를 호출. 타임아웃 6초.
    *   `download_update`: `urllib.request`를 사용하여 지정된 `download_url`에서 바이너리 데이터를 스트리밍 없이 전체 로드(`resp.read()`)하여 저장. 타임아웃 30초.
*   **데이터 바인딩/상태 관리**:
    *   **메타데이터**: Firestore의 `app_releases/latest` 문서에서 `version`, `download_url`, `sha256`, `signature`, `mandatory`, `changelog`, `min_supported_version` 필드를 추출하여 `release_info` 딕셔너리로 바인딩.
    *   **파일 시스템 상태**: `BASE_DIR`을 기준으로 `VERSION` 파일, `keys/release_ed25519.pub`, `backup/v{version}` 디렉토리의 존재 여부를 동적으로 확인.
    *   **프로세스 상태**: `Get-NetTCPConnection`을 통해 포트 8765의 `OwningProcess`를 식별하고, `Win32_Process`의 `CommandLine`을 검사하여 백업 시스템 프로세스임을 확인한 후 종료.

### 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

1.  **하드코딩된 보안 키 (중요)**:
    *   `FIREBASE_API_KEY = "AIzaSyCe21skNfRno3PPo-xRYCqfwh3jtboo7Ls"`가 소스 코드에 하드코딩되어 있습니다. 이는 보안 취약점이며, 환경 변수나 설정 파일로 분리해야 합니다.
2.  **`download_update`의 메모리 문제**:
    *   `content = resp.read()`로 전체 파일을 메모리에 로드한 후 디스크에 씁니다. 대용량 업데이트 파일(수백 MB 이상)의 경우 메모리 부족(OOM) 오류가 발생할 수 있습니다. 스트리밍 다운로드(`shutil.copyfileobj` 등)가 권장됩니다.
3.  **`safely_stop_running_backup_server`의 플랫폼 의존성**:
    *   `if not sys.platform.startswith("win"): return True`로 인해 **Windows 외 플랫폼(Linux/Mac)에서는 프로세스 종료 로직이 완전히 무시**됩니다. Phase 3가 크로스 플랫폼을 지원해야 한다면 이 로직은 재설계가 필요합니다.
    *   PowerShell 스크립트 내 `*백업시스템*` 문자열 매칭은 인코딩 문제(UTF-8 vs ANSI)로 인해 실패할 가능성이 있습니다.
4.  **`verify_update`의 Zero-Leak 검사 한

### [분석 청크 2: updater.py (Part 2/2)]
# `updater.py` (Part 2/2) 정밀 분석 보고서

## 1. 주요 함수/컴포넌트 및 핵심 역할

이 블록은 업데이트의 **최종 실행 단계(Install)** 와 **전체 파이프라인 오케스트레이션**을 담당합니다.

| 함수명 | 핵심 역할 |
| :--- | :--- |
| `install_update` | 실제 파일 교체, 백업, 프로세스 종료, 재시작, 헬스체크 및 롤백을 수행하는 핵심 로직. |
| `perform_full_update_pipeline` | `check` -> `download` -> `verify` -> `install` 순서를 연결하는 엔트리포인트. |

**주요 프로세스 흐름:**
1.  **Staging:** 임시 디렉토리에 ZIP 압축 해제.
2.  **Backup:** 현재 버전의 `core`, `web`, `keys` 폴더 및 핵심 스크립트를 `backup/v{version}`에 보존.
3.  **Stop:** 포트 8765를 사용하는 기존 백업 서버 프로세스 안전 종료.
4.  **Apply:** Staging의 내용을 Target 디렉토리로 복사/교체.
5.  **Restart:** `start_silent.vbs` 또는 `pythonw.exe`를 통해 무창 백그라운드 재시작.
6.  **Verify:** 포트 8765 헬스체크 수행. 실패 시 `rollback` 호출.

---

## 2. 이벤트 핸들러, API 호출, 데이터 바인딩 상태

*   **API/외부 호출:**
    *   `safely_stop_running_backup_server(8765)`: 기존 프로세스를 종료하는 로직 (Part 1에서 정의된 것으로 추정).
    *   `subprocess.Popen`: `wscript.exe` 또는 `pythonw.exe`를 통해 새 프로세스를 생성.
    *   `health_check(port=8765, timeout=12)`: HTTP 또는 Socket 기반의 서비스 생존 확인 (Part 1에서 정의된 것으로 추정).
*   **데이터 바인딩/상태:**
    *   `current_ver`: `get_current_installed_version()`으로 가져온 현재 설치 버전.
    *   `rel`: `check_for_update()`에서 반환된 업데이트 정보 (버전, SHA256, 서명 등).
    *   `zip_file`: 다운로드된 업데이트 파일 경로.
*   **이벤트 핸들러:**
    *   `try-except-finally` 블록을 통해 예외 발생 시 `rollback`을 강제 호출하고, `finally`에서 임시 파일(`staging_dir`, `zip_path`)을 정리하는 구조입니다.

---

## 3. 발견된 버그, 예외 누락, 하드코딩, 동작하지 않는 요소

### 🔴 치명적 버그 및 리스크

1.  **`rollback` 함수의 불완전한 정의 가능성 (Part 1 의존성):**
    *   `rollback(backup_ver_dir, target_dir)`이 호출되지만, 이 함수가 Part 1에 정의되어 있는지 확인이 필요합니다. 만약 `rollback`이 단순히 파일을 복원하는 것이라면, **재시작된 프로세스를 어떻게 처리할지**가 문제입니다.
    *   **문제점:** 헬스체크 실패 시 `rollback`을 호출하지만, **직전에 재시작한 프로세스(Step 5)는 여전히 실행 중일 수 있습니다.** `rollback`이 파일만 복원하고 프로세스를 다시 종료/재시작하지 않으면, 시스템은 "파일은 구버전인데 프로세스는 새버전(또는 죽은 상태)"인 불일치 상태에 빠집니다.
    *   **수정 제안:** `rollback` 내부에서 반드시 프로세스를 종료하고, 구버전으로 재시작하는 로직이 포함되어야 합니다.

2.  **`safely_stop_running_backup_server`의 실패 처리 누락:**
    *   Step 3에서 프로세스를 종료하고 `time.sleep(1)`을 하지만, 프로세스가 실제로 종료되지 않았거나 파일이 잠겨(Locked) 있는 경우 Step 4의 `shutil.rmtree` 또는 `copy2`가 `PermissionError`를 발생시킬 수 있습니다.
    *   **수정 제안:** 프로세스 종료 후 파일 잠금 해제 확인 또는 재시도 로직이 필요합니다.

3.  **`health_check`의 타임아웃과 롤백 타이밍:**
    *   `health_check(timeout=12)`가 실패하면 즉시 `rollback`을 호출합니다. 하지만 `subprocess.Popen`으로 재시작한 프로세스가 완전히 부팅되는 데 시간이 걸릴 수 있습니다.
    *   **리스크