import hashlib
import os
from typing import Optional, Dict, Any

def calculate_sha256(filepath: str, block_size: int = 1048576) -> str:
    """Calculate SHA-256 hash of a file efficiently with 1MB buffer."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()

def calculate_bytes_sha256(data: bytes) -> str:
    """Calculate SHA-256 of byte array."""
    return hashlib.sha256(data).hexdigest()

def get_file_stat(filepath: str) -> Optional[Dict[str, Any]]:
    """Get file size and modified timestamp safely."""
    try:
        st = os.stat(filepath)
        return {
            'size': st.st_size,
            'mtime': st.st_mtime,
            'created': st.st_ctime,
            'is_dir': os.path.isdir(filepath),
            'is_file': os.path.isfile(filepath),
            'is_symlink': os.path.islink(filepath)
        }
    except (PermissionError, FileNotFoundError, OSError):
        return None
