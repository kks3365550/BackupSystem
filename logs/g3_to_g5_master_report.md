# 백업시스템 v2.9.18 RC 마스터 검증 및 종합 릴리즈 판정 리포트 (G3 ~ G5)
- **검증 시각**: `2026-09-29T12:11:52.128440`
- **검증 대상 버전**: `v2.9.18`
- **차기 패치 버전**: `v2.9.19` (DEF-01 해결 반영)
- **검증 모드**: 원샷 마스터 파이프라인 (`tools/run_g3_to_g5_master.py`)
- **검증 환경**: 내 미니피씨 (`100.72.224.71`, Windows 11), Sandbox (`D:\G3_Master_Sandbox_Repo`)
- **수행 원칙**: 마스터 검증 완료 시까지 코어 코드 동결 유지 후 검증 종료 단계에서 DEF-01 패치 적용 및 회귀

---

## 1. 단계별 검증 결과 종합 매트릭스

| 단계 | 검증 영역 | 시나리오 수 | 성공 | 실패 | 종합 판정 |
|:---:|:---|:---:|:---:|:---:|:---:|
| **G1** | Windows 실환경 3대 검증 (Defender, Scheduler, VSS, 3단계 Uninstall) | 3 | 3 | 0 | ✅ **PASS** |
| **G2** | 내구성 & 자가치유 (Interrupted Write, Kill, Corruption, Concurrency) | 6 | 6 | 0 | ✅ **PASS** |
| **G3-1** | In-Place Full DR & 동일 상대경로(Collision) 원위치 격리 복원 | 4 | 4 | 0 | ✅ **PASS** |
| **G3-2** | Granular Selected Paths Restore (9대 세부 선택 시나리오) | 9 | 9 | 0 | ✅ **PASS (DEF-01 패치 후 회귀 완료)** |
| **G3-3** | Restore Safety & Boundary (상대/절대경로 탈출 차단, 독점 락, 읽기전용) | 4 | 4 | 0 | ✅ **PASS** |
| **G3-4** | Multi-Source Complex Collision (4개 소스 교차 충돌 & 선별 복구) | 3 | 3 | 0 | ✅ **PASS** |
| **G3-5** | Large Baseline (7.5만 메타데이터 전수 검증 + 5,000개 파일 벤치) | 3 | 3 | 0 | ✅ **PASS** |
| **G3-6** | Interrupted Kill & Resume (SIGKILL 사살 후 DB 무결성 & 100% 재개) | 2 | 2 | 0 | ✅ **PASS** |
| **G4** | Real Disaster Recovery (단일파일/랜섬웨어/디렉터리/전체증발 4종 DR) | 4 | 4 | 0 | ✅ **PASS** |

---

## 2. G3-3 ~ G4 세부 실행 결과 내역

### G3-3 검증 결과
| No | 테스트 항목 | 실측 판정 | 상세 실측 지표 |
|:---:|:---|:---:|:---|
| 1 | **G3-3.1 Path Traversal (in_place=False)** | ✅ PASS | Blocked: True, Outside Leaks: False, Normal Restored: True |
| 2 | **G3-3.2 Path Traversal (in_place=True)** | ✅ PASS | Blocked: True, Outside Leaks: False, Legit Restored: True |
| 3 | **G3-3.3 File-in-Use Lock Tolerance** | ✅ PASS | Restored: 4/4, Failed: 1/1, Locked Isolated: True |
| 4 | **G3-3.4 Read-Only Target Auto-Unlock & Overwrite** | ✅ PASS | Restored: 5/5, Overwritten: True |

### G3-4 검증 결과
| No | 테스트 항목 | 실측 판정 | 상세 실측 지표 |
|:---:|:---|:---:|:---|
| 1 | **G3-4.1 Full In-Place DR (4 Sources)** | ✅ PASS | Restored: 8/8, SHA Match: True, Collision Isolated: True |
| 2 | **G3-4.2 Selective In-Place DR (Colliding Path)** | ✅ PASS | Restored: 4/4, SHA Match: True, Selective Ok: True |
| 3 | **G3-4.3 Flat Extraction Contrast (Known Behavior)** | ✅ PASS | Flat Files: 5/5, Flattened shared/config.json: True |

### G3-5 검증 결과
| No | 테스트 항목 | 실측 판정 | 상세 실측 지표 |
|:---:|:---|:---:|:---|
| 1 | **G3-5.1 Metadata Integrity Full Scan** | ✅ PASS | Entries: 75724, source_root Rate: 100.0%, Protected Error Files: 62, Blob Existence: 100.0% |
| 2 | **G3-5.2 Disk Space Safety Guard** | ✅ PASS | Free Space: 593.63 GB (Threshold: > 20.0 GB) |
| 3 | **G3-5.3 5,000 Files Restore Stress Benchmark** | ✅ PASS | Restored: 5000/5000 (50.0s, 100.1 files/s, 163.1 MB/s), Sample SHA: 50/50 |

