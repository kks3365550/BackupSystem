import os
import zipfile
import subprocess
import shutil

zip_path = r"C:\Users\kksjmj\AppData\Local\Temp\backup_update_v2.9.21_1790777420.zip"
print("ZIP exists?", os.path.exists(zip_path))
if not os.path.exists(zip_path):
    import glob
    zips = glob.glob(r"C:\Users\kksjmj\AppData\Local\Temp\backup_update_*.zip")
    print("Found zips:", zips)
    if zips:
        zip_path = zips[-1]

staging_dir = r"C:\Users\kksjmj\AppData\Local\Temp\test_staging"
if os.path.exists(staging_dir):
    shutil.rmtree(staging_dir, ignore_errors=True)
os.makedirs(staging_dir, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(staging_dir)
print("Staging files count:", len(os.listdir(staging_dir)))
st_ver = os.path.join(staging_dir, "VERSION")
if os.path.exists(st_ver):
    print("Staging VERSION content:", open(st_ver).read().strip())
    print("Staging VERSION mtime:", os.path.getmtime(st_ver))

target_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
dst_ver = os.path.join(target_dir, "VERSION")
print("Target VERSION content:", open(dst_ver).read().strip())
print("Target VERSION mtime:", os.path.getmtime(dst_ver))

# Test robocopy command directly
cmd = f'robocopy "{staging_dir}" "{target_dir}" /E /XO /NP /R:3 /W:1'
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("Robocopy returncode:", res.returncode)
print("Robocopy output:\n", res.stdout[:500])

print("After robocopy Target VERSION:", open(dst_ver).read().strip())
shutil.rmtree(staging_dir, ignore_errors=True)
