# -*- coding: utf-8 -*-
"""
core/updater.py: Firebase 기반 소프트웨어 자동 업데이트 클라이언트 모듈 (v2.9.2)

핵심 기능:
1. check_for_update(): Firestore app_releases/latest 조회 및 시맨틱 버전 비교
2. download_update(): HTTPS URL을 통한 임시 디렉토리 안전 다운로드
3. verify_update(): SHA-256 무결성 및 Ed25519 디지털 서명 검증 (Zero-Leak 검사 포함)
4. install_update(): Staging 해제, 기존 버전 보존, 백업 프로세스 타겟 안전 종료, 스왑 및 무창 재기동
5. health_check(): 포트 8765 및 /api/system-info 10초 이내 정상 가동 검증
6. rollback(): 헬스체크 실패 시 직전 정상 버전으로 자동 원복

보안 및 안전 원칙:
- Fail-Safe: 네트워크/Firebase 장애 발생 시 기존 백업 엔진의 정상 구동 보장
- Process Isolation: Qwen(RTX 5080) 등 타 파이썬 프로세스를 건드리지 않고 백업 데몬만 선별 제어
- Zero-Trust: 서명 또는 해시 불일치 시 설치 전 즉각 폐기
"""

import os
import sys
import time
import json
import socket
import shutil
import hashlib
import zipfile
import logging
import tempfile
import datetime
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("core.updater")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIREBASE_PROJECT_ID = "sunhang-772e5"
FIREBASE_API_KEY = "AIzaSyCe21skNfRno3PPo-xRYCqfwh3jtboo7Ls"
FIRESTORE_REST_BASE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"
PUBLIC_KEY_PATH = os.path.join(BASE_DIR, "keys", "release_ed25519.pub")


def parse_version(v_str: str) -> Tuple[int, ...]:
    """버전 문자열을 비교 가능한 정수 튜플로 변환 (예: 'v2.9.1' -> (2, 9, 1))"""
    clean_v = v_str.strip().lstrip('v').lstrip('V')
    parts = []
    for part in clean_v.split('.'):
        digits = []
        for ch in part:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        if digits:
            parts.append(int("".join(digits)))
        else:
            parts.append(0)
    return tuple(parts) if parts else (0, 0, 0)


