# CI 1차 실행 실패 분석 및 수정 (2026-10-07)

## 요약

첫 push(`2ae7f34`) 에서 CI 잡 2개가 실패했다.

```
정적 분석 (pyflakes) : failure
회귀 테스트          : failure  (배포 빌드는 needs 때문에 skipped)
```

로컬에서는 전부 통과했다. 로컬에서 안 잡힌 이유는 **실제 로그를 받고 나서** 알았다.

## 실패 1: pyflakes 22건 (`core/updater_v2`)

로컬에서는 `web/app.py`, `core/replication.py` 만 검사해서 몰랐다.
CI 는 `core` 디렉터리 전체를 검사하므로 구버전 모듈 `core/updater_v2` 의
결함이 처음 드러났다.

### 진짜 코드 결함 1건

```python
class SafetyViolationError(SecurityError if "SecurityError" in dir(__builtins__) else Exception):
```

pyflakes: `undefined name 'SecurityError'`

이 조건식은 의도가 불분명하다. `__builtins__` 는 CPython 에서
모듈로 import 할 때는 dict, 모듈 안에서 직접 실행될 때는 모듈 객체가 된다.
`dir()` 결과가 환경에 따라 달라진다.

- 모듈 import 시: `dir(dict)` → `'SecurityError'` 없음 → `Exception`
- 구문 컴파일 단위 실행 시: `dir(module)` → `'SecurityError'` 있음 → `SecurityError`

같은 코드가 실행 방식만 달라져 **부모 예외 타입이 바뀐다.** 그 결과
`except Exception` 은 항상 잡지만, `except SecurityError` 는 한쪽에서만
작동한다. 잡는 쪽이 조용히 달라지면 검증 실패가 삼켜질 수 있다.

수정: `Exception` 으로 고정하고 이력을 주석에 남겼다.

```python
class SafetyViolationError(Exception):
    """...
    이전 코드는 `SecurityError if "SecurityError" in dir(__builtins__) else Exception`
    이었다. __builtins__ 는 dict 또는 module 두 형태가 있어 실행 환경마다
    결과가 달라졌다. 상위 예외 타입을 바꾸지 않고 Exception 으로 고정한다.
    """
```

### 나머지 21건: 미사용 import / 미사용 변수

```
core/updater_v2/bundle.py:29          'typing.Optional' imported but unused
core/updater_v2/bundle.py:30          'pathlib.Path' imported but unused
core/updater_v2/installer.py:266      local variable 'package_zip_path' ...
... 총 21건
```

`git log` 기준 이 모듈은 2026-09-26/27 이후 수정되지 않았다.
v2.9.11 OTA 모던화 때 만들어지고 손대지 않은 코드다.

**제거한 뒤 검증:**

```
12개 모듈 전부 import 성공 (성공 12 / 실패 0)
pyflakes 0건
```

미사용 import 제거는 문법만 바꾸는 것이라 위험이 낮지만,
`import A, B` 형태에서 B만 지우면 A가 깨질 수 있다.
그래서 전체 모듈 import 검증으로 확인했다.

## 실패 2: 회귀 테스트 수집 에러 2건

CI 로그 전문 (GitHub Actions 로그 다운로드):

```
ERROR collecting System Volume Information
E   PermissionError: [WinError 5] Access is denied: 'D:\System Volume Information'

ERROR collecting a/BackupSystem/BackupSystem/tests/test_web_auth_api.py
E   RuntimeError: The starlette.testclient module requires the httpx2 package to be installed.
```

### 원인 2-A: `\` 줄바꿈 (PowerShell 문법 오류)

CI 는 `windows-latest` + 기본 셸이 PowerShell 이다.
`steps[].run` 에 사용한 구문이 이렇다:

```yaml
run: |
  python -m pytest -q \
    tests/test_api_contract.py \
    tests/test_updater.py
```

`\` 로 줄을 잇는 것은 **Linux 셸 문법**이다. PowerShell 에서는
백슬래시가 그대로 인자로 전달된다. 그러면 pytest 가

```
pytest -q \ tests/test_a.py tests/test_b.py ...
```

를 받게 되고, 단독 `\` 인자는 현재 드라이브 루트(`D:\`)로 해석된다.
pytest 는 그 경로에서 테스트를 수집하려 시도하다가
`D:\System Volume Information` 에서 `PermissionError` 가 난다.

**근본 원인**: `norecursedirs` 로 이걸 막을 수 없었다.
`pytest.ini` 의 `norecursedirs` 는 재귀 탐색 대상만 제외하지만,
여기서는 `\` 를 **명시적 인자로 준 것**이 문제다. 인자로 준 경로는
설정과 무관하게 수집한다.

**수정**: 명령을 한 줄로 썼다.

```yaml
run: python -m pytest -q tests/test_api_contract.py tests/test_backup_logging.py ...
```

`\ ` 가 사라졌으므로 드라이브 루트가 인자로 들어갈 수 없다.

### 원인 2-B: `httpx2` 누락 (재현성 갭)

```
RuntimeError: The starlette.testclient module requires the httpx2 package
```

`requirements.txt` 에 `fastapi` 와 `starlette` 는 transitively 들어오지만
`httpx2` 는 없다. 로컬 `.venv` 에는 우연히 `httpx` (0.28.1) 가 있어서
테스트가 통과했다.

```
로컬 venv : httpx 0.28.1  →  deprecation 경고만 뜨고 동작
CI (clean): httpx 없음   →  RuntimeError
```

이것이 어제 말한 "재현성 갭"의 실제 사례다.
**로컬에 우연히 설치돼 있던 것이 로컬 테스트 통과의 이유였다.**

수정: `requirements.txt` 검증 도구 항목에 추가.

```
httpx2>=2.0.0
```

설치 후 확인:

```
httpx  0.28.1
httpx2 2.13.1
GET /api/auth/status -> 200
```

## 검증 결과

```
pyflakes (CI 동일 명령)          0건
CI 게이트 13개 파일             89 passed  (수정 전 79 passed)
```

## 교훈 (다음 세션용)

### 1. 로컬 통과 ≠ CI 통과

로컬 `.venv` 는 3가지가 CI 와 달랐다.

| 항목 | 로컬 | CI |
|---|---|---|
| 검사 범위 | 일부 파일 | `core` 전체 |
| httpx | 우연히 설치됨 | 없음 |
| 셸 | PowerShell 직접 실행 | pwsh -command |

첫 두 개는 재현성 문제다. 로컬 `.venv` 를 수동으로 맞춰도
**앞으로 새 의존성이 늘 때마다 재발한다.** `requirements.txt` 가
완전한 선언이 되어야 그게 막힌다.

### 2. 셸 문법을 다른 셸에서 검증해야 한다

`\` 줄바꿈은 로컬에서 절대 실행되지 않는 코드였다.
로컬에서 `python -m pytest` 를 직접 치면 되니까.
CI 파일 안의 명령은 로컬에서 실행되지 않기 때문에, 내가 쓴 문법을
검증할 방법이 없었다.

### 3. GitHub Actions 로그를 실제로 읽어야 한다

추측으로 "httpx 누락 같으니" 하고 끝냈을 수 있다.
`gh run view --log-failed` 로 20초면 정확한 원인이 나온다.
API(`/logs`)는 403 이지만 `gh` CLI 는 인증이 있어서 동작한다.

```powershell
gh run view <run-id> --repo kks3365550/BackupSystem --log-failed
```