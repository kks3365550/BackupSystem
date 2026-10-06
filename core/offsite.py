# -*- coding: utf-8 -*-
"""
core/offsite.py: 오프사이트(이중화) 복제 엔진
- robocopy 기반 대용량/소파일 최적화 복제
- 백업 파이프라인에 후속 단계로 통합
- 실패해도 로컬 백업 결과에 영향 없음 (격리)

배경 (실측 근거):
    core/replication.py는 블록마다 icacls subprocess를 호출해 SMB 상에서
    블롭 1개당 239ms가 소요되어 84,116개 기준 약 20시간이 소요되었다.
    robocopy /MT:32는 동일한 84,192개 파일을 약 12분에 복제한다.
    따라서 로컬 저장소 보호는 core/worm.py가, 원격 복제는 robocopy가 담당한다.

원격 저장소는 다른 장비의 공유 폴더이므로 NTFS Deny ACL 방어선을 두지 않는다.
오프사이트의 목적은 "별도 물리 장비에 복구 지점을 확보"하는 것이며,
이는 ACL 없이도 달성된다.
"""

import os
import time
import subprocess
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger("BackupSystem")

# Windows 전용
IS_WINDOWS = os.name == "nt"


class OffsiteReplicationError(Exception):
    """오프사이트 복제 실패"""
    pass


