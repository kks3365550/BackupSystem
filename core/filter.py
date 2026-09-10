import fnmatch
import os
from typing import List, Optional, Set

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
    "*.dmp",
    # Crash reports and telemetry
    "*Crashpad*",
    "*CrashReporting*",
    "*crash_reports*",
    # Browser / App caches
    "*Cache*",
    "*GPUCache*",
    "*Code Cache*",
    "*ShaderCache*",
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
    ".nuxt",
    # Massive VM / Disk images that should be excluded from file-level backup
    "*.vhdx",
    "*.vmdk",
    "*.vdi"
]

class PathFilter:
    def __init__(self, exclude_patterns: Optional[List[str]] = None, include_patterns: Optional[List[str]] = None, use_defaults: bool = True):
        raw_excludes = list(DEFAULT_EXCLUDE_PATTERNS) if use_defaults else []
        if exclude_patterns:
            for p in exclude_patterns:
                p = p.strip()
                if p and p not in raw_excludes:
                    raw_excludes.append(p)
        self.include_patterns = include_patterns or []

        # Fix: Pre-split patterns into O(1) exact match set and wildcard patterns
        self.exact_names: Set[str] = set()
        self.wildcard_patterns: List[str] = []

        for pattern in raw_excludes:
            p = pattern.strip().lower()
            if not p or p.startswith('#'):
                continue
            if '*' in p or '?' in p or '[' in p:
                self.wildcard_patterns.append(p)
            else:
                self.exact_names.add(p)

    def is_excluded(self, path: str, is_dir: bool = False) -> bool:
        norm_path = os.path.normpath(path).replace('\\', '/').lower()
        basename = os.path.basename(norm_path)

        # 1. Fast O(1) exact name lookup for basename (covers ~90% of hits: .git, node_modules, desktop.ini, etc.)
        if basename in self.exact_names:
            return True

        # 2. Fast O(1) ancestor directory name lookup
        path_parts = set(norm_path.split('/'))
        if not self.exact_names.isdisjoint(path_parts):
            return True

        # 3. Wildcard matching for remainder patterns (*.tmp, *.pyc, *cache*, etc.)
        for pattern in self.wildcard_patterns:
            if fnmatch.fnmatch(basename, pattern):
                return True
            if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(norm_path, f"*/{pattern}/*") or fnmatch.fnmatch(norm_path, f"*/{pattern}"):
                return True

        return False
