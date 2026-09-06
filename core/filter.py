import fnmatch
import os
from typing import List, Optional

DEFAULT_EXCLUDE_PATTERNS = [
    # Windows system files and caches
    "$RECYCLE.BIN",
    "System Volume Information",
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
    "DumpStack.log.tmp",
    "Thumbs.db",
    "desktop.ini",
    # Temp files and lock files
    "*.tmp",
    "*.temp",
    "*.lock",
    "*~*",
    # Development / Cache folders
    "__pycache__",
    "*.pyc",
    ".git",
    "node_modules",
    ".cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt"
]

class PathFilter:
    def __init__(self, exclude_patterns: Optional[List[str]] = None, include_patterns: Optional[List[str]] = None, use_defaults: bool = True):
        self.exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS) if use_defaults else []
        if exclude_patterns:
            for p in exclude_patterns:
                p = p.strip()
                if p and p not in self.exclude_patterns:
                    self.exclude_patterns.append(p)
        self.include_patterns = include_patterns or []

    def is_excluded(self, path: str, is_dir: bool = False) -> bool:
        norm_path = os.path.normpath(path).replace('\\', '/')
        basename = os.path.basename(norm_path)

        for pattern in self.exclude_patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith('#'):
                continue
            
            # Match basename
            if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(basename.lower(), pattern.lower()):
                return True
            
            # Match full or relative path pattern
            if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(norm_path, f"*/{pattern}/*") or fnmatch.fnmatch(norm_path, f"*/{pattern}"):
                return True
            
            if pattern in norm_path.split('/'):
                return True

        return False
