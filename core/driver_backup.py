import os
import time
import subprocess
from typing import Dict, Any

def export_windows_drivers(dest_dir: str, force: bool = False) -> Dict[str, Any]:
    """
    Exports all installed third-party/OEM Windows drivers to dest_dir using pnputil.
    Uses .driver_manifest.json to avoid repeating the heavy multi-minute export on every backup!
    """
    import json
    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    manifest_file = os.path.join(dest_dir, ".driver_manifest.json")

    # Fast cache hit: return in ~0ms if drivers were already exported
    if os.path.exists(manifest_file) and not force:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["reused"] = True
                return data
        except Exception:
            pass

    # Quick check if directory already contains exported drivers
    existing_inf_count = 0
    total_size = 0
    try:
        with os.scandir(dest_dir) as it:
            for entry in it:
                if entry.is_dir():
                    # Check first subfolder for .inf
                    try:
                        for sub_f in os.listdir(entry.path):
                            if sub_f.lower().endswith(".inf"):
                                existing_inf_count += 1
                                break
                    except OSError:
                        pass
                elif entry.name.lower().endswith(".inf"):
                    existing_inf_count += 1
    except OSError:
        pass

    if existing_inf_count >= 10 and not force:
        result = {
            "success": True,
            "dest_dir": dest_dir,
            "driver_count": existing_inf_count,
            "total_bytes": total_size,
            "reused": True
        }
        try:
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
        return result

    cmd = ["pnputil", "/export-driver", "*", dest_dir]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="cp949", errors="replace", timeout=180)
        
        driver_count = 0
        total_size = 0
        for root, dirs, files in os.walk(dest_dir):
            for file in files:
                if file.lower().endswith(".inf"):
                    driver_count += 1
                try:
                    total_size += os.path.getsize(os.path.join(root, file))
                except OSError:
                    pass

        result = {
            "success": proc.returncode == 0,
            "dest_dir": dest_dir,
            "driver_count": driver_count,
            "total_bytes": total_size,
            "reused": False,
            "output": proc.stdout[:500] if proc.stdout else ""
        }
        if proc.returncode == 0:
            try:
                with open(manifest_file, "w", encoding="utf-8") as f:
                    json.dump(result, f)
            except Exception:
                pass
        return result
    except Exception as e:
        return {
            "success": False,
            "dest_dir": dest_dir,
            "error": str(e)
        }
