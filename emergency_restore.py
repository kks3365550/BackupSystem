"""
독립형 비상 재해 복구 엔진 (Standalone Emergency Disaster Recovery Script)
외부 라이브러리(FastAPI 등) 없이 파이썬 기본 표준 라이브러리(zlib, hashlib, json 등)만으로 동작합니다.
"""

import os
import sys
import json
import zlib
import hashlib
import time
import glob
from typing import Dict, List, Any, Optional

try:
    import zstandard as zstd
except ImportError:
    zstd = None

# Safe stdout/stderr reconfigure to prevent cp949 encoding errors on pure Windows CMD
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def format_bytes(size: int) -> str:
    power = 1024
    n = 0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    while size > power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def get_blob_path(repo_dir: str, sha256_hash: str) -> str:
    if not sha256_hash:
        return ""
    prefix = sha256_hash[:2]
    return os.path.join(repo_dir, "blobs", prefix, f"{sha256_hash}.blob")

def extract_blob(blob_path: str, dest_path: str, expected_sha256: str, verify_hash: bool = True) -> bool:
    if not os.path.exists(blob_path):
        raise FileNotFoundError(f"Blob file not found: {blob_path}")

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_dest = dest_path + ".restore.tmp"

    sha256 = hashlib.sha256() if verify_hash else None

    # Check magic byte for zstd (0x28 0xB5 0x2F 0xFD)
    with open(blob_path, "rb") as fin:
        header = fin.read(4)

    is_zstd = (header == b"\x28\xb5\x2f\xfd")

    with open(blob_path, "rb") as fin, open(temp_dest, "wb") as fout:
        if is_zstd:
            if zstd is None:
                raise RuntimeError("이 백업 블롭은 Zstandard(zstd)로 압축되었습니다. 'pip install zstandard'를 실행해 주세요.")
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(fin) as reader:
                while True:
                    chunk = reader.read(65536)
                    if not chunk:
                        break
                    fout.write(chunk)
                    if sha256:
                        sha256.update(chunk)
        else:
            decompressor = zlib.decompressobj()
            while True:
                chunk = fin.read(65536)
                if not chunk:
                    break
                decompressed = decompressor.decompress(chunk)
                if decompressed:
                    fout.write(decompressed)
                    if sha256:
                        sha256.update(decompressed)
            tail = decompressor.flush()
            if tail:
                fout.write(tail)
                if sha256:
                    sha256.update(tail)

    if verify_hash and sha256.hexdigest() != expected_sha256:
        if os.path.exists(temp_dest):
            os.remove(temp_dest)
        raise ValueError(f"Hash mismatch for {dest_path}")

    if os.path.exists(dest_path):
        try:
            os.remove(dest_path)
        except OSError:
            pass

    os.replace(temp_dest, dest_path)
    return True

def get_candidate_repositories() -> List[str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        script_dir,
        os.path.dirname(script_dir),
        os.path.join(script_dir, "backup_repository"),
        os.path.join(os.path.expanduser("~"), "MyBackup_Repository"),
        r"D:\MyBackup_Repository",
        r"C:\Users\kksjmj\Desktop\ai\백업시스템\backup_repository"
    ]
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        for repo_name in ("MyBackup_Repository", "backup_repository"):
            candidates.append(f"{letter}:\\{repo_name}")
    valid = []
    seen = set()
    for c in candidates:
        norm = os.path.normpath(c).lower()
        if norm not in seen and os.path.exists(os.path.join(c, "snapshots")) and os.path.exists(os.path.join(c, "blobs")):
            seen.add(norm)
            valid.append(c)

    def _latest_snap_time(r: str) -> float:
        s_dir = os.path.join(r, "snapshots")
        try:
            files = [os.path.join(s_dir, f) for f in os.listdir(s_dir) if f.endswith(".json")]
            return max([os.path.getmtime(f) for f in files]) if files else 0.0
        except Exception:
            return 0.0

    valid.sort(key=_latest_snap_time, reverse=True)
    return valid

def find_snapshots(repo_dir: str) -> List[Dict[str, Any]]:
    snaps_dir = os.path.join(repo_dir, "snapshots")
    if not os.path.exists(snaps_dir):
        return []
    
    files = glob.glob(os.path.join(snaps_dir, "snap_*.json"))
    snapshots = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                snapshots.append({
                    "id": data.get("id"),
                    "created_at": data.get("created_at", 0),
                    "iso_time": data.get("iso_time", ""),
                    "profile_name": data.get("profile_name", ""),
                    "file_count": len(data.get("entries", [])),
                    "path": f
                })
        except Exception:
            continue

    snapshots.sort(key=lambda x: x["created_at"], reverse=True)
    return snapshots

