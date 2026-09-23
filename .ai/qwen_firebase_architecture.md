# 백업시스템 Firebase Firestore 실시간 연동 아키텍처

## 1. 개요
- **기존 사내 Firebase 프로젝트**: `sunhang-772e5` (API 키: `AIzaSyCe21skNfRno3PPo-xRYCqfwh3jtboo7Ls`)
- **목적**: 미니PC(`100.72.224.71`) 및 데스크탑(`100.90.20.59`)에서 백업 이벤트(스냅샷 완료, 상태 변경, 디스크 잔량 등) 발생 시 Firebase Firestore에 자동 업로드하고, 백업 전용 대시보드(`web/templates/index.html`)가 실시간(`onSnapshot`)으로 감지하여 양쪽 기기의 백업 상태를 즉시 인식/시각화.

## 2. 데이터 모델 (`backup_devices` / `backup_status`)
- 문서 ID: 디바이스 식별자 (예: `minipc` / `desktop` 또는 호스트명/IP)
- 필드 구성:
  - `device_id`: "minipc" | "desktop"
  - `device_name`: "미니피씨 (100.72.224.71)" | "데스크탑 (100.90.20.59)"
  - `last_backup_time`: ISO 8601 일시
  - `last_status`: "success" | "running" | "failed"
  - `last_snapshot_id`: "snap_YYYYMMDD_HHMMSS_xxxxxx"
  - `total_snapshots`: 총 스냅샷 개수
  - `used_storage_mb`: 저장소 사용량
  - `free_disk_gb`: 디스크 잔여 용량
  - `auto_backup_enabled`: boolean (미니PC: true, 데스크탑: false)
  - `updated_at`: Firestore ServerTimestamp

## 3. 업로드 파이프라인 (백업시스템 엔진 -> Firestore)
- `core/firebase_sync.py`: 외부 무거운 라이브러리 의존성 없이 `urllib.request` 기반 Firestore REST API 활용
- 트리거 시점:
  1. 백업 완료 시 (`_background_backup_task`, `_background_custom_backup_task`, CLI, 스케줄러)
  2. 백업 서버 부팅 시 (`@app.on_event("startup")`)
  3. 대시보드에서 수동 [동기화] 또는 상태 갱신 요청 시

## 4. 백업 전용 대시보드 연동 (`web/templates/index.html`, `static/app.js`)
- Firebase Compat SDK 스크립트 로드
- `db.collection("backup_devices").onSnapshot(...)` 실시간 리스너 구독
- 대시보드 상단/상태 영역에 **Firebase 클라우드 연동 뱃지** 및 **멀티 디바이스(미니PC/데스크탑) 백업 통합 현황 카드** 표출

## 5. 보안 규칙 (`firestore.rules`)
```rules
match /backup_devices/{deviceId} {
  allow read, write: if true;
}
```
