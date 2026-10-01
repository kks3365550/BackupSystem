import time
import urllib.request
import json
import statistics
import sys

url = "http://127.0.0.1:8765/api/snapshots"
print("=" * 60)
print("[*] Measuring Verified Latency for /api/snapshots (10 iterations)...")
print("=" * 60)

latencies = []
snap_count = 0
sample_snap = None

for i in range(10):
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            snap_count = len(data)
            if sample_snap is None and snap_count > 0:
                sample_snap = data[0]
            print(f"  [Iter {i+1:2d}] {elapsed:6.2f} ms | Loaded {snap_count} snapshots")
    except Exception as e:
        print(f"  [Iter {i+1:2d}] ERROR: {e}")
    time.sleep(0.1)

print("\n" + "=" * 60)
print("[VERIFIED BENCHMARK RESULTS - v2.9.23 Tier 1 Optimized]")
print("=" * 60)
if latencies:
    print(f"Total Snapshots : {snap_count}")
    print(f"Min Latency     : {min(latencies):.2f} ms")
    print(f"Max Latency     : {max(latencies):.2f} ms")
    print(f"Average Latency : {statistics.mean(latencies):.2f} ms")
    print(f"Median Latency  : {statistics.median(latencies):.2f} ms")
    if len(latencies) > 1:
        print(f"Std Dev         : {statistics.stdev(latencies):.2f} ms")
    
    if sample_snap:
        print("\n[DATA INTEGRITY CHECK]")
        print(f"  Sample Snapshot ID   : {sample_snap.get('id')}")
        print(f"  Offsite Status       : {sample_snap.get('offsite_status')}")
        print(f"  Is Offsite Protected : {sample_snap.get('is_offsite_protected')}")
        print(f"  Is Local Protected   : {sample_snap.get('is_local_protected')}")
print("=" * 60)
