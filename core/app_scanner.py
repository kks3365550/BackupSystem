import os
import sys
import time
import threading
from typing import List, Dict, Any, Optional

_cached_apps = None
_cached_apps_time = 0
_CACHE_TTL = 300.0  # 5 minutes cache
_scanner_lock = threading.Lock()

def _scan_installed_applications_impl() -> List[Dict[str, Any]]:

    apps = []
    seen_names = set()

    if sys.platform.startswith("win"):
        import winreg

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        ignore_keywords = [
            "KB", "Security Update", "Update for", "Hotfix",
            "Microsoft Visual C++", "Windows Software Development Kit",
            "Microsoft Windows Desktop Runtime", "DirectX", "Vulkan",
            "AMD GPIO", "AMD Interface", "AMD MicroPEP", "AMD PPM", "AMD PSP",
            "AMD Chipset", "Branding64", "Office 16 Click-to-Run",
            "Microsoft .NET", "Microsoft Windows Application"
        ]

        # Pre-scan candidate directories once into an in-memory map (O(1) lookup!)
        candidate_dirs = {}
        roaming_base = os.path.expanduser(r"~\AppData\Roaming")
        roaming_dirs = set()

        for pf in [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.expanduser(r"~\AppData\Local\Programs"),
            roaming_base
        ]:
            if os.path.exists(pf):
                try:
                    with os.scandir(pf) as it:
                        for entry in it:
                            if entry.is_dir(follow_symlinks=False):
                                n_lower = entry.name.lower()
                                if pf == roaming_base:
                                    roaming_dirs.add(n_lower)
                                if n_lower not in candidate_dirs:
                                    candidate_dirs[n_lower] = entry.path
                except OSError:
                    pass

        for hkey, subkey in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            key_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, key_name) as app_key:
                                try:
                                    display_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                    display_name = str(display_name).strip()
                                    if not display_name or display_name.lower() in seen_names:
                                        continue

                                    if any(ign.lower() in display_name.lower() for ign in ignore_keywords):
                                        continue

                                    loc = ""
                                    try:
                                        raw_loc, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                                        raw_loc = str(raw_loc).strip('"').strip()
                                        if raw_loc and os.path.exists(raw_loc):
                                            loc = raw_loc
                                    except FileNotFoundError:
                                        pass

                                    if not loc:
                                        try:
                                            icon, _ = winreg.QueryValueEx(app_key, "DisplayIcon")
                                            icon_p = str(icon).split(",")[0].strip('"').strip()
                                            if icon_p and os.path.exists(icon_p):
                                                loc = os.path.dirname(icon_p) if os.path.isfile(icon_p) else icon_p
                                        except FileNotFoundError:
                                            pass

                                    # Fast in-memory candidate lookup instead of 4x slow disk exists checks
                                    if not loc:
                                        loc = candidate_dirs.get(display_name.lower(), "")

                                    pub = ""
                                    try:
                                        pub, _ = winreg.QueryValueEx(app_key, "Publisher")
                                        pub = str(pub).strip()
                                    except FileNotFoundError:
                                        pass

                                    ver = ""
                                    try:
                                        ver, _ = winreg.QueryValueEx(app_key, "DisplayVersion")
                                        ver = str(ver).strip()
                                    except FileNotFoundError:
                                        pass

                                    is_valid = bool(loc and os.path.exists(loc))
                                    seen_names.add(display_name.lower())

                                    has_roaming = display_name.lower() in roaming_dirs
                                    roaming_guess = os.path.join(roaming_base, display_name) if has_roaming else None

                                    apps.append({
                                        "name": display_name,
                                        "publisher": pub or "소프트웨어",
                                        "version": ver,
                                        "location": loc if is_valid else "",
                                        "has_location": is_valid,
                                        "roaming_path": roaming_guess
                                    })
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            pass
            except OSError:
                pass

    apps.sort(key=lambda x: (0 if x["has_location"] else 1, x["name"].lower()))
    return apps

def get_installed_applications(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Scans Windows Registry to detect genuine installed software applications.
    Caches results in memory with thread-safe double-checked locking (< 1ms).
    """
    global _cached_apps, _cached_apps_time

    now = time.time()
    if not force_refresh and _cached_apps is not None and (now - _cached_apps_time) < _CACHE_TTL:
        return _cached_apps

    with _scanner_lock:
        now = time.time()
        if not force_refresh and _cached_apps is not None and (now - _cached_apps_time) < _CACHE_TTL:
            return _cached_apps

        apps = _scan_installed_applications_impl()
        _cached_apps = apps
        _cached_apps_time = time.time()
        return apps

def get_project_items(base_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lists sub-projects in the AI workspace or user Desktop with fast non-blocking scandir.
    """
    if not base_path:
        candidate_paths = [
            os.path.join(os.path.expanduser("~"), "Desktop", "ai"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ]
        base_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])

    projects = []
    if not os.path.exists(base_path):
        return projects

    try:
        with os.scandir(base_path) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False) and not entry.name.startswith(".") and entry.name != "backup_repository":
                    projects.append({
                        "name": entry.name,
                        "path": entry.path,
                        "item_count": 0
                    })
    except (PermissionError, OSError):
        pass

    projects.sort(key=lambda x: x["name"].lower())
    return projects
