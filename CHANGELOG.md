# Changelog

이 문서는 BackupSystem의 릴리스 이력을 기록한다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르며,
버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따른다.

---

## [2.13.6] - 2026-10-06

### 변경
- 카카오톡 알림 모듈 및 호출부 제거 (`core/notifier.py`, `kakao_setup_helper.py`)
- 알림 실패 시 백업 결과에 영향을 주던 예외 처리 정리

---

## [2.13.5] - 2026-10-06

### 변경
- WORM 방어 한계를 검증된 사실만 남기도록 문서화 (`docs/design_worm_acl.md`)
- `disaster_recovery.py` 의 죽은 코드(`common_prefix`) 제거
- 배치·스크립트 개행 CRLF 정규화
- `scratch/` 테스트 산출물 git 추적 해제 (49개)

---

## [2.13.4] - 2026-10-06

### 수정
- **CRITICAL** `BackupLock` 이 프로세스 내 다른 스레드의 진행 중 백업을 무혈입 통과시키는 결함
  → 재진입 키를 `(repo_dir, thread_id)` 로 분리
- **CRITICAL** `ed25519_signature` 생성 실패가 조용히 무효화되던 문제
  → `raise RuntimeError` 로 백업 중단 (Fail-Closed)
- **HIGH** `auth_config.json` 손상 시 전체 API 가 무인증으로 개방되던 문제
  → 손상 감지 시 HTTP 500 Fail-Closed 차단
- **HIGH** 마스터 암호 최소 4자리 + 로그인 무제한 시도
  → 최소 8자리 + 5회 실패 시 5분 락아웃 (HTTP 429)
- **MEDIUM** 삭제·보존 권한 기본값이 fail-open 이던 문제
  → `authorized=False` 로 통일
- WORM 보호 주장 철회 및 오염된 테스트 산출물 정리

---

## [2.13.3] - 2026-10-06

### 수정
- **MEDIUM** 스냅샷 전자서명 실패를 로그만 남기고 진행하던 문제
  → 보안 경고 로깅 및 UI 콜백 통지
- **LOW** `put_bytes_blob` 임시 파일명 고정 → PID + 랜덤 hex 로 통일
- **LOW** 프로필 보존 기간(`retention_days`) 미명시 → 60일 명시

### 참고
- WORM 디렉토리 DeleteChild ACL 적용 시도는 이후 `2.13.4` 에서 철회됨

---

## [2.13.2] - 2026-10-06

### 수정
- **HIGH** 인증 Fail-Open (설정 파일 손상 시 API 무인증 개방)
- **HIGH** 마스터 암호 최소 길이 4자리 → 8자리
- **HIGH** 로그인 시 무제한 무차별 대입 가능 → 5회/5분 락아웃

---

## [2.13.1] - 2026-10-06

### 수정
- **CRITICAL** GC(정리)와 백업 실행 간 동시성 경합
  → `BackupLock` 재진입 지원 + Prune/GC 전역 락 적용
- **CRITICAL** 매니페스트 손실 시 `except: pass` 로 무음 무시되어 정상 블롭이 영구 삭제되던 문제
  → Fail-Closed 로 즉시 중단

### 추가
- `pytest` 를 `requirements.txt` 에 명시

---

## [2.13.0] - 2026-10-06

### 추가
- Track 2-17: 유휴 시간 Pack Consolidation 및 Delayed GC

---

## [2.12.0] - 2026-10-06

### 추가
- Track 2-16: Pack Container 프로덕션 정식 활성화, Dual-Read 지원

---

## [2.11.0] - 2026-10-05

### 추가
- Track 2-12~2-14: Multi-chunk Ingest 및 Assembly 결합, Zero-Touch 릴리즈

---

## 미배포 (main 브랜치)

### 수정
- **HIGH** `core/replication.py` 의 TOCTOU 경합
  → 동시 복제 시 8개 워커 중 7개가 `PermissionError` 로 실패하던 문제.
  CAS 블롭은 내용 주소 기반이므로 "이미 존재 = 동일 내용" 이며, 경합을 benign 으로 흡수
- 런타임 `NameError` 4건 (`web/app.py` 의 `logger`·`urllib`, `core/driver_backup.py` 의 `sys`,
  `cli.py` 의 `BlobStorage`) — 정상 경로에서 드러나지 않던 유형
- 테스트 10건 결함 해결 → **전체 스위트 최초 완주 (169 passed, exit 0)**

### 추가
- 오프사이트 복제 파이프라인 (`core/offsite.py`, robocopy 기반)
- `pytest.ini`, `.github/workflows/ci.yml`, `LICENSE`
- 회귀 테스트 `tests/test_replication_torace.py` (동시성 검증)

[2.13.6]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.13.6
[2.13.5]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.13.5
[2.13.4]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.13.4
[2.13.3]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.13.3
[2.13.2]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.13.2
[2.13.1]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.13.1
[2.13.0]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.13.0
[2.12.0]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.12.0
[2.11.0]: https://github.com/kks3365550/BackupSystem/releases/tag/v2.11.0
