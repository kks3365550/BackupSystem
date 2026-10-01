# 🛡️ BackupSystem: Windows 3-Tier Immutable Hybrid Backup Manager
> **Windows 업무 및 엔터프라이즈 환경을 위한 3계층 불변(Immutable) 하이브리드 백업 매니저**  
> *VSS 무중단 일관성 · Content-Addressable Storage · Zstandard 멀티코어 압축 · WORM 불변성 · 11ms 초저지연 캐시 · Windows BMR 연동*

---

## 📌 1. 개요 (Overview)

**BackupSystem**은 Windows PC 및 워크스테이션 환경에서 발생하는 데이터 손실, 랜섬웨어 변조, 물리적 SSD 장애를 다각도로 방어하기 위해 설계된 **3계층(3-Tier) 하이브리드 백업 솔루션**입니다.

글로벌 범용 클라우드 백업 도구와의 단순 기능 경쟁을 지양하고, **Windows 실무 환경에서의 무중단 파일 일관성(VSS), 초저지연 메타데이터 조회(Snapshot Cache), 랜섬웨어 변조 방지(WORM), 그리고 물리적 SSD 교체 시의 무인 복구(WinRE)**라는 실질적 엔지니어링 목표에 집중하여 최적화되었습니다.

---

## 🏛️ 2. 아키텍처: 3계층(3-Tier) 복구 모델

단일 엔진으로 모든 장애를 해결하려는 무리한 설계를 배제하고, 장애 유형과 복구 목표 시간(RTO)에 따라 명확히 역할을 분리한 3계층 방어선을 운용합니다.

```text
                        [ BackupSystem ]
                               │
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
   [ Tier 1 ]             [ Tier 2 ]             [ Tier 3 ]
   CAS Engine           Windows Native         Standalone DR
  (Snapshot/Restore)    (wbadmin / WinRE)   (disaster_recovery.py)
        │                      │                      │
 • 매일 증분 백업 (1분 미만)• 주간/월간 시스템 이미지• 파이썬 표준 라이브러리 구동
 • VSS 무중단 일관성   • OS Critical Volumes   • 저장소 Bit-Rot 전수 감사
 • WORM 불변성 보호     • 빈 SSD 물리 교체 복구 • 독립 실행 긴급 데이터 구출
 • 11ms 초고속 메타데이터 • WinRE 무인 복구 파이프라인
```

| 계층 | 전담 모듈 | 복구 시나리오 및 대상 | 목표 복구 시간 (RTO) |
|:---|:---|:---|:---:|
| **Tier 1 (CAS)** | `core/snapshot.py`<br>`core/restore.py` | 일상 업무 중 파일 실수 삭제, 이전 버전 롤백, 랜섬웨어 감염 시 시점 복원 | **초(Seconds) 단위** |
| **Tier 2 (BMR)** | `core/system_image.py`<br>`Windows WinRE` | 메인보드/SSD 물리적 고장, 부팅 불가(BSOD) 시 새 빈 SSD에 OS 전체 복구 | **수십 분 단위** |
| **Tier 3 (DR)** | `disaster_recovery.py` | 백업 관리 서버 프로세스가 완전히 파괴된 비상 상황에서 독립 데이터 추출 | **즉시 실행** |

---

## ✨ 3. 핵심 기능 상세 (Features in Depth)

### 3.1. Zero-Lock VSS 네이티브 트랜잭션 백업
- Windows 볼륨 섀도 복사본 서비스(VSS)를 백업 엔진의 핵심 경로에 직접 통합하였습니다.
- 사용자가 작업 중인 열린 오피스 문서, 실행 중인 로컬 데이터베이스(SQLite, MDB), 잠긴 레지스트리 하이브 파일을 작업 중단이나 "파일이 사용 중"이라는 에러 없이 100% 트랜잭션 완결 상태로 스냅샷합니다.

### 3.2. Content-Addressable Storage (CAS) & Zstandard 멀티스레드 압축
- 파일 내용의 암호학적 SHA-256 해시를 주소로 사용하는 불변 CAS 블롭 저장소를 구현했습니다.
- 동일한 내용은 단 한 번만 저장되는 중복 제거(Deduplication)를 지원하며, Meta의 Zstandard(zstd 레벨 3~9) 멀티코어 압축 엔진을 통해 I/O 병목을 최소화하면서 높은 압축률을 달성합니다.

### 3.3. Invalidation-Driven SnapshotMetadataCache (~11ms)
- 대규모 디렉터리 스캔 지연을 해결하기 위해 메모리 기반 메타데이터 캐시 계층을 탑재했습니다.
- 외부 변경을 감지하는 디렉터리 핑거프린트 안전망과 이벤트 기반 무효화(Invalidation)를 결합하여, **22만 개 파일 환경에서도 평균 11.46ms(Warm Cache)**의 초저지연 스냅샷 조회를 보장합니다.

### 3.4. WORM (Write Once Read Many) 소프트웨어 불변성 보호
- 스냅샷 생성 즉시 메타데이터와 저장소 블롭 파일에 WORM 보호를 적용합니다.
- 악의적인 랜섬웨어나 오작동 프로세스가 과거의 백업 파일이나 스냅샷 매니페스트를 임의로 덮어쓰거나 수정할 수 없도록 엔진 레벨에서 원천 차단합니다.

### 3.5. Windows Native BMR (Bare-Metal Recovery) 연동
- Microsoft Windows 표준 백업 엔진(`wbadmin start backup -allCritical`)을 오케스트레이션하여 EFI 시스템 파티션, 복구 파티션, C: OS 전체 볼륨을 포함하는 시스템 이미지를 보관합니다.
- 물리 SSD가 사망하더라도, 독자 WinPE 제작 없이 Microsoft 공식 Windows 설치/복구 미디어(WinRE)의 **[시스템 이미지 복구]**를 통해 새 빈 SSD에 파티션 자동 생성부터 부팅 복구까지 완벽하게 수행합니다.

### 3.6. 독립형 무설치 재해복구 CLI (`disaster_recovery.py`)
- 백업 서버 및 웹 대시보드가 구동 불가능한 극단적인 환경에 대비하여, 파이썬 표준 라이브러리(zlib, hashlib)만으로 동작하는 단일 무설치 CLI 도구를 저장소 루트에 상시 자동 동기화합니다.
- 저장소 전체 블롭의 SHA-256 Bit-Rot(침묵의 데이터 손상) 전수 감사(`--audit`) 및 긴급 복원(`--restore`)을 독립적으로 실행할 수 있습니다.

### 3.7. Durable Queue & Tailscale P2P 오프사이트 복제
- 로컬 백업 완료 즉시 SQLite 기반의 Durable Queue에 복제 작업을 기록하고 백그라운드 워커가 오프사이트 노드로 전송합니다.
- 네트워크 단절이나 대상 머신 오프라인 시 자동 백오프(Backoff) 재시도를 수행하며, Tailscale P2P 암호화 터널을 통해 외부 클라우드 중개 없이 안전하게 원격 전송됩니다.

### 3.8. Ed25519 디지털 서명 기반 Zero-Downtime OTA 업데이트
- GitHub Releases API를 단일 공식 채널로 하여 새로운 버전 감지, 다운로드, 무결성 검증, 스왑 및 무창 재기동을 100% 무인 자동화합니다.
- 모든 배포 패키지는 릴리즈 파이프라인에서 개발자 전용 Ed25519 개인키로 전자 서명되며, 클라이언트는 공개키 검증 실패 시 설치 전 즉각 폐기합니다.

---

## 🎯 4. 객관적 장점 및 차별성 (Strengths)

1. **Windows 실무 환경에 완벽한 무간섭성**: VSS 통합으로 파일 잠금 충돌이나 엑셀 닫기 안내 없이 백그라운드에서 투명하게 정합성을 확보합니다.
2. **초저지연 관리자 경험**: 수십만 파일 환경에서도 수초~수십초의 로딩 없이 10ms 대의 즉각적인 스냅샷 조회 및 브라우징을 제공합니다.
3. **랜섬웨어 훼손 불가(Immutable)**: 과거의 복원 지점은 소프트웨어 레벨에서 수정이 원천 거부됩니다.
4. **외부 클라우드 서비스 종속성 제로**: 외부 유료 클라우드나 서드파티 중개 서버 없이, 사내 폐쇄망 또는 순수 Tailscale 내부망만으로 완전 자립 구동됩니다.
5. **물리적 재해에 대한 명확한 복구 경로**: 파일 복구에만 머무르지 않고, SSD 하드웨어 사망 시의 WinRE 시스템 복구 파이프라인을 온전히 제공합니다.

---

## ⚖️ 5. 엔지니어링 트레이드오프 및 한계 (Trade-offs & Scope)

BackupSystem은 설계 목적상 다음과 같은 기술적 한계와 트레이드오프를 투명하게 인정합니다:

1. **Whole-File CAS의 한계**:
   - 현재 엔진은 **파일 단위(Whole-File) SHA-256 해싱**을 채택하고 있습니다.
   - 일반 문서, 소스코드, 이미지 등의 환경에서는 복잡도가 낮고 복원 신뢰성이 매우 뛰어납니다.
   - 단, **수십 GB급 대용량 가상머신(VHDX)이나 대형 DB 파일 내부의 1MB 수정 시 파일 전체가 재저장되는 비효율**이 존재합니다.
   - *[로드맵]*: 향후 v3.x에서 일반 파일의 안정성을 유지하면서 대용량 파일에만 한정하여 청크 단위로 쪼개는 **선택적 Large-File Chunking(CDC)** 도입을 검토 중입니다.
2. **Windows 전용(Non-POSIX)**:
   - 윈도우 커널(VSS, Win32 API, wbadmin)에 깊게 융합되어 있어 Linux 및 macOS 서버는 지원하지 않습니다.
3. **로컬/사내망 중심 설계**:
   - AWS S3, Backblaze B2 등 퍼블릭 클라우드 오브젝트 스토리지 직접 연동 드라이버는 내장되어 있지 않으며, 로컬 디렉터리, 사내 NAS(UNC), Tailscale P2P 환경에 최적화되어 있습니다.

---

## 📊 6. 실측 벤치마크 데이터 (Empirical Benchmarks)

데스크탑(라이젠 7 9800X3D, `F:\` 22만 개 파일) 실운영 환경에서 계측된 데이터입니다.

| 측정 항목 | 측정 시나리오 | 기존 방식 | BackupSystem v2.10.x | 성능 개선도 |
|:---|:---|:---:|:---:|:---:|
| **스냅샷 목록 조회 지연** | 22만 개 파일 환경 `/api/snapshots` | 2,947.52 ms | **11.46 ms** | **약 257배 단축 (99.6%)** |
| **메타데이터 캐시 히트** | `SnapshotMetadataCache` 내부 조회 | - | **0.077 ms** | **실시간 O(1) 수준** |
| **파일 복원 무결성** | 스냅샷 복원 파일 SHA-256 비교 | - | **100% 비트 일치** | **무결성 입증 (Zero-Drift)** |
| **외부 변동 탐지 지연** | 디렉터리 mtime + 파일 개수 지문 | 수천 ms | **0.05 ms** | **초고속 안전망 작동** |

---

## 🚀 7. 빠른 시작 (Quick Start)

### 7.1. 대시보드 무창 실행 (권장)
바탕화면의 바로가기를 클릭하거나 다음 VBS 런처를 실행합니다:
```cmd
wscript.exe launch_dashboard.vbs
```
- 콘솔 검은 창 깜빡임(Ghost Window) 없이 백그라운드에서 조용히 실행되며, 웹 브라우저(`http://127.0.0.1:8765`)가 자동으로 열립니다.

### 7.2. CLI 기본 명령어
```bash
# 기본 프로필 백업 즉시 실행
python cli.py backup

# 스냅샷 목록 조회
python cli.py list-snapshots

# 특정 시점으로 복원
python cli.py restore --snapshot-id snap_20261001_xxxx --target "C:\Restored"

# 저장소 무결성 검증
python disaster_recovery.py --audit --repo "D:\MyBackup_Repository"
```

---

## 📁 8. 프로젝트 구조 (Structure)

```text
백업시스템/
├── core/                         # 백업 코어 엔진
│   ├── snapshot.py               # 스냅샷 생성 & 병렬 VSS 파일 스캐너
│   ├── snapshot_cache.py         # 11ms 초저지연 메타데이터 캐시 (v2.10.0)
│   ├── restore.py                # CAS 블롭 복원 및 SHA-256 무결성 검증
│   ├── system_image.py           # Windows Native BMR (wbadmin -allCritical)
│   ├── storage.py                # Zstandard 압축 블롭 저장소 & WORM 보호
│   ├── scheduler.py              # 백그라운드 자동 백업 & Deep-Scan 스케줄러
│   ├── replication_queue.py      # SQLite Durable Queue 네트워크 복원력
│   └── updater.py                # Ed25519 서명 기반 GitHub Releases OTA
│
├── web/                          # 모던 웹 GUI 대시보드
│   ├── app.py                    # FastAPI 비동기 백엔드 API
│   ├── static/                   # 다크 테마 UI 정적 자원
│   └── templates/index.html      # 반응형 통합 대시보드 뷰어
│
├── tools/                        # 빌드, 릴리즈, 패키징 자동화
│   └── release.py                # 버전 범프, Ed25519 서명, 배포 전자동화
│
├── disaster_recovery.py          # 단일 파일 무설치 독립형 비상 복구 CLI
├── run.py                        # 프로세스 격리 및 브라우저 오케스트레이터
├── launch_dashboard.vbs          # 무창(SW_HIDE) 백그라운드 스마트 런처
├── requirements.txt              # 최소 의존성 목록
└── VERSION                       # 시맨틱 버전 식별자
```

---

## 📄 라이선스 (License)
본 프로젝트는 사내 내부 시스템 및 지정된 환경에서 안전하게 데이터를 보호하기 위해 개발되었습니다.