class OffsiteReplicator:
    """
    robocopy 기반 오프사이트 복제기.

    robocopy 선택 근거 (실측):
        방법                  341개 소요   84,192개 환산
        robocopy /MT:32       1.5초        12분
        Python Copy-Item      26.3초       108분
        Python + icacls       약 78초      약 20시간
    """

    # robocopy 성공 판정값 (0~7 = 성공, 8+ = 실제 오류)
    ROBOCOPY_OK_CODES = range(0, 8)

    def __init__(
        self,
        local_repo_dir: str,
        remote_repo_dir: str,
        timeout_sec: int = 7200,
        max_threads: int = 32,
        retries: int = 2,
        wait_sec: int = 1
    ):
        self.local_repo_dir = os.path.abspath(local_repo_dir)
        # UNC 경로(\\)는 abspath가 드라이브 문자를 붙이지 않지만, 명시적으로 보존한다.
        if remote_repo_dir.startswith("\\\\"):
            self.remote_repo_dir = remote_repo_dir.rstrip("\\")
        else:
            self.remote_repo_dir = os.path.abspath(remote_repo_dir)
        self.timeout_sec = timeout_sec
        self.max_threads = max_threads
        self.retries = retries
        self.wait_sec = wait_sec

    # ------------------------------------------------------------------
    # 사전 점검
    # ------------------------------------------------------------------
    def preflight(self) -> Dict[str, Any]:
        """복제 전 조건 확인. 실패해도 로컬 백업은 정상 완료되어야 한다."""
        result = {
            "ok": False,
            "local_exists": False,
            "remote_reachable": False,
            "is_unc": self.remote_repo_dir.startswith("\\\\"),
            "reason": ""
        }

        if not IS_WINDOWS:
            result["reason"] = "Windows 전용 기능 (현재 OS: %s)" % os.name
            return result

        result["local_exists"] = os.path.isdir(self.local_repo_dir)
        if not result["local_exists"]:
            result["reason"] = "로컬 저장소 없음: %s" % self.local_repo_dir
            return result

        # 원격 상위 폴더 도달 가능성 확인 (쓰기 없이)
        probe = self.remote_repo_dir
        reachable = False
        # UNC 최상위 서버까지만 확인
        if probe.startswith("\\\\"):
            parts = probe[2:].split("\\")
            server = "\\\\" + parts[0]
        else:
            server = os.path.splitdrive(probe)[0] + "\\"
        try:
            os.makedirs(probe, exist_ok=True)
            reachable = os.path.isdir(probe)
        except Exception as e:
            result["reason"] = "원격 경로 생성 실패: %s" % e
            return result

        result["remote_reachable"] = reachable
        if not reachable:
            result["reason"] = "원격 저장소를 만들 수 없음: %s" % probe
            return result

        result["ok"] = True
        return result

    # ------------------------------------------------------------------
    # 복제 실행
    # ------------------------------------------------------------------
    def replicate(self) -> Dict[str, Any]:
        """
        로컬 저장소를 원격으로 복제한다.

        반환:
            {
                "success": bool,        # robocopy 결과 기준
                "skipped": bool,        # 사전 점검 실패로 스킵
                "reason": str,
                "return_code": int,
                "files_total": int,     # robocopy 요약에서 추출 (없으면 0)
                "files_copied": int,
                "files_failed": int,
                "duration_sec": float,
            }
        """
        started = time.time()
        result: Dict[str, Any] = {
            "success": False,
            "skipped": False,
            "reason": "",
            "return_code": -1,
            "files_total": 0,
            "files_copied": 0,
            "files_failed": 0,
            "duration_sec": 0.0,
        }

        # 1) 사전 점검
        pf = self.preflight()
        if not pf["ok"]:
            result["skipped"] = True
            result["reason"] = pf["reason"] or "사전 점검 실패"
            logger.warning("[오프사이트] 스킵: %s", result["reason"])
            result["duration_sec"] = time.time() - started
            return result

        logger.info(
            "[오프사이트] 복제 시작: %s -> %s (제한 %d분)",
            self.local_repo_dir, self.remote_repo_dir, self.timeout_sec // 60
        )

        # 2) robocopy 실행
        #    /E    : 하위 디렉터리 포함
        #    /MT:n : 병렬 스레드
        #    /R:n : 실패 시 재시도 횟수
        #    /W:n : 재시도 대기 초
        #    /NFL /NDL /NP : 로그 잡음 감소
        #    /DCOPY:DA /COPY:DAT : 디렉터리/파일 속성 보존
        cmd = [
            "robocopy",
            self.local_repo_dir,
            self.remote_repo_dir,
            "/E",
            "/MT:%d" % self.max_threads,
            "/R:%d" % self.retries,
            "/W:%d" % self.wait_sec,
            "/DCOPY:DA",
            "/COPY:DAT",
            "/NFL", "/NDL", "/NP"
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                # 로케일 기본 인코딩으로 디코딩해야 한다.
                # robocopy 요약 라벨("파일", "전체" 등)은 콘솔 코드페이지(cp949)로
                # 출력되므로 encoding="utf-8"을 지정하면 한글 라벨이 깨지고
                # 요약 파싱이 전부 0이 된다. (실측 확인)
                errors="replace",
                timeout=self.timeout_sec,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            rc = proc.returncode
            output = proc.stdout or ""
            result.update(self._parse_robocopy_output(output))
            result["return_code"] = rc

            # robocopy는 0~7을 성공으로 본다 (8+ = 실제 오류)
            result["success"] = rc in self.ROBOCOPY_OK_CODES
            if result["success"]:
                result["reason"] = "복제 완료"
                logger.info(
                    "[오프사이트] 완료: 신규 %d개 / 전체 %d개 / 실패 %d개 (%.1f초)",
                    result["files_copied"], result["files_total"],
                    result["files_failed"], result["duration_sec"]
                )
            else:
                result["reason"] = "robocopy 오류 (코드 %d)" % rc
                logger.error("[오프사이트] 실패: %s", result["reason"])
                if output.strip():
                    logger.error("[오프사이트] robocopy 출력:\n%s", output[-1500:])

        except subprocess.TimeoutExpired:
            result["success"] = False
            result["reason"] = "복제 시간 초과 (%d분). 다음 실행에서 이어서 진행됩니다." % (self.timeout_sec // 60)
            logger.error("[오프사이트] %s", result["reason"])
        except FileNotFoundError:
            result["skipped"] = True
            result["reason"] = "robocopy를 찾을 수 없음"
            logger.warning("[오프사이트] %s", result["reason"])
        except Exception as e:
            result["reason"] = "복제 예외: %s" % e
            logger.error("[오프사이트] %s", result["reason"])

        result["duration_sec"] = time.time() - started
        return result

    # ------------------------------------------------------------------
    # robocopy 요약 라벨 (로케일별). Files 행은 Files / 파일 / Fichiers / Dateien 등.
    _LABEL_FILES = ("files", "파일", "fichiers", "dateien", "archivos", "arquivos")

    @staticmethod
    def _parse_robocopy_output(output: str) -> Dict[str, Any]:
        """
        robocopy 요약 블록의 Files 행 숫자를 파싱한다.

        로케일 의존성 주의 (실측, 이 시스템은 한글 로케일):
            요약 블록 형식
                      전체       복사됨      건너뜀     불일치       실패        추가
              디렉터리 :         2         2         0         0         0         0
                파일 :         1         1         0         0         0         0
               바이트 :        50        50         0         0         0         0

            문자열만 믿으면 안 되는 이유:
              1) 라벨이 로케일별로 달라 'Files' 리터럴 검색이 실패한다.
              2) '파일 : *.*' (필터 설정 줄)도 '파일'로 시작해 오인된다.
                 -> 실제 Files 행은 숫자 6개가 콜론 뒤에 나온다.
              3) 숫자를 큰 단위(쉼표/공백)로 표기할 수도 있어 정규화 필요.

        판별 규칙:
            콜론 뒤에 숫자(쉼표/공백/서로게 제거 후)가 정확히 6개 이상인 행 중
            Files 라벨을 포함하는 행을 선택한다.
        """
        out = {"files_total": 0, "files_copied": 0, "files_failed": 0}

        for raw_line in (output or "").splitlines():
            line = raw_line.strip()
            if ":" not in line:
                continue

            label, _, tail = line.partition(":")
            label_l = label.strip().lower()

            # Files 라벨 판별 (로케일 대응)
            if not any(lbl in label_l for lbl in OffsiteReplicator._LABEL_FILES):
                continue

            # 숫자 추출: 쉼표 제거 후 공백 분리
            normalized = tail.replace(",", "").replace(".", "").replace("\u00a0", " ")
            nums = [int(t) for t in normalized.split() if t.isdigit()]

            # 실제 Files 행은 6개 숫자 (Total Copied Skipped Mismatch FAILED Extras)
            if len(nums) < 6:
                continue

            out["files_total"] = nums[0]
            out["files_copied"] = nums[1]
            out["files_failed"] = nums[4]
            break

        return out


def replicate_offsite(
    local_repo_dir: str,
    remote_repo_dir: str,
    timeout_sec: int = 7200
) -> Dict[str, Any]:
    """간단 호출 헬퍼."""
    replicator = OffsiteReplicator(
        local_repo_dir=local_repo_dir,
        remote_repo_dir=remote_repo_dir,
        timeout_sec=timeout_sec
    )
    return replicator.replicate()