def run_emergency_restore(
    repo_dir: str,
    snapshot_path: str,
    target_override: Optional[str] = None,
    remap_user: bool = True,
    overwrite: bool = True,
    verify_hash: bool = True,
    filter_keyword: Optional[str] = None
):
    print("=" * 70)
    print(" [복구시작] 긴급 비상 재해 복구 (Emergency Disaster Recovery)")
    print("=" * 70)
    print(f"[*] 저장소 경로: {repo_dir}")
    print(f"[*] 스냅샷 파일: {snapshot_path}")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    entries = snapshot.get("entries", [])
    total_entries = len(entries)
    print(f"[*] 총 백업 파일 수: {total_entries:,} 개")

    # Filter entries if needed
    if filter_keyword:
        kw = filter_keyword.lower().replace('/', '\\')
        entries = [e for e in entries if kw in (e.get("rel_path", "") + " " + e.get("source_root", "")).lower().replace('/', '\\')]
        print(f"[*] 필터링 적용 ('{filter_keyword}'): {len(entries):,} 개 파일 선택됨")

    if not entries:
        print("[!] 복원할 파일이 없습니다.")
        return

    # User remapping detection
    current_user_profile = os.path.expanduser('~') # e.g. C:\Users\kksjmj or C:\Users\NewUser
    sample_source = entries[0].get("source_root", "")
    remap_from = ""
    if remap_user and "Users" in sample_source:
        parts = sample_source.split(os.sep)
        try:
            u_idx = [p.lower() for p in parts].index("users")
            if u_idx + 1 < len(parts):
                backup_user = parts[u_idx + 1]
                remap_from = os.path.join(parts[0] + os.sep, "Users", backup_user)
                if remap_from.lower() != current_user_profile.lower():
                    print(f"[*] 윈도우 사용자 폴더 리매핑 감지:")
                    print(f"    - 백업 당시: {remap_from}")
                    print(f"    - 현재 시스템: {current_user_profile}")
                else:
                    remap_from = ""
        except ValueError:
            pass

    start_time = time.time()
    restored_count = 0
    skipped_count = 0
    failed_count = 0
    restored_bytes = 0
    total_to_process = len(entries)

    print("-" * 70)
    print("[*] 복원 작업을 시작합니다... (잠시만 기다려주세요)")
    print("-" * 70)

    reg_files_to_import = []

    for idx, entry in enumerate(entries, 1):
        rel_path = entry.get("rel_path", "")
        source_root = entry.get("source_root", "")
        sha256 = entry.get("sha256") or entry.get("blob_id")
        f_size = entry.get("size", 0)
        mtime = entry.get("mtime")

        if not rel_path or not sha256:
            continue

        # Target path calculation
        if target_override:
            dest_path = os.path.normpath(os.path.join(target_override, rel_path))
        else:
            base_dir = source_root
            if remap_from and base_dir.lower().startswith(remap_from.lower()):
                base_dir = current_user_profile + base_dir[len(remap_from):]
            dest_path = os.path.normpath(os.path.join(base_dir, rel_path))

        blob_path = get_blob_path(repo_dir, sha256)

        if not overwrite and os.path.exists(dest_path):
            skipped_count += 1
            continue

        try:
            extract_blob(blob_path, dest_path, sha256, verify_hash=verify_hash)
            if mtime:
                try:
                    os.utime(dest_path, (mtime, mtime))
                except OSError:
                    pass

            if dest_path.lower().endswith(".reg"):
                reg_files_to_import.append(dest_path)

            restored_count += 1
            restored_bytes += f_size
        except Exception as e:
            failed_count += 1

        # Progress reporting
        if idx % 100 == 0 or idx == total_to_process:
            elapsed = time.time() - start_time
            speed = (restored_bytes / elapsed) if elapsed > 0 else 0
            pct = (idx / total_to_process) * 100
            print(f"\r진행률: [{pct:5.1f}%] {idx}/{total_to_process} 파일 | 복원: {restored_count}건 ({format_bytes(restored_bytes)}) | 속도: {format_bytes(int(speed))}/s", end="", flush=True)

    print()
    total_elapsed = time.time() - start_time
    print("=" * 70)
    print(" [완료] 복원 작업이 정상적으로 종료되었습니다!")
    print(f"[*] 총 소요 시간: {total_elapsed:.1f}초")
    print(f"[*] 복원된 파일: {restored_count:,} 개 ({format_bytes(restored_bytes)})")
    if skipped_count > 0:
        print(f"[*] 건너뛴 파일: {skipped_count:,} 개 (이미 존재함)")
    if failed_count > 0:
        print(f"[!] 실패한 파일: {failed_count:,} 개")
    print("=" * 70)

    if reg_files_to_import:
        print(f"\n[*] 복원된 윈도우 레지스트리 백업 파일이 {len(reg_files_to_import)}개 있습니다:")
        for rf in reg_files_to_import[:5]:
            print(f"    - {rf}")
        print("    (필요 시 위 .reg 파일을 실행하여 레지스트리를 복원하세요)")

