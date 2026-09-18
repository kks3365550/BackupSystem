# 🛡️ 서버 & 시스템 증분 백업 및 스냅샷 매니저 v2.0.0
> **Meta Zstandard 초고속 압축 & 8코어 멀티프로세싱 병렬 파이프라인 탑재**

스마트 **증분 백업(Incremental Backup)**, **콘텐츠 해시 기반 데이터 중복 제거(Deduplication)**, **Zstandard 초고속 압축**, 그리고 **타임머신형 시점 복원(Point-in-time Restore)** 기능을 갖춘 엔터프라이즈급 백업 솔루션입니다.

---

## ✨ 주요 기능

- 🚀 **멀티코어 병렬 가속 (v2.0.0)**: 8~10개 CPU 코어를 동시 가동하는 병렬 파이프라인으로 대용량 파일 및 수만 개 파일을 기존 대비 5~8배 초고속 처리합니다.
- 🗜️ **Meta Zstandard (zstd) 고성능 압축 (v2.0.0)**: 기존 높은 압축률을 100% 유지하면서도 압축 속도를 3~5배 끌어올리고, 기존 zlib 백업본도 100% 자동 감지하여 오류 없이 복원합니다.
- ⚡ **One-Pass 스트리밍 I/O (v2.0.0)**: 단 한 번의 디스크 읽기로 SHA-256 해시 계산과 압축을 동시에 수행하여 디스크 I/O를 50% 절감합니다.
- 💾 **콘텐츠 기반 중복 제거 (Deduplication)**: 파일 내용의 SHA-256 해시를 기반으로 동일한 데이터는 중복 저장하지 않고 메타데이터만 생성하여 디스크 용량을 획기적으로 절감합니다.
- 🕒 **타임머신형 스냅샷 탐색 & 시점 복원**: 과거 어느 시점으로든 전체 파일 또는 선택한 폴더/파일을 그대로 완벽 복원할 수 있습니다.
- 🖥️ **모던 웹 GUI 대시보드 (v2.0.0)**: 실시간 진행률, 전송 속도(MB/s), 멀티코어 가속 상태, 저장소 통계 및 디스크 사용량 등을 한눈에 확인하고 제어할 수 있습니다.
- 🔄 **백그라운드 자동 스케줄러**: 지정된 주기마다 자동으로 백그라운드 증분 백업을 수행하고 보관 정책(Retention)에 따라 스냅샷을 자동 정리합니다.
- 💽 **윈도우 OS 전체 베어메탈 백업**: SSD 교체 시 윈도우 재설치 없이 부팅(EFI) 파티션 및 OS 전체를 100% 원상복구할 수 있는 기능 제공.

---

## 🚀 빠른 시작 (GUI 실행)

### 방법 1: 원클릭 실행 (배치 파일)
`start_backup_system.bat` 파일을 더블 클릭하면 백엔드 서버가 시작되고 기본 웹 브라우저에서 대시보드가 자동으로 열립니다.

### 방법 2: Python 명령어로 실행
```bash
python run.py
```
브라우저에서 `http://127.0.0.1:8765` 로 접속합니다.

---

## 💻 CLI 명령어 사용법

### 1. 백업 실행
```bash
# 기본 프로필 백업 실행
python cli.py backup

# 특정 프로필 또는 디렉토리 지정 백업
python cli.py backup --source "C:\Users\Username\Documents" --repo "D:\Backups\MyRepo"
```

### 2. 백업 스냅샷 목록 조회
```bash
python cli.py list-snapshots --repo "D:\Backups\MyRepo"
```

### 3. 특정 시점 복원 (Restore)
```bash
# 전체 스냅샷 복원
python cli.py restore --snapshot-id snap_20260830_091630_xxxx --target "C:\Restored"

# 특정 폴더/파일만 선택 복원
python cli.py restore --snapshot-id snap_20260830_091630_xxxx --target "C:\Restored" --select "configs/server.conf"
```

### 4. 스냅샷 무결성 검증 (Verify)
```bash
python cli.py verify --snapshot-id snap_20260830_091630_xxxx
```

### 5. 저장소 용량 및 중복 제거 절감 통계 확인
```bash
python cli.py stats --repo "D:\Backups\MyRepo"
```

---

## 📁 프로젝트 구조

```
백업시스템/
│
├── core/                         # 백업 핵심 엔진 모듈
│   ├── hasher.py                 # SHA-256 및 빠른 파일 변경 감지
│   ├── filter.py                 # 제외 패턴(Glob/Regex) 매칭
│   ├── storage.py                # 블롭(Blob) 저장소 & 중복 제거 & 압축 관리
│   ├── snapshot.py               # 스냅샷 생성, 인덱싱, 트리 매니페스트 관리
│   ├── restore.py                # 시점 복원 및 무결성 검증
│   ├── config.py                 # 프로필 및 설정 관리
│   └── scheduler.py              # 백그라운드 자동 스케줄러
│
├── web/                          # 모던 웹 GUI 대시보드
│   ├── app.py                    # FastAPI 백엔드 REST & SSE API
│   ├── static/
│   │   ├── app.js                # 프론트엔드 비동기 제어 및 실시간 갱신
│   │   └── style.css             # 모던 다크 테마 스타일
│   └── templates/
│       └── index.html            # 반응형 통합 대시보드 UI
│
├── data/                         # 설정 및 프로필 데이터베이스
├── cli.py                        # CLI 자동화 명령어 도구
├── run.py                        # GUI 서버 및 브라우저 자동 실행 엔트리포인트
├── start_backup_system.bat       # 원클릭 실행 배치 파일
├── test_backup_system.py         # 전체 수명주기 자동 검증 테스트
├── requirements.txt              # 의존성 패키지 목록
└── README.md                     # 사용 설명서
```
