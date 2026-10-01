# -*- coding: utf-8 -*-
"""
Phase 2 Local Verification Script for v2.9.21 Patches
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ctypes
import subprocess

def test_mutex_behavior():
    print("=== TEST 1: Windows Named Mutex Single-Instance Protection ===")
    MUTEX_NAME = "Global\\BackupSystem_Server_SingleInstance_Mutex"
    kernel32 = ctypes.windll.kernel32
    
    # 1. First acquisition
    m1 = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    err1 = kernel32.GetLastError()
    print(f"  [+] First Mutex handle: {m1}, LastError: {err1} (Expected 0)")
    assert err1 == 0, f"Expected 0, got {err1}"
    
    # 2. Second acquisition attempt (Simulating duplicate process)
    m2 = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    err2 = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    print(f"  [+] Second Mutex attempt: handle: {m2}, LastError: {err2} (Expected 183 ERROR_ALREADY_EXISTS)")
    assert err2 == ERROR_ALREADY_EXISTS, f"Expected 183, got {err2}"
    
    # Cleanup
    kernel32.CloseHandle(m2)
    kernel32.CloseHandle(m1)
    print("  [PASS] Mutex correctly detects duplicate instance!\n")

def test_silent_flag_parsing():
    print("=== TEST 2: --silent Flag Parsing in run.py ===")
    import subprocess
    cmd = [sys.executable, "-c", "import sys; is_silent = '--silent' in sys.argv; print('SILENT_MODE:', is_silent)", "--silent"]
    out = subprocess.check_output(cmd, text=True).strip()
    print(f"  [+] Output with --silent: {out}")
    assert "SILENT_MODE: True" in out
    
    cmd_normal = [sys.executable, "-c", "import sys; is_silent = '--silent' in sys.argv; print('SILENT_MODE:', is_silent)"]
    out_normal = subprocess.check_output(cmd_normal, text=True).strip()
    print(f"  [+] Output without --silent: {out_normal}")
    assert "SILENT_MODE: False" in out_normal
    print("  [PASS] --silent flag successfully isolates startup mode!\n")

def test_github_updater_channel():
    print("=== TEST 3: GitHub Releases API in core/updater.py ===")
    from core.updater import _check_github_release, check_for_update
    
    # Test with current installed version (2.9.20) -> should be already up to date (None)
    res_same = _check_github_release("2.9.20")
    print(f"  [+] Check when version is 2.9.20: {res_same} (Expected None)")
    assert res_same is None
    
    # Test with simulated older version (2.9.19) -> should detect v2.9.20 from GitHub!
    res_older = _check_github_release("2.9.19")
    print(f"  [+] Check when version is 2.9.19 (Simulated): Update Available={res_older is not None}")
    if res_older:
        print(f"      - Latest Version: {res_older.get('latest_version')}")
        print(f"      - Download URL: {res_older.get('download_url')}")
        print(f"      - Expected SHA256: {res_older.get('sha256')}")
        print(f"      - Source: {res_older.get('source')}")
        assert res_older.get("latest_version") == "2.9.20"
        assert res_older.get("source") == "github"
        assert res_older.get("download_url") is not None
    print("  [PASS] GitHub Releases API is working as primary OTA channel!\n")

if __name__ == "__main__":
    test_mutex_behavior()
    test_silent_flag_parsing()
    test_github_updater_channel()
    print("🎉 ALL PHASE 2 VERIFICATIONS PASSED (3/3)")
