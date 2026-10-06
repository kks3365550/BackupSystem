# -*- coding: utf-8 -*-
"""
tests/test_offsite.py - 오프사이트 복제 엔진 회귀 테스트

검증 대상 (실측에서 발견한 함정 포함):
  1. robocopy 요약 출력 파싱 - 로케일 한글 라벨("파일") 대응
  2. 인코딩 함정: encoding="utf-8" 지정 시 cp949 출력이 깨져 파싱이 전부 0이 됨
  3. 사전 점검 - 원격 미도달 시 스킵(백업 결과에 영향 없음)
  4. 증분 복제 - 이미 복제된 파일은 건너뜀
"""

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.offsite import OffsiteReplicator


class TestOffsiteParsing(unittest.TestCase):
    """robocopy 출력 파싱 회귀 테스트"""

    def test_parse_korean_locale_summary(self):
        """한글 로케일 요약 블록 파싱 (실측 형식)"""
        out = (
            "                  전체       복사됨      건너뜀     불일치       실패        추가\n"
            "    디렉터리 :         2         2         0         0         0         0\n"
            "      파일 :         3         3         0         0         0         0\n"
            "     바이트 :       300       300         0         0         0         0\n"
        )
        r = OffsiteReplicator._parse_robocopy_output(out)
        self.assertEqual(r["files_total"], 3)
        self.assertEqual(r["files_copied"], 3)
        self.assertEqual(r["files_failed"], 0)

    def test_parse_english_locale_summary(self):
        """영문 로케일 요약 블록 파싱"""
        out = (
            "               Total    Copied   Skipped  Mismatch    FAILED    Extras\n"
            "    Dirs :         2         2         0         0         0         0\n"
            "   Files :     84192     47642     36550         0         0         0\n"
            "   Bytes :  9.939 g   5.343 g   4.596 g         0         0         0\n"
        )
        r = OffsiteReplicator._parse_robocopy_output(out)
        self.assertEqual(r["files_total"], 84192)
        self.assertEqual(r["files_copied"], 47642)
        self.assertEqual(r["files_failed"], 0)

    def test_parse_ignores_filter_line(self):
        """'파일 : *.*' 필터 설정 줄을 Files 행으로 오인하지 않아야 한다"""
        out = (
            "        파일 : *.*\n"
            "      파일 :         3         3         0         0         0         0\n"
        )
        r = OffsiteReplicator._parse_robocopy_output(out)
        self.assertEqual(r["files_total"], 3, "필터 줄(*.*)을 오인했다")

    def test_parse_empty_output(self):
        """빈 출력이면 예외 없이 0 반환"""
        r = OffsiteReplicator._parse_robocopy_output("")
        self.assertEqual(r["files_total"], 0)
        self.assertEqual(r["files_copied"], 0)
        self.assertEqual(r["files_failed"], 0)

    def test_parse_with_thousands_separator(self):
        """쉼표 구분 숫자 파싱"""
        out = (
            "   Files : 84,192 47,642 36,550 0 0 0\n"
        )
        r = OffsiteReplicator._parse_robocopy_output(out)
        self.assertEqual(r["files_total"], 84192)
        self.assertEqual(r["files_copied"], 47642)


class TestOffsiteReplication(unittest.TestCase):
    """실제 robocopy 실행 회귀 테스트"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="offsite_test_")
        self.src = os.path.join(self.tmp, "src")
        self.dst = os.path.join(self.tmp, "dst")
        os.makedirs(os.path.join(self.src, "blobs", "aa"), exist_ok=True)
        for i in range(3):
            with open(os.path.join(self.src, "blobs", "aa", "b%d.blob" % i), "wb") as f:
                f.write(b"x" * 100)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_first_run_copies_all(self):
        """1회차: 신규 파일 모두 복제"""
        res = OffsiteReplicator(self.src, self.dst, timeout_sec=60).replicate()
        self.assertTrue(res["success"], res["reason"])
        self.assertEqual(res["files_total"], 3)
        self.assertEqual(res["files_copied"], 3)
        self.assertEqual(res["files_failed"], 0)

    def test_incremental_skips_existing(self):
        """2회차: 변경 없으면 복제 0건 (인코딩 버그 시 3으로 회귀)"""
        OffsiteReplicator(self.src, self.dst, timeout_sec=60).replicate()
        res = OffsiteReplicator(self.src, self.dst, timeout_sec=60).replicate()
        self.assertTrue(res["success"])
        self.assertEqual(res["files_copied"], 0,
                         "files_copied=0이어야 한다 (인코딩/파싱 회귀 suspicion)")

    def test_incremental_copies_only_new(self):
        """3회차: 신규 1개만 복제"""
        OffsiteReplicator(self.src, self.dst, timeout_sec=60).replicate()
        with open(os.path.join(self.src, "blobs", "aa", "new.blob"), "wb") as f:
            f.write(b"y" * 100)
        res = OffsiteReplicator(self.src, self.dst, timeout_sec=60).replicate()
        self.assertTrue(res["success"])
        self.assertEqual(res["files_total"], 4)
        self.assertEqual(res["files_copied"], 1)

    def test_preflight_local_missing(self):
        """로컬 저장소 없으면 스킵(실패 아님)"""
        rep = OffsiteReplicator(os.path.join(self.tmp, "nope"), self.dst)
        pf = rep.preflight()
        self.assertFalse(pf["ok"])
        self.assertIn("로컬 저장소", pf["reason"])

    def test_preflight_unc_detection(self):
        """UNC 경로 인식 여부"""
        rep = OffsiteReplicator(self.src, r"\\server\share\repo")
        pf = rep.preflight()
        self.assertTrue(pf["is_unc"], "UNC 경로로 인식되어야 한다")
        # 도달 불가하므로 ok는 False
        self.assertFalse(pf["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