def main():
    candidates = get_candidate_repositories()
    repo_dir = candidates[0] if candidates else None

    if not repo_dir:
        print("[!] 백업 저장소를 자동으로 찾을 수 없습니다.")
        repo_dir = input("백업 저장소 경로를 입력해주세요 (예: D:\\MyBackup_Repository): ").strip('"\' ')

    snapshots = find_snapshots(repo_dir)
    if not snapshots:
        print(f"[!] '{repo_dir}' 내에 복원 가능한 스냅샷이 존재하지 않습니다.")
        input("\n엔터 키를 누르면 종료합니다...")
        return

    print("\n" + "=" * 70)
    print("       [긴급 비상 복구 매니저] (Emergency Disaster Recovery)")
    print("=" * 70)
    print(f"저장소: {repo_dir}\n")
    print("사용 가능한 백업 스냅샷 목록:")
    for i, snap in enumerate(snapshots):
        is_latest = " [최신 권장]" if i == 0 else ""
        print(f" [{i+1}] {snap['id']} ({snap['iso_time']}) - {snap['file_count']:,}개 파일{is_latest}")

    selected_idx = 0
    if len(snapshots) > 1 and "--auto" not in sys.argv:
        val = input(f"\n복원할 스냅샷 번호를 선택하세요 [기본: 1]: ").strip()
        if val.isdigit() and 1 <= int(val) <= len(snapshots):
            selected_idx = int(val) - 1

    selected_snap = snapshots[selected_idx]
    print(f"\n선택된 스냅샷: {selected_snap['id']}")

    target_override = None
    filter_kw = None

    if "--auto" in sys.argv:
        print("[*] 자동 모드(--auto): 백업 당시의 원본 위치(C드라이브 등)로 즉시 전체 복원을 진행합니다.")
    else:
        print("\n복구 대상 위치를 선택하세요:")
        print(" [1] 원본 위치 그대로 복구 (C드라이브의 원래 위치로 즉시 원상복구) [기본값]")
        print(" [2] 별도 지정 폴더로 복구 (예: C:\\Restored)")
        mode_choice = input("선택 [기본: 1]: ").strip()
        if mode_choice == "2":
            target_override = input("복원할 대상 폴더 경로 입력: ").strip('"\' ')
            if not target_override:
                target_override = r"C:\Restored"

        print("\n복원 범위:")
        print(" [1] 전체 파일 복원 [기본값]")
        print(" [2] 특정 폴더/파일명만 검색하여 선택 복원")
        range_choice = input("선택 [기본: 1]: ").strip()
        if range_choice == "2":
            filter_kw = input("복원할 파일명 또는 경로 키워드 입력 (예: 백업시스템, Documents 등): ").strip()

    confirm = "y"
    if "--auto" not in sys.argv:
        confirm = input("\n복원을 시작하시겠습니까? (Y/n): ").strip().lower()

    if confirm in ("", "y", "yes"):
        run_emergency_restore(
            repo_dir=repo_dir,
            snapshot_path=selected_snap["path"],
            target_override=target_override,
            filter_keyword=filter_kw,
            remap_user=True,
            overwrite=True,
            verify_hash=True
        )
    else:
        print("[*] 복원이 취소되었습니다.")

    if "--auto" not in sys.argv:
        input("\n작업 완료. 엔터 키를 누르면 창을 닫습니다...")

if __name__ == "__main__":
    main()
