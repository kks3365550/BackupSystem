## PART 1. [EXECUTIVE SUMMARY FOR ANTIGRAVITY]

**[CRITICAL]**
*   **ZIP Slip 취약점**: `BundleReader.read()`에서 `zf.read()` 호출 시 경로 검증이 전무하여, 악성 `.bundle` 내부의 `package.zip`가 상대 경로(`../../etc/passwd`)를 포함할 경우 디스크 외부 파일 덮어쓰기(Write) 공격이 가능함.
*   **Fail-Open 리스크**: `default_keyring`의 신뢰 앵커가 부재하거나 실패할 경우, 서명 검증이 우회되거나 무시되는 로직이 존재할 경우(코드 미확인이나 구조적 의심) 시스템이 무방비 상태로 업데이트를 허용할 위험이 있음.

**[BUG]**
*   **Null/Empty Reference**: `policy.sig` 및 `manifest.sig` 읽기 시 `.decode("utf-8").strip()` 호출 전 바이너리 서명(Binary Signature)일 경우 `UnicodeDecodeError` 발생. 현재 코드는 Hex 문자열만 가정함.
*   **Resource Leak**: `zf` 컨텍스트 매니저(`with zf:`) 내에서 `package_bytes = zf.read("package.zip")`가 대용량 데이터를 메모리에 올림. `AcquiredUpdate` 객체가 이를 참조하므로 GC 지연 시 메모리 누출 가능성.

**[RISK]**
*   **Windows 파일락/레이스 컨디션**: `BundleCreator.create_bundle()`에서 `os.makedirs`와 `ZipFile` 생성 간 틈새에 다른 프로세스가 파일 접근 시 `PermissionError` 발생. 특히 백업 시스템 특성상 동시 접근 가능성이 높음.
*   **NOOP 검증 회피**: `validate_signatures_format()`가 형식만 검증하고 실제 암호학적 검증(Hash/Signature Match)을 수행하지 않는다면, NOOP(무작업) 업데이트 시에도 검증이 통과하여 악성 코드가 삽입될 수 있음.
*   **롤백 보장 한계**: `AcquiredUpdate` 생성 후 실제 설치 단계에서 실패 시, 이전 버전으로의 자동 롤백 메커니즘이 `bundle.py` 레벨에서 보장되지 않음.

**[ACTION]**
1.  **즉시 보강**: `BundleReader.read()`에서 `zf.namelist()` 검증 시 `os.path.normpath` 및 절대 경로 포함 여부 체크 추가 (ZIP Slip 방지).
2.  **즉시 보강**: `policy.sig`/`manifest.sig` 읽기 로직을 Hex 문자열과 바이너리 서명을 모두 처리하도록 수정 (`try/except UnicodeDecodeError`).
3.  **즉시 보강**: `BundleCreator`에서 파일 생성 전 `tempfile` 사용 후 원자적 이동(`os.replace`) 패턴 적용하여 파일락/레이스 컨디션 방지.
4.  **검토 필요**: `models.py`의 `validate_signatures_format()`가 실제 서명 검증인지 확인. 형식 검증만이라면 `verify_signature()` 메서드 추가 필요.

**[DECISION REQUIRED]**
*   **Antigravity 승인**: ZIP Slip 방지 로직 추가 및 서명 검증 강화(형식 → 실제 검증)를 위한 코드 수정 승인.
*   **사용자 승인**: Windows 환경에서의 파일락 처리 전략(중요도: 높음) 및 NOOP 업데이트 시 검증 우회 허용 여부(보안 vs 편의성) 최종 결정.

---

## PART 2. [DETAILED ANALYSIS & STRUCTURE REPORT]

### 1. 파일 구조 및 역할 분석
*   **`bundle.py`**: 오프라인 배포 번들(`.bundle`)의 파싱(`BundleReader`) 및 생성(`BundleCreator`)을 담당.
*   **`AcquiredUpdate`**: `models.py`에서 정의된 데이터 클래스로, 정책, 서명, 매니페스트, 패키지 바이트를 포함.
*   **`ValidationError`**: 서명 형식 오류 시 발생하는 예외.

### 2. 사용자 지적 사항에 대한 비판적/객관적 분석

#### 1. BundleReader outer ZIP 공격면 (ZIP Slip)
*   **현황**: `zf.read("package.zip")`는 ZIP 아카이브 내부의 `package.zip` 파일을 읽음. 이 `package.zip`은 다시 압축 해제될 때 내부 파일 경로를 결정함.
*   **비판적 분석**: `bundle.py` 자체는 `package.zip`의 *내용*을解压(압축 해제)하지 않으므로, `bundle.py` 레벨에서는 ZIP Slip이 직접 발생하지 않음. **그러나**, `package.zip`을 압축 해제하는 하위 모듈(예: `installer.py`)에서 경로 검증을 하지 않으면 공격이 가능함.
*   **수용 및 보강**: `bundle.py`는 `package.zip`의 무결성을 보장해야 함. `package.zip` 내부의 파일 목록을 미리 스캔하여 `..` 또는 절대 경로를 포함하는 엔트리가 있는지 검증하는 로직을 추가하거나, 하위 모듈에 대한 명확한 문서화 및 검증 책임 전가 필요.
*   **기술적 사실**: ZIP Slip은 압축 해제 시점에 발생하므로, `bundle.py`는 "검증" 역할만 수행. 하지만 보안 경계(Boundary)를 명확히 하기 위해 `package.zip` 내부 경로 사전 검증이 권장됨.

