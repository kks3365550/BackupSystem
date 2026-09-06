import os
import time
import subprocess
from typing import Dict, Any

def export_windows_drivers(dest_dir: str, force: bool = False) -> Dict[str, Any]:
    """
    Exports all installed third-party/OEM Windows drivers to dest_dir using pnputil.
    Skips re-export if drivers were already exported recently and force=False.
    """
    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)

    # Check if drivers already exist
    existing_inf_count = 0
    total_size = 0
    if os.path.exists(dest_dir):
        for root, dirs, files in os.walk(dest_dir):
            for file in files:
                if file.lower().endswith(".inf"):
                    existing_inf_count += 1
                try:
                    total_size += os.path.getsize(os.path.join(root, file))
                except OSError:
                    pass

    # If already exported 20+ drivers and not forced, reuse existing
    if existing_inf_count >= 20 and not force:
        return {
            "success": True,
            "dest_dir": dest_dir,
            "driver_count": existing_inf_count,
            "total_bytes": total_size,
            "reused": True
        }

    cmd = ["pnputil", "/export-driver", "*", dest_dir]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
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

        return {
            "success": proc.returncode == 0,
            "dest_dir": dest_dir,
            "driver_count": driver_count,
            "total_bytes": total_size,
            "reused": False,
            "output": proc.stdout[:500] if proc.stdout else ""
        }
    except Exception as e:
        return {
            "success": False,
            "dest_dir": dest_dir,
            "error": str(e)
        }
