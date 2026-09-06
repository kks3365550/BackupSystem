import os
import sys
import subprocess
from typing import List, Dict, Any, Tuple

def find_app_start_menu_shortcuts(app_name: str, publisher: str = "") -> List[str]:
    """
    Finds Start Menu .lnk shortcuts associated with the given application.
    """
    start_menus = [
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.path.expanduser("~"), r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs")
    ]
    shortcuts = []
    tokens = [t.lower() for t in [app_name, app_name.split()[0] if app_name else "", publisher] if t and len(t) > 1]

    for sm in start_menus:
        if os.path.exists(sm):
            for root, dirs, files in os.walk(sm):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        f_lower = f.lower()
                        root_lower = root.lower()
                        if any(token in f_lower or token in root_lower for token in tokens):
                            full_path = os.path.join(root, f)
                            if full_path not in shortcuts:
                                shortcuts.append(full_path)
    return shortcuts

def find_app_data_directories(app_name: str, publisher: str = "") -> List[str]:
    """
    Finds user AppData Roaming / Local directories for the given application.
    """
    appdatas = []
    bases = [
        os.path.expanduser(r"~\AppData\Roaming"),
        os.path.expanduser(r"~\AppData\Local")
    ]
    tokens = [t for t in [app_name, app_name.split()[0] if app_name else "", publisher] if t and len(t) > 1]

    for base in bases:
        if os.path.exists(base):
            try:
                for entry in os.listdir(base):
                    full_p = os.path.join(base, entry)
                    if os.path.isdir(full_p):
                        entry_lower = entry.lower()
                        if any(t.lower() == entry_lower or t.lower() in entry_lower for t in tokens):
                            if full_p not in appdatas and not entry_lower.startswith("temp"):
                                appdatas.append(full_p)
            except OSError:
                pass
    return appdatas

def export_universal_app_registry(app_name: str, publisher: str = "", dest_dir: str = "") -> List[str]:
    """
    Scans Windows Registry for ANY application and exports:
    1. Uninstall keys (HKLM, HKLM\\WOW6432Node, HKCU) -> makes Windows recognize it in Control Panel / Settings
    2. Software configuration keys (HKCU\\Software\\<App>, HKLM\\Software\\<App>, etc.)
    """
    if not sys.platform.startswith("win"):
        return []

    import winreg
    import tempfile

    if not dest_dir:
        dest_dir = os.path.join(tempfile.gettempdir(), "Universal_Registry_Backup")
    os.makedirs(dest_dir, exist_ok=True)

    exported_files = []
    seen_reg_keys = set()

    clean_name = "".join(c for c in app_name if c.isalnum() or c in (" ", "_", "-")).strip()
    file_prefix = clean_name.replace(" ", "_")[:30]

    # 1. Search Uninstall Keys in all 3 root hives
    uninstall_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM", "HKLM"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM", "HKLM_WOW64"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", "HKCU", "HKCU")
    ]

    for root_hkey, subkey_path, reg_hive_str, file_tag in uninstall_roots:
        try:
            with winreg.OpenKey(root_hkey, subkey_path) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        kname = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, kname) as sub:
                            try:
                                dname, _ = winreg.QueryValueEx(sub, "DisplayName")
                                dname_str = str(dname).strip()
                                if dname_str.lower() == app_name.lower() or app_name.lower() in dname_str.lower():
                                    full_reg_key = f"{reg_hive_str}\\{subkey_path}\\{kname}"
                                    if full_reg_key not in seen_reg_keys:
                                        seen_reg_keys.add(full_reg_key)
                                        out_file = os.path.join(dest_dir, f"{file_prefix}_Uninstall_{file_tag}_{i}.reg")
                                        cmd = ["reg", "export", full_reg_key, out_file, "/y"]
                                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                                        if res.returncode == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                                            exported_files.append(out_file)
                            except FileNotFoundError:
                                pass
                    except OSError:
                        pass
        except OSError:
            pass

    # 2. Search Software Configuration Keys
    software_roots = [
        ("HKCU\\Software", "HKCU"),
        ("HKLM\\Software", "HKLM"),
        ("HKLM\\Software\\WOW6432Node", "HKLM_WOW64")
    ]

    tokens = [t for t in [app_name, app_name.split()[0] if app_name else "", publisher] if t and len(t) > 1]

    for root_path, hive_tag in software_roots:
        for t in tokens:
            full_reg_key = f"{root_path}\\{t}"
            if full_reg_key in seen_reg_keys:
                continue

            clean_t = "".join(c for c in t if c.isalnum() or c in ("_", "-")).strip()
            out_file = os.path.join(dest_dir, f"{file_prefix}_{clean_t}_{hive_tag}.reg")
            cmd = ["reg", "export", full_reg_key, out_file, "/y"]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                    seen_reg_keys.add(full_reg_key)
                    exported_files.append(out_file)
            except Exception:
                pass

    return exported_files

def import_registry_file(reg_filepath: str) -> bool:
    """
    Imports a .reg file back into Windows Registry silently.
    """
    if not sys.platform.startswith("win") or not os.path.exists(reg_filepath):
        return False

    cmd = ["reg", "import", os.path.abspath(reg_filepath)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return res.returncode == 0
    except Exception:
        return False

def collect_full_app_package(app_name: str, publisher: str = "", install_location: str = "", temp_reg_dir: str = "") -> Tuple[List[str], List[str]]:
    """
    Collects the full application package:
    - Install directory
    - AppData user configuration directories
    - Start Menu shortcuts (.lnk)
    - Exported Registry files (.reg)
    Returns: (sources_to_backup, exported_reg_files)
    """
    sources = []
    
    # 1. Main Install Location
    if install_location and os.path.exists(install_location):
        sources.append(os.path.abspath(install_location))

    # 2. AppData directories
    for ap in find_app_data_directories(app_name, publisher):
        if os.path.exists(ap) and ap not in sources:
            sources.append(ap)

    # 3. Start Menu Shortcuts
    for sc in find_app_start_menu_shortcuts(app_name, publisher):
        if os.path.exists(sc) and sc not in sources:
            sources.append(sc)

    # 4. Registry Keys
    reg_files = export_universal_app_registry(app_name, publisher, temp_reg_dir)
    for rf in reg_files:
        parent_dir = os.path.dirname(rf)
        if parent_dir not in sources:
            sources.append(parent_dir)

    return sources, reg_files