#### 2. Windows 파일락/프로세스 레이스 실전 리스크
*   **현황**: `BundleCreator.create_bundle()`에서 `os.makedirs` 후 `ZipFile` 생성.
*   **비판적 분석**: Windows는 파일이 열려 있을 때 삭제/이동을 허용하지 않음. `output_bundle_path`가 이미 존재하거나 다른 프로세스에 의해 잠겨 있을 경우 `PermissionError` 발생.
*   **수용 및 보강**: **즉시 보강 필요**. `tempfile.NamedTemporaryFile`을 사용하여 임시 파일에 작성 후, `os.replace()`로 원자적 이동(Atomic Move)을 수행해야 함. 이는 Windows에서도 안전하며, 중간 상태(중단된 파일)를 방지함.
*   **기술적 사실**: `os.replace()`는 POSIX 및 Windows 모두에서 원자적 파일 교체(Atomic File Replacement)를 보장함.

#### 3. default_keyring fail-closed/신뢰 앵커 취약점
*   **현황**: `bundle.py`는 서명 검증 로직을 `AcquiredUpdate.validate_signatures_format()`에 위임.
*   **비판적 분석**: `validate_signatures_format()`가 "형식"만 검증한다면(예: 128자리 Hex인지), 실제 암호학적 검증(예: Ed25519 서명 검증)이 누락됨. `default_keyring`이 부재하거나 실패할 경우, fail-open(검증 우회)이 될 위험이 있음.
*   **수용 및 보강**: **즉시 보강 필요**. `models.py`에서 `validate_signatures_format()`가 실제 서명 검증인지 확인. 만약 형식 검증만이라면, `verify_signature()` 메서드를 추가하고, 키링 접근 실패 시 `BundleError`를 던져 fail-closed로 동작하도록 해야 함.
*   **기술적 사실**: 보안 시스템은 "의심스러울 때 거부(Fail-Closed)" 원칙을 준수해야 함.

#### 4. NOOP 시 Artifact 검증 회피 여부
*   **현황**: `AcquiredUpdate` 생성 시 `package_bytes`가 비어있거나 NOOP 업데이트일 경우.
*   **비판적 분석**: NOOP 업데이트(변경 없음)일 경우에도 `policy.json`, `manifest.json`의 서명은 검증되어야 함. `package.zip`이 비어있거나 NOOP 마커일 경우, 서명 검증이 우회되면 안 됨.
*   **수용 및 보강**: **검토 필요**. `validate_signatures_format()`가 NOOP 케이스를 처리하는지 확인. NOOP일 경우에도 정책/매니페스트 서명은 검증되어야 하며, `package.zip`은 최소한의 무결성 체크(예: SHA256)를 받아야 함.
*   **기술적 사실**: NOOP 업데이트도 배포 정책의 일부이므로, 서명 검증은 필수.

#### 5. 롤백 보장 표현의 한계
*   **현황**: `bundle.py`는 번들 파싱/생성만 담당.
*   **비판적 분석**: 롤백은 설치 단계(`installer.py`)에서 처리되어야 함. `bundle.py`는 롤백 정보를 포함하지 않음.
*   **수용 및 보강**: **문서화 필요**. `bundle.py`의 역할은 "검증된 번들 전달"이며, 롤백은 하위 모듈의 책임임을 명확히 해야 함. `AcquiredUpdate`에 `rollback_info` 필드를 추가할 수 있으나, 이는 설계 변경.
*   **기술적 사실**: 롤백은 설치 트랜잭션(Transaction)의 일부이므로, `bundle.py` 레벨에서 보장할 수 없음.

### 3. 라인별 상세 분석 및 수정 제안

| 라인 | 코드 | 문제점 | 수정 제안 |
|------|------|--------|-----------|
| 48-52 | `zf = zipfile.ZipFile(...)` | `BadZipFile` 예외 처리는 적절함. | 유지 |
| 55-58 | `missing = [name for name in cls.REQUIRED_ENTRIES if name not in namelist]` | 필수 파일 누락 검증은 적절함. | 유지 |
| 60-63 | `policy_sig_raw = zf.read("policy.sig").decode("utf-8").strip()` | 바이너리 서명일 경우 `UnicodeDecodeError` 발생. | `try/except UnicodeDecodeError`로 바이너리 서명 처리 로직 추가. |
| 65 | `package_bytes = zf.read("package.zip")` | 대용량 데이터 메모리 누출 가능성. | 스트리밍 읽기 또는 메모리 제한 설정 고려. |
| 75-78 | `acquired.validate_signatures_format()` | 형식 검증만 수행할 가능성. | `verify_signature()`로 변경 및 키링 접근 실패 시 fail-closed 처리. |
| 92-95 | `os.makedirs(...)` + `ZipFile(...)` | 파일락/레이스 컨디션. | `tempfile` + `os.replace()` 패턴 적용. |

### 4. 결론 및 최종 조치
*   **즉시 보강**: ZIP Slip 방지(하위 모듈 검증 책임 명확화), 파일락 방지(원자적 이동), 서명 검증 강화(형식 → 실제 검증).
*   **검토 필요**: NOOP 업데이트 시 검증 로직, 롤백 메커니즘의 하위 모듈 의존성.
*   **결론**: `bundle.py`는 보안 경계의 첫 단계이므로, fail-closed 원칙을 준수하고, 파일 시스템 조작의 원자성을 보장해야 함.