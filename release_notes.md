# CAS BackupSystem 릴리즈 노트

## [v2.9.22] - 2026-10-01 (DEF-03 종결 정식 패치 릴리즈)

### 🚀 결함 해결 (Resolved Defect)
- **[DEF-03] 바탕화면 바로가기 Cold-Start 연결 거부 결함 완전 해결 (`Self-Gated Browser Launch`)**:
  - `launch_dashboard.vbs`: 임의 3초 대기 루프 및 VBScript 내부 브라우저 강제 호출 제거. 백그라운드 서버 깨우기만 수행하고 0.01초 만에 즉시 종료.
  - `run.py`: Uvicorn/FastAPI 서버 소켓이 8765 포트에 BIND & LISTEN 된 것을 자체적으로 확인한 바로 그 순간에만 `open_browser(8765)`를 직접 호출하도록 상태 전이 재설계.
  - 브라우저 오픈과 서버 준비 간의 레이스 컨디션을 원천 차단하여 `127.0.0.1:8765` 연결 거부(`ERR_CONNECTION_REFUSED`) 발생 가능성 0% 달성.
  - 8대 검증 시나리오(콜드스타트, 빠른 연타, 지연 부팅, 2차 실행 인스턴스, `--silent` 부팅, 부팅 실패 다이얼로그 등) 전수 통과.

---

## [v2.9.21] - 2026-09-30 (DEF-02 패치 릴리즈)

### 🚀 결함 해결 (Resolved Defect)
- **[DEF-02] 재부팅 시 백업시스템 웹 대시보드 창 2개 중복 팝업 결함 완전 해결**:
  - 구버전 Inno Setup 및 작업 스케줄러 중복 실행 방지
  - Windows Named Mutex 기반 단일 인스턴스 보호 도입
  - 부팅 자동시작 시 `--silent` 모드 적용
