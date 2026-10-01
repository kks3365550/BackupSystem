import time
import urllib.request
import json
import statistics

url = "http://127.0.0.1:8765/api/snapshots"
print("[*] Measuring Baseline latency for /api/snapshots (10 iterations)...")

latencies = []
snap_count = 0
for i in range(10):
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            elapsed = (time.time() - t0) * 1000
            latencies.append(elapsed)
            snap_count = len(data)
    except Exception as e:
        print(f"Error on iteration {i}: {e}")
    time.sleep(0.1)

if latencies:
    print(f"[+] Total snapshots returned: {snap_count}")
    print(f"[+] Min latency: {min(latencies):.2f} ms")
    print(f"[+] Max latency: {max(latencies):.2f} ms")
    print(f"[+] Avg latency: {statistics.mean(latencies):.2f} ms")
    print(f"[+] Median latency: {statistics.median(latencies):.2f} ms")