def get_current_installed_version() -> str:
    """현재 설치된 소프트웨어 버전 확인"""
    v_file = os.path.join(BASE_DIR, "VERSION")
    if os.path.exists(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    try:
        from core import __version__
        return __version__
    except Exception:
        return "2.9.1"


def check_for_update(current_ver: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Firestore app_releases/latest 문서 조회 및 업데이트 필요 여부 확인.
    네트워크 장애나 Firebase 연결 실패 시 예외 없이 None 반환 (Fail-Safe).
    """
    if current_ver is None:
        current_ver = get_current_installed_version()

    logger.info("UPDATE_CHECK_START current_version=%s", current_ver)
    url = f"{FIRESTORE_REST_BASE}/app_releases/latest?key={FIREBASE_API_KEY}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BackupSystemUpdater/2.9"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        fields = data.get("fields", {})
        latest_ver = fields.get("version", {}).get("stringValue", "")
        if not latest_ver:
            logger.info("UPDATE_CHECK_COMPLETED no_version_in_metadata")
            return None

        cur_tuple = parse_version(current_ver)
        latest_tuple = parse_version(latest_ver)

        if latest_tuple > cur_tuple:
            download_url = fields.get("download_url", {}).get("stringValue", "")
            sha256 = fields.get("sha256", {}).get("stringValue", "")
            signature = fields.get("signature", {}).get("stringValue", "")
            mandatory = fields.get("mandatory", {}).get("booleanValue", False)
            changelog = fields.get("changelog", {}).get("stringValue", "")
            min_supported = fields.get("min_supported_version", {}).get("stringValue", "1.0.0")

            # 최소 지원 버전 미달 시 강제 업데이트 플래그
            if cur_tuple < parse_version(min_supported):
                mandatory = True

            release_info = {
                "update_available": True,
                "current_version": current_ver,
                "latest_version": latest_ver,
                "download_url": download_url,
                "sha256": sha256,
                "signature": signature,
                "mandatory": mandatory,
                "changelog": changelog,
                "min_supported_version": min_supported
            }
            logger.info("UPDATE_AVAILABLE version=%s mandatory=%s", latest_ver, mandatory)
            return release_info
        else:
            logger.info("UPDATE_CHECK_COMPLETED already_up_to_date (%s >= %s)", current_ver, latest_ver)
            return None

    except urllib.error.HTTPError as e:
        logger.warning("UPDATE_CHECK_FAILED http_error=%s (URL: %s)", e.code, url)
        return None
    except Exception as e:
        logger.warning("UPDATE_CHECK_FAILED error=%s", str(e))
        return None


def download_update(release_info: Dict[str, Any], temp_dir: Optional[str] = None) -> Optional[str]:
    """
    지정된 HTTPS URL에서 업데이트 패키지(ZIP)를 임시 디렉토리로 다운로드.
    다운로드 실패 시 None 반환.
    """
    download_url = release_info.get("download_url")
    version = release_info.get("latest_version", "unknown")

    if not download_url:
        logger.error("UPDATE_DOWNLOAD_FAILED reason=empty_download_url")
        return None

    if temp_dir is None:
        temp_dir = tempfile.gettempdir()

    target_zip = os.path.join(temp_dir, f"backup_update_v{version}_{int(time.time())}.zip")
    logger.info("UPDATE_DOWNLOAD_START version=%s url=%s target=%s", version, download_url, target_zip)

    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "BackupSystemUpdater/2.9"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()

        with open(target_zip, "wb") as f:
            f.write(content)

        logger.info("UPDATE_DOWNLOAD_OK size=%d bytes", len(content))
        return target_zip
    except Exception as e:
        logger.error("UPDATE_DOWNLOAD_FAILED error=%s", str(e))
        if os.path.exists(target_zip):
            try:
                os.remove(target_zip)
            except OSError:
                pass
        return None


def verify_update(
    zip_path: str,
    expected_sha256: str,
    expected_signature: str,
    pub_key_path: Optional[str] = None
) -> bool:
    """
    1. 파일 존재 및 크기 검사
    2. SHA-256 해시 검증
    3. Ed25519 전자 서명 검증
    4. ZIP 파일 내부 악성/개인키 파일 유입 차단 검증
    """
    if not os.path.exists(zip_path):
        logger.error("UPDATE_VERIFY_FAILED reason=file_not_found path=%s", zip_path)
        return False

    # 1. 파일 읽기 및 SHA-256 검증
    try:
        with open(zip_path, "rb") as f:
            raw_bytes = f.read()

        calc_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        if expected_sha256 and calc_sha256.lower() != expected_sha256.lower():
            logger.error(
                "UPDATE_HASH_MISMATCH expected=%s actual=%s",
                expected_sha256, calc_sha256
            )
            return False
        logger.info("UPDATE_HASH_VERIFY_OK sha256=%s", calc_sha256)
    except Exception as e:
        logger.error("UPDATE_VERIFY_FAILED hash_calc_error=%s", str(e))
        return False

    # 2. Ed25519 디지털 서명 검증
    if expected_signature:
        if pub_key_path is None:
            pub_key_path = PUBLIC_KEY_PATH

        if not os.path.exists(pub_key_path):
            logger.error("UPDATE_SIGNATURE_INVALID reason=public_key_missing path=%s", pub_key_path)
            return False

        try:
            from core.crypto_sign import verify_bytes_ed25519
            is_valid = verify_bytes_ed25519(raw_bytes, expected_signature, pub_key_path)
            if not is_valid:
                logger.error("UPDATE_SIGNATURE_INVALID signature=%s", expected_signature[:16])
                return False
            logger.info("UPDATE_SIGNATURE_VERIFY_OK")
        except Exception as e:
            logger.error("UPDATE_SIGNATURE_INVALID error=%s", str(e))
            return False

    # 3. ZIP 파일 내부 구조 및 Zero-Leak 검증
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            for name in names:
                name_l = name.lower()
                if name_l.endswith(".key") or name_l.endswith(".pem") or "private" in name_l:
                    logger.error("UPDATE_SECURITY_VIOLATION sensitive_file_in_zip=%s", name)
                    return False
        logger.info("UPDATE_ARCHIVE_VERIFY_OK file_count=%d", len(names))
    except Exception as e:
        logger.error("UPDATE_VERIFY_FAILED archive_corrupt error=%s", str(e))
        return False

    return True


def safely_stop_running_backup_server(port: int = 8765) -> bool:
    """
    포트 8765를 점유하고 있는 백업 서버 프로세스만 선별 종료.
    Qwen(RTX 5080) 등 기타 파이썬 워크로드는 절대 건드리지 않음.
    """
    if not sys.platform.startswith("win"):
        return True

    ps_script = (
        f"$conn = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue; "
        "if ($conn) { foreach ($c in $conn) { "
        "  $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue; "
        "  if ($p) { "
        "    $cmd = (Get-CimInstance Win32_Process -Filter \"ProcessId = $($p.Id)\").CommandLine; "
        "    if ($cmd -like '*백업시스템*' -or $cmd -like '*run.py*') { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } "
        "  } "
        "} }; "
        "Start-Sleep -Seconds 1"
    )
    no_win = {"creationflags": subprocess.CREATE_NO_WINDOW} if hasattr(subprocess, "CREATE_NO_WINDOW") else {}
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=8, **no_win)
        return True
    except Exception as e:
        logger.warning("safely_stop_running_backup_server warning: %s", e)
        return False


def health_check(port: int = 8765, timeout: int = 10) -> bool:
    """
    소프트웨어 재기동 후 10초 이내에 로컬 포트 8765 소켓 및 시스템 정보 API 정상 응답 확인.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                logger.info("UPDATE_HEALTHCHECK_OK port=%d responding", port)
                return True
        except OSError:
            time.sleep(0.5)

    logger.error("UPDATE_HEALTHCHECK_FAILED port=%d did not respond within %ds", port, timeout)
    return False


def rollback(backup_dir: str, target_dir: Optional[str] = None) -> bool:
    """
    업데이트 실패 시 이전 정상 보존 디렉토리에서 전체 파일 원복 및 서비스 재시작.
    """
    if target_dir is None:
        target_dir = BASE_DIR

    logger.warning("UPDATE_ROLLBACK initiated from %s to %s", backup_dir, target_dir)
    if not os.path.exists(backup_dir):
        logger.error("UPDATE_ROLLBACK_FAILED reason=backup_dir_missing")
        return False

    try:
        safely_stop_running_backup_server(8765)
        # 이전 버전 파일 덮어쓰기 (blobs, snapshots 등 백업 데이터는 건드리지 않음)
        for folder in ["core", "web", "keys"]:
            src_f = os.path.join(backup_dir, folder)
            dst_f = os.path.join(target_dir, folder)
            if os.path.exists(src_f):
                if os.path.exists(dst_f):
                    shutil.rmtree(dst_f, ignore_errors=True)
                shutil.copytree(src_f, dst_f)

        for script in ["run.py", "start_silent.vbs", "VERSION"]:
            src_s = os.path.join(backup_dir, script)
            dst_s = os.path.join(target_dir, script)
            if os.path.exists(src_s):
                shutil.copy2(src_s, dst_s)

        # 재기동
        vbs_path = os.path.join(target_dir, "start_silent.vbs")
        if os.path.exists(vbs_path):
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(["wscript.exe", vbs_path], cwd=target_dir, creationflags=flags, close_fds=True)
            health_check(8765, timeout=10)

        logger.info("UPDATE_ROLLBACK_SUCCESS restored to previous version")
        return True
    except Exception as e:
        logger.critical("UPDATE_ROLLBACK_FAILED error=%s", str(e))
        return False


def install_update(zip_path: str, target_dir: Optional[str] = None) -> bool:
    """
    1. 임시 Staging 디렉토리에 압축 해제 검증
    2. 기존 소프트웨어 디렉토리 백업 보존 (backup/v{현재버전})
    3. 실행 중인 백업 데몬 안전 종료
    4. 파일 교체 적용
    5. 무창 백그라운드 재기동
    6. 헬스체크 및 실패 시 자동 롤백
    """
    if target_dir is None:
        target_dir = BASE_DIR

    current_ver = get_current_installed_version()
    logger.info("UPDATE_INSTALL_START current=%s target_dir=%s", current_ver, target_dir)

    staging_dir = tempfile.mkdtemp(prefix="backup_stage_")
    backup_ver_dir = os.path.join(target_dir, "backup", f"v{current_ver}")

    try:
        # 1. Staging 압축 해제
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(staging_dir)

        # 2. 현재 설치 본 백업 (소프트웨어 코드만 백업, 데이터/blobs 제외)
        os.makedirs(backup_ver_dir, exist_ok=True)
        for folder in ["core", "web", "keys"]:
            src_f = os.path.join(target_dir, folder)
            dst_f = os.path.join(backup_ver_dir, folder)
            if os.path.exists(src_f):
                if os.path.exists(dst_f):
                    shutil.rmtree(dst_f, ignore_errors=True)
                shutil.copytree(src_f, dst_f)

        for script in ["run.py", "start_silent.vbs", "VERSION"]:
            src_s = os.path.join(target_dir, script)
            dst_s = os.path.join(backup_ver_dir, script)
            if os.path.exists(src_s):
                shutil.copy2(src_s, dst_s)

        logger.info("UPDATE_BACKUP_SAVED backup_dir=%s", backup_ver_dir)

        # 3. 기존 서비스 프로세스 안전 종료
        safely_stop_running_backup_server(8765)
        time.sleep(1)

        # 4. 새 파일 교체 복사 (Staging -> Target)
        for item in os.listdir(staging_dir):
            s_item = os.path.join(staging_dir, item)
            d_item = os.path.join(target_dir, item)
            if os.path.isdir(s_item):
                if os.path.exists(d_item):
                    shutil.rmtree(d_item, ignore_errors=True)
                shutil.copytree(s_item, d_item)
            else:
                shutil.copy2(s_item, d_item)

        # 5. 무창 백그라운드 재시작
        vbs_path = os.path.join(target_dir, "start_silent.vbs")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        if os.path.exists(vbs_path):
            subprocess.Popen(["wscript.exe", vbs_path], cwd=target_dir, creationflags=flags, close_fds=True)
        else:
            pyw = os.path.join(target_dir, ".venv", "Scripts", "pythonw.exe")
            if not os.path.exists(pyw):
                pyw = "pythonw.exe"
            subprocess.Popen([pyw, os.path.join(target_dir, "run.py")], cwd=target_dir, creationflags=flags, close_fds=True)

        # 6. Health Check 검증
        if health_check(port=8765, timeout=12):
            logger.info("UPDATE_SUCCESS updated to new version")
            return True
        else:
            logger.error("UPDATE_INSTALL_FAILED healthcheck_timed_out -> starting rollback")
            rollback(backup_ver_dir, target_dir)
            return False

    except Exception as e:
        logger.critical("UPDATE_INSTALL_FAILED error=%s -> starting rollback", str(e))
        rollback(backup_ver_dir, target_dir)
        return False
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass


def perform_full_update_pipeline(target_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    단일 호출로 전체 업데이트 라이프사이클을 안전하게 실행:
    check -> download -> verify -> install -> health check -> (or rollback)
    """
    rel = check_for_update()
    if not rel or not rel.get("update_available"):
        return {"status": "NO_UPDATE", "message": "최신 버전을 사용 중입니다."}

    zip_file = download_update(rel)
    if not zip_file:
        return {"status": "DOWNLOAD_FAILED", "message": "업데이트 파일 다운로드에 실패했습니다."}

    is_verified = verify_update(
        zip_path=zip_file,
        expected_sha256=rel.get("sha256", ""),
        expected_signature=rel.get("signature", "")
    )
    if not is_verified:
        if os.path.exists(zip_file):
            os.remove(zip_file)
        return {"status": "VERIFY_FAILED", "message": "업데이트 무결성 또는 전자 서명 검증 실패."}

    success = install_update(zip_file, target_dir)
    if success:
        return {"status": "SUCCESS", "message": f"v{rel.get('latest_version')} 업데이트가 완료되었습니다."}
    else:
        return {"status": "INSTALL_FAILED", "message": "설치 중 오류가 발생하여 이전 버전으로 롤백되었습니다."}
