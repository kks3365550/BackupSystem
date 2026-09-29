# G3-2 Granular Selected Paths Restore 실전 검증 리포트

- **검증 시각**: `2026-09-29T12:24:52.035495`
- **최종 요약**: 총 `9`개 시나리오 중 **PASS: `9`개**, **FAIL: `0`개**
- **검증 대상**: `RestoreEngine.restore_snapshot(..., selected_rel_paths=...)`

---

## 9대 시나리오별 실측 검증 결과 매트릭스

| No | 시나리오 | 입력값 | 기대 요구사항 | 실제 실측 결과 | 판정 | 결함 등급 |
|:---:|:---|:---|:---|:---|:---:|:---:|
| **1** | **Case 1: 단일 파일 선택 복원** | `['file_alpha.txt']` | file_alpha.txt 정확히 1개 복원 | ['file_alpha.txt'] | ✅ **PASS** | `None` |
| **2** | **Case 2: 복수 파일 선택 복원** | `['file_alpha.txt', 'file_beta.txt']` | ['file_alpha.txt', 'file_beta.txt'] | ['file_alpha.txt', 'file_beta.txt'] | ✅ **PASS** | `None` |
| **3** | **Case 3: 디렉터리 subtree 복원 (docs/)** | `['docs']` | docs/ 하위 2개 복원 (docs_backup 제외) | ['docs/manual.pdf', 'docs/sub/guide.txt'] | ✅ **PASS** | `None` |
| **4** | **Case 4: 깊은 디렉터리 경로 (5단계)** | `['l1/l2/l3/l4/l5/deep_target.bin']` | l1/l2/l3/l4/l5/deep_target.bin 정확히 복원 | ['l1/l2/l3/l4/l5/deep_target.bin'] | ✅ **PASS** | `None` |
| **5** | **Case 5: 대소문자 무시 (Case-Insensitive)** | `['CASE_TEST/README.TXT']` | case_test/readme.txt 1개 복원 | ['case_test/readme.txt'] | ✅ **PASS** | `None` |
| **6** | **Case 6: 부존재 경로 선택 (Graceful Skip)** | `['ghost/non_existent.txt']` | 0개 복원, 에러 없음 | 복원 0개, 에러 0개 | ✅ **PASS** | `None` |
| **7** | **Case 7: None 시맨틱 (필터 미지정)** | `None` | 스냅샷 전체 9개 복원 | 9개 복원 | ✅ **PASS** | `None` |
| **8** | **Case 8: 빈 리스트 [] 시맨틱 (0개 선택)** | `[]` | 0개 복원 | 0개 복원 | ✅ **PASS** | `None` |
| **9** | **Case 9: 멀티소스 동일 rel_path 선택 복원** | `['shared/config.json'] (in_place=True)` | Main/Extra 두 소스의 shared/config.json이 각각의 루트로 100% 분리 복원 | Main=True, Extra=True, 해시 일치=True | ✅ **PASS** | `None` |

---

## 🚨 발견된 결함 상세 분석 (Defect Triage)

### 1. [Class B — Restore Correctness] Case 8: 빈 리스트 `[]` 전달 시 전체 복원 버그
- **증상**: 호출자가 `selected_rel_paths=[]` (0개 파일 선택)를 명시적으로 전달했음에도, 스냅샷 내 **모든 파일(100%)이 전체 복원**됨.
- **원인 코드 (`core/restore.py` L49)**:
  ```python
  if selected_rel_paths:  # 빈 리스트([])는 Falsy이므로 else로 진입!
      ...
  else:
      to_restore = entries  # 스냅샷 전체 복원 발생!
  ```
- **영향 범위**:
  - `selected_rel_paths=None` (필터 미지정 ➡️ 전체 복원 의도)
  - `selected_rel_paths=[]` (선택 개수 0개 ➡️ 0개 복원 의도)
  - 두 시맨틱의 구분이 파괴되어, 웹 UI나 API에서 사용자가 체크박스를 전부 해제하고 복원을 시작할 경우 의도치 않게 모든 파일이 복원되는 위험한 동작 유발.
- **권고 수정안**:
  `if selected_rel_paths is not None:`로 변경하여 `None`일 때만 전체 복원으로 진입하고, `[]`일 때는 `to_restore = []`로 유지되어 0개 복원되도록 처리 필요.

---

## 💡 결론 및 조치 권고
- G3-2의 기능적 필터링(단일 파일, 복수 파일, 디렉터리 subtree, 깊은 경로, Windows 대소문자 무시, 부존재 경로, 멀티소스 분리)은 **모두 100% 정상 작동**함을 확인했습니다.
- 단, **Case 8 (`[]` vs `None`) 결함은 사용자가 수립한 기준에 따라 `Class B (Restore Correctness)` 결함으로 공식 적출**되었습니다.
- 사용자 지침에 따라 즉시 버전을 올리지 않고, 본 결함을 **G3 결함 트래커에 기록**한 뒤 G3 전체 단계 완료 후 일괄 패치 여부를 결정하는 것을 권고합니다.
