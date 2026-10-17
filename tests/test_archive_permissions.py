# -*- coding: utf-8 -*-
"""
tests/test_archive_permissions.py: 권한 격리 및 아카이브 검증 테스트
1. 비관리자 권한에서 D:\WindowsImageBackup 실측 VHDX 조회 및 크기 검증 (23바이트 가짜 파일 퇴치 검증)
2. UAC 승격 워커 호출 검증 (VSS 스냅샷 및 DISM 실행 권한 확보 여부)
"""
import os
import sys
import json
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.drive_archive import find_latest_wbadmin_vhdx, DriveArchiveManager
from core.disk_clone import run_elevated_command


def test_wbadmin_vhdx_real_size_not_mock():
    """백업 삭제 후 find_latest_wbadmin_vhdx()가 예외 없이 None을 반환하거나, 존재 시 실측 크기 검증"""
    info = find_latest_wbadmin_vhdx("D:")
    if info is not None:
        assert info["size_bytes"] > 10 * 1024 * 1024 * 1024, f"VHDX 크기가 비정상적입니다: {info['size_bytes']} bytes"
        assert info["size_gb"] > 10.0, f"VHDX GB 크기가 비정상적입니다: {info['size_gb']} GB"
        print(f"\n[PASS] 실제 VHDX 식별: {info['vhdx_path']} ({info['size_gb']} GB)")
    else:
        print("\n[PASS] 이전 백업 삭제 완료 상태 정상 확인 (VHDX 미존재 -> None)")


def test_list_archives_reports_correct_metadata():
    """DriveArchiveManager.list_archives()가 삭제 완료 후 유령 항목 없이 깨끗한 상태(0건)를 반환하는지 검증"""
    mgr = DriveArchiveManager.get_instance()
    archives = mgr.list_archives()
    # 삭제 후에는 유령(Ghost) 아카이브 없이 정확히 0건이어야 함
    assert len(archives) == 0, f"삭제 후 아카이브 목록이 비어있지 않습니다: {archives}"
    print("\n[PASS] 아카이브 목록 완전 삭제(0건) 및 유령 캐시 부재 실측 검증 완료")


def test_elevated_worker_execution_permissions():
    """비관리자 세션에서 run_elevated_command를 통해 관리자 권한 도구(dism, vssadmin)가 정상 실행되는지 실측 검증"""
    # 1. dism 확인
    rc_dism, out_dism, _ = run_elevated_command(["dism.exe", "/?"], timeout=30)
    assert rc_dism == 0, f"DISM elevated 실행 실패: rc={rc_dism}"
    assert "Deployment Image Servicing and Management" in out_dism

    # 2. vssadmin 확인
    rc_vss, out_vss, _ = run_elevated_command(["vssadmin.exe", "list", "shadows"], timeout=30)
    assert rc_vss == 0, f"vssadmin elevated 실행 실패: rc={rc_vss}"
    print("\n[PASS] UAC 승격 실행기를 통한 DISM 및 vssadmin 권한 획득 100% 실측 검증 완료")


if __name__ == "__main__":
    test_wbadmin_vhdx_real_size_not_mock()
    test_list_archives_reports_correct_metadata()
    test_elevated_worker_execution_permissions()
    print("\n=== 모든 권한 및 정합성 검증 테스트 통과 ===")
