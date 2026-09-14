# -*- coding: utf-8 -*-
"""
core/verify.py: 백업 무결성 자동 검증 엔진 (Health Check Engine)
- zstandard / zlib 압축 블롭 스트림 및 해시 무결성 검증
- 스냅샷 저장 직후 신규 청크 및 샘플 청크 물리적 무결성 검사
- 손상된 블롭(Bit Rot / Bad Block) 조기 감지
"""

import os
import zlib
import hashlib
import random
from typing import Dict, Any, List, Optional, Tuple
from core.storage import BlobStorage, ZSTD_MAGIC, HAS_ZSTD

if HAS_ZSTD:
    import zstandard as zstd


class IntegrityVerifier:
    """스냅샷 및 블롭 저장소의 물리적 무결성을 검증하는 엔진"""

    def __init__(self, repo_dir: str):
        self.repo_dir = os.path.abspath(repo_dir)
        self.storage = BlobStorage(self.repo_dir)

    def verify_blob(self, sha256_hash: str) -> Tuple[bool, Optional[str]]:
        """
        단일 블롭의 압축 해제 및 SHA-256 일치 여부를 검증.
        반환: (성공 여부, 오류 메시지)
        """
        blob_path = self.storage.get_blob_abs_path(sha256_hash)
        if not os.path.exists(blob_path):
            return False, f"블롭 파일이 존재하지 않음: {sha256_hash}"

        try:
            with open(blob_path, "rb") as f:
                magic = f.read(4)

            is_zstd = (magic == ZSTD_MAGIC)
            decompressed_hasher = hashlib.sha256()

            with open(blob_path, "rb") as f_in:
                if is_zstd and HAS_ZSTD:
                    dctx = zstd.ZstdDecompressor()
                    with dctx.stream_reader(f_in) as reader:
                        while True:
                            chunk = reader.read(262144)
                            if not chunk:
                                break
                            decompressed_hasher.update(chunk)
                else:
                    # zlib 또는 zstd 미지원 환경 폴백
                    decomp = zlib.decompressobj()
                    while True:
                        raw = f_in.read(262144)
                        if not raw:
                            break
                        chunk = decomp.decompress(raw)
                        if chunk:
                            decompressed_hasher.update(chunk)

            calculated_hash = decompressed_hasher.hexdigest()
            if calculated_hash.lower() != sha256_hash.lower():
                return False, f"해시 불일치 (기록: {sha256_hash}, 계산: {calculated_hash})"

            return True, None

        except Exception as e:
            return False, f"압축 해제 또는 데이터 무결성 오류: {str(e)}"

    def verify_snapshot(
        self,
        snapshot_manifest: Dict[str, Any],
        sample_ratio: float = 0.1,
        max_samples: int = 100,
        verify_all_new: bool = True
    ) -> Dict[str, Any]:
        """
        스냅샷 내 블롭들의 무결성을 검증.
        - verify_all_new=True: 이번 백업에서 신규/수정 생성된 블롭은 100% 전수 검증
        - 기존 블롭은 sample_ratio(기본 10%, 최대 max_samples개) 무작위 표본 검증
        """
        entries = snapshot_manifest.get("entries", [])
        if not entries:
            return {
                "success": True,
                "verified_count": 0,
                "error_count": 0,
                "errors": [],
                "detail": "검증할 파일 항목 없음"
            }

        new_hashes = set()
        existing_hashes = set()

        for entry in entries:
            h = entry.get("blob_id") or entry.get("sha256")
            if not h:
                continue
            status = entry.get("status", "")
            if status in ("new", "modified"):
                new_hashes.add(h)
            else:
                existing_hashes.add(h)

        targets_to_verify = set()
        if verify_all_new:
            targets_to_verify.update(new_hashes)

        # 기존 블롭 샘플링
        if existing_hashes:
            sample_size = min(len(existing_hashes), max(10, int(len(existing_hashes) * sample_ratio)))
            sample_size = min(sample_size, max_samples)
            sampled = random.sample(list(existing_hashes), sample_size)
            targets_to_verify.update(sampled)

        verified_count = 0
        errors = []

        for blob_hash in targets_to_verify:
            ok, err = self.verify_blob(blob_hash)
            if ok:
                verified_count += 1
            else:
                errors.append({"blob_id": blob_hash, "error": err})

        success = (len(errors) == 0)
        return {
            "success": success,
            "total_candidates": len(targets_to_verify),
            "verified_count": verified_count,
            "error_count": len(errors),
            "errors": errors,
            "new_verified": len(new_hashes),
            "sample_verified": len(targets_to_verify) - len(new_hashes)
        }
