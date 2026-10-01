import os
import sys
import tempfile
import shutil

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.hasher import get_file_stat
from core.replication_queue import ReplicationQueueManager

def test_hasher_get_file_stat():
    print("[*] Testing core.hasher.get_file_stat...")
    tmpdir = tempfile.mkdtemp()
    try:
        # 1. 파일 검증
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("hello world test tier 1")

        stat_res = get_file_stat(test_file)
        assert stat_res is not None, "get_file_stat returned None for existing file"
        assert stat_res['is_file'] is True, "is_file should be True"
        assert stat_res['is_dir'] is False, "is_dir should be False"
        assert stat_res['is_symlink'] is False, "is_symlink should be False"
        assert stat_res['size'] == len("hello world test tier 1"), f"size mismatch: {stat_res['size']}"

        # 2. 디렉토리 검증
        stat_dir = get_file_stat(tmpdir)
        assert stat_dir is not None, "get_file_stat returned None for directory"
        assert stat_dir['is_dir'] is True, "is_dir should be True for dir"
        assert stat_dir['is_file'] is False, "is_file should be False for dir"
        assert stat_dir['is_symlink'] is False, "is_symlink should be False for dir"

        # 3. 존재하지 않는 파일
        non_existent = os.path.join(tmpdir, "does_not_exist.txt")
        assert get_file_stat(non_existent) is None, "Non-existent file must return None"

        print("    [+] get_file_stat passed all tests!")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def test_replication_queue_batch():
    print("[*] Testing core.replication_queue.get_status_batch...")
    tmpdir = tempfile.mkdtemp()
    rq = ReplicationQueueManager(tmpdir)
    try:
        # 1. 빈 목록
        empty_res = rq.get_status_batch([])
        assert empty_res == {}, f"Empty list should return {{}}, got {empty_res}"

        # 2. 작업 추가 후 단건 vs 배치 비교
        for i in range(10):
            sid = f"snap_20261001_{i:03d}"
            rq.enqueue(sid, tmpdir, r"D:\Remote")

        # 단건 get_status 결과와 get_status_batch 비교
        all_ids = [f"snap_20261001_{i:03d}" for i in range(10)]
        batch_res = rq.get_status_batch(all_ids, chunk_size=3) # 청크 3으로 분할 강제

        assert len(batch_res) == 10, f"Expected 10 items, got {len(batch_res)}"

        for sid in all_ids:
            single = rq.get_status(sid)
            batch = batch_res.get(sid)
            assert batch is not None, f"Missing {sid} in batch"
            assert single['state'] == batch['state'], f"State mismatch for {sid}"
            assert single['attempts'] == batch['attempts'], f"Attempts mismatch for {sid}"
            assert single['is_offsite_protected'] == batch['is_offsite_protected'], f"is_offsite_protected mismatch for {sid}"

        # 3. 미존재 ID 혼합
        mixed_ids = ["snap_20261001_001", "non_existent_snap", "snap_20261001_005"]
        mixed_res = rq.get_status_batch(mixed_ids)
        assert len(mixed_res) == 2, f"Expected 2 matches, got {len(mixed_res)}"
        assert "non_existent_snap" not in mixed_res

        print("    [+] get_status_batch passed all tests!")
    finally:
        rq.close()
        shutil.rmtree(tmpdir, ignore_errors=True)

def test_web_app_syntax():
    print("[*] Testing web.app syntax and import...")
    import web.app as app_module
    assert hasattr(app_module, "list_snapshots"), "list_snapshots function not found in web.app"
    print("    [+] web.app successfully imported and list_snapshots exists!")

if __name__ == "__main__":
    test_hasher_get_file_stat()
    test_replication_queue_batch()
    test_web_app_syntax()
    print("\n[SUCCESS] All Tier 1 unit tests passed flawlessly!")