### G3-6 검증 결과
| No | 테스트 항목 | 실측 판정 | 상세 실측 지표 |
|:---:|:---|:---:|:---|
| 1 | **G3-6.1 Repository Integrity Post-Kill** | ✅ PASS | SQLite PRAGMA integrity_check: True |
| 2 | **G3-6.2 Resume Completion & Bitwise Integrity** | ✅ PASS | Final Files: 300/300, 100% SHA Match: True, Resume Time: 1.01s |

### G4 검증 결과
| No | 테스트 항목 | 실측 판정 | 상세 실측 지표 |
|:---:|:---|:---:|:---|
| 1 | **G4.1 Single Critical File Recovery** | ✅ PASS | DB File Recovered: True, SHA Bitwise Match: True |
| 2 | **G4.2 Ransomware / Corruption In-Place Repair** | ✅ PASS | Corrupted Files Repaired: True, Restored Files: 20/20 |
| 3 | **G4.3 Entire Directory Subtree DR Recovery** | ✅ PASS | Subtree Fully Rebuilt: True, Restored Files: 20/20 |
| 4 | **G4.4 Catastrophic Total Loss Full DR Recovery** | ✅ PASS | DB Ok: True, Cfg Ok: True, Docs Ok: True, Total Restored: 22/22 |

---

## 3. 공식 결함 대장 (Defect Ledger)

| 결함 ID | 분류 등급 | 대상 파일 (라인) | 요약 | 조치 상태 |
|:---:|:---:|:---:|:---|:---:|
| **DEF-01** | `Class B (Restore Correctness)` | `core/restore.py` (L49) | selected_rel_paths=[] 전달 시 Falsy 평가로 인한 스냅샷 전체 복원 | 🟢 **패치 완료 & G3-2 회귀 통과** |

### 🔍 [DEF-01] selected_rel_paths=[] 전달 시 Falsy 평가로 인한 스냅샷 전체 복원
- **결함 분류**: `Class B (Restore Correctness)`
- **위치**: `core/restore.py` L49
- **원인 분석**: `if selected_rel_paths:` 구문에서 빈 리스트(`[]`)가 False로 평가되어 `else`(`to_restore = entries`)로 빠짐
- **영향**: 체크박스 0개 선택 시 아무것도 복원되지 않아야 하나 전체 스냅샷이 복원됨
- **조치 결과**: `if selected_rel_paths is not None:`으로 원포인트 수정 완료. `tools/test_g3_2_selected_restore.py` 9대 시나리오 회귀 결과 `[]` -> 0개 복원, `None` -> 전체 복원 정상 분리 검증 완료.

---

## 4. 최종 릴리즈 Triage 판정 및 상태 (Final Release Verdict & Status)

- **검증 대상 버전**: **`v2.9.18`**
- **Class A (치명적 안전성/탈출/데이터파괴 결함)**: **`0` 건**
- **Class B (기능 정확성 결함)**: **`1` 건** (`DEF-01`: 빈 리스트 전달 시 전체 복원 버그 ➡️ **패치 및 회귀 검증 완료**)
- **Class C (운영성/예외 핸들링)**: **`0` 건**
- **Class D (표기/사소한 UI 개선)**: **`0` 건**

### 🎯 종합 판정: **DEF-01 패치 적용 완료 및 회귀 검증 통과 (v2.9.19 릴리스 준비 완료)**

1. **안전성 및 DR 복구 검증 요약**:
   - G4에서 정의한 4개 DR 시나리오를 모두 통과했으며, 해당 테스트 조건에서 Class A 데이터 안전성 결함은 발견되지 않았습니다.
   - Path Traversal 차단, 멀티소스 4개 루트 분리 복구, 대용량 7.5만 개 메타데이터 무결성, 5,000개 파일 벤치마크(100.1 files/s, 163.1 MB/s), 프로세스 강제 종료(`taskkill /F`) 후 재개 무결성이 모두 정상 검증되었습니다.
2. **DEF-01 원포인트 패치 및 회귀 결과**:
   - `core/restore.py` L49를 `if selected_rel_paths is not None:`으로 수정 완료.
   - `tools/test_g3_2_selected_restore.py` 9대 시나리오 재실행 결과:
     - `selected_rel_paths = None`: 스냅샷 전체 복원 (9/9개) ✅ PASS
     - `selected_rel_paths = []`: 복원 대상 0개 (0개 복원) ✅ PASS
     - 단일/복수 파일, 디렉터리 subtree, 깊은 경로, 대소문자 무시, 부존재 경로, 멀티소스 격리 등 나머지 7개 시나리오 전수 회귀 ✅ PASS
3. **현재 상태 및 다음 절차**:
   - 현재 코드는 DEF-01 수정 및 단위/통합 회귀 검증을 마친 상태로, 사용자의 최종 승인 시 `python tools/release.py --bump patch -m "fix(restore): resolve DEF-01 empty selected_rel_paths restore bug"`를 가동하여 **v2.9.19 정식 배포**를 완결할 준비가 완료되었습니다.
