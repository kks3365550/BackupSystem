import os
import sys
import glob
from typing import List, Dict, Any, Optional

def get_installed_applications() -> List[Dict[str, Any]]:
    """
    Scans Windows Registry to detect genuine installed software applications.
    Filters out system internal runtimes and driver components.
    """
    apps = []
    seen_names = set()

    if sys.platform.startswith("win"):
        import winreg

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        # Ignore internal system components & drivers (these are backed up by the Driver engine)
        ignore_keywords = [
            "KB", "Security Update", "Update for", "Hotfix",
            "Microsoft Visual C++", "Windows Software Development Kit",
            "Microsoft Windows Desktop Runtime", "DirectX", "Vulkan",
            "AMD GPIO", "AMD Interface", "AMD MicroPEP", "AMD PPM", "AMD PSP",
            "AMD Chipset", "Branding64", "Office 16 Click-to-Run",
            "Microsoft .NET", "Microsoft Windows Application"
        ]

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

                                    # Check ignore keywords
                                    if any(ign.lower() in display_name.lower() for ign in ignore_keywords):
                                        continue

                                    loc = ""
                                    try:
                                        loc, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                                        loc = str(loc).strip('"').strip()
                                    except FileNotFoundError:
                                        pass

                                    if not loc or not os.path.exists(loc):
                                        try:
                                            icon, _ = winreg.QueryValueEx(app_key, "DisplayIcon")
                                            icon_p = str(icon).split(",")[0].strip('"').strip()
                                            if os.path.exists(icon_p):
                                                loc = os.path.dirname(icon_p) if os.path.isfile(icon_p) else icon_p
                                        except FileNotFoundError:
                                            pass

                                    # Try to find standard install folder in Program Files / AppData
                                    if not loc or not os.path.exists(loc):
                                        for pf in [
                                            r"C:\Program Files",
                                            r"C:\Program Files (x86)",
                                            os.path.expanduser(r"~\AppData\Local\Programs"),
                                            os.path.expanduser(r"~\AppData\Roaming")
                                        ]:
                                            guess = os.path.join(pf, display_name)
                                            if os.path.exists(guess) and os.path.isdir(guess):
                                                loc = guess
                                                break

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

                                    # Check user roaming data path (e.g. AppData\Roaming\<App>)
                                    roaming_guess = os.path.join(os.path.expanduser(r"~\AppData\Roaming"), display_name)
                                    has_roaming = os.path.exists(roaming_guess)

                                    apps.append({
                                        "name": display_name,
                                        "publisher": pub or "소프트웨어",
                                        "version": ver,
                                        "location": loc if is_valid else "",
                                        "has_location": is_valid,
                                        "roaming_path": roaming_guess if has_roaming else None
                                    })
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            pass
            except OSError:
                pass

    # Sort: valid locations first, then by name
    apps.sort(key=lambda x: (0 if x["has_location"] else 1, x["name"].lower()))
    return apps

def get_project_items(base_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lists sub-projects in the AI workspace or user Desktop.
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
        for item in os.listdir(base_path):
            full_p = os.path.join(base_path, item)
            if os.path.isdir(full_p) and not item.startswith(".") and item != "backup_repository":
                try:
                    entries_count = len(os.listdir(full_p))
                except OSError:
                    entries_count = 0

                projects.append({
                    "name": item,
                    "path": full_p,
                    "item_count": entries_count
                })
    except (PermissionError, OSError):
        pass

    projects.sort(key=lambda x: x["name"].lower())
    return projects
