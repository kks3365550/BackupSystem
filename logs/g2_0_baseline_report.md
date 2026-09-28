# G2-0 저장소 및 메타데이터 정상 기준선(Baseline) 리포트

- **측정 시각**: `2026-09-28T13:06:57.411211`
- **타겟 저장소**: `D:\MyBackup_Repository`
- **종합 상태**: **PASS** (DB 건전성: True, 복원 검증: True)

---

## 1. Snapshot 현황
- **총 Snapshot 개수**: `3개`
- **최신 Snapshot**: `snap_20260928_122622_7d1849.json`
  - 파일 수: `75397개`
  - 총 용량: `19.89 GB`
  - SHA-256: `d2260c9cd405f8f5bde00431dd6a8b8c23bad9500b4ac87711c71a039852508c`

## 2. CAS Blob 저장소 현황
- **총 CAS Blob 수**: `50354개`
- **총 Blob 용량**: `8.62 GB` (`9,250,555,498 바이트`)

## 3. metadata.db 무결성
- **DB 크기**: `104.00 KB`
- **PRAGMA integrity_check**: `ok`
- **PRAGMA quick_check**: `ok`
- **테이블별 레코드 수**:
  - `blobs_summary`: 1건
  - `snapshots_meta`: 3건

## 4. 최신 Snapshot 복원(Restore) & SHA-256 대조 검증
- **테스트 Snapshot**: `snap_20260928_122622_7d1849`
- **복원 소요 시간**: `2.17초`
- **검증 파일 수**: `100개`
- **SHA-256 일치 수**: `100개`
- **불일치 / 누락**: `0개 / 0개`
- **일치율**: **`100.0%`** (완전 일치: True)

---
이 리포트는 이후 진행될 G2-1(Interrupted Write), G2-2(Process Kill), G2-3(DB Corruption), G2-4(Power Loss Simulation), G2-5(Concurrency/Lock) 테스트의 절대적 비교 기준선으로 사용됩니다.
