import os
import subprocess

code = (
    "import psutil\n"
    "try:\n"
    "    p = psutil.Process(21840)\n"
    "    print('PID 21840 Name:', p.name())\n"
    "    print('PID 21840 Cmdline:', p.cmdline())\n"
    "    print('PID 21840 Status:', p.status())\n"
    "except Exception as e:\n"
    "    print('Error:', e)\n"
)
app_dir = r"C:\Users\kksjmj\AppData\Local\Programs\백업시스템"
internal_py = os.path.join(app_dir, "python", "python.exe")
res = subprocess.run([internal_py, "-c", code], capture_output=True, text=True)
print(res.stdout)
