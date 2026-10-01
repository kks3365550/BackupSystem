# -*- coding: utf-8 -*-
"""
scratch/benchmark_desktop_rc1.py
=================================
Measure end-to-end HTTP API Latency of /api/snapshots on Desktop (100.90.20.59:8765)
v2.9.23 Baseline: 2,947.52 ms
Target: v2.10.0-rc1 Latency & Reduction Rate
"""

import time
import urllib.request
import json
import statistics

TARGET_URL = "http://100.90.20.59:8765/api/snapshots"
VERSION_URL = "http://100.90.20.59:8765/api/version"
V2923_BASELINE_MS = 2947.52

print("=" * 80)
print(" [v2.10.0-rc1 REMOTE HTTP API BENCHMARK ON DESKTOP (100.90.20.59)]")
print("=" * 80)

# 1. 버전 확인
try:
    with urllib.request.urlopen(VERSION_URL, timeout=5) as resp:
        ver_info = json.loads(resp.read().decode('utf-8'))
        print(f"[+] Remote Server Version: {ver_info.get('version', ver_info)}")
except Exception as e:
    print(f"[-] Failed to get version: {e}")

# 2. 10회 반복 측정 (Cold start 1회 + Warm cache 9회)
print("\n[*] Measuring /api/snapshots latency across Tailscale network (10 iterations)...")
latencies = []
snap_count = 0
sample_snap = None

for i in range(10):
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(TARGET_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            data = json.loads(raw)
            snap_count = len(data)
            if sample_snap is None and snap_count > 0:
                sample_snap = data[0]
            tag = "COLD/FIRST" if i == 0 else f"WARM #{i}"
            print(f"  [{tag:10s}] {elapsed:8.2f} ms | Received {snap_count} snapshots")
    except Exception as e:
        print(f"  [Iter {i+1:2d}] ERROR: {e}")
    time.sleep(0.1)

print("\n" + "=" * 80)
print(" [BENCHMARK RESULTS & COMPARISON]")
print("=" * 80)
if latencies:
    cold_latency = latencies[0]
    warm_latencies = latencies[1:] if len(latencies) > 1 else latencies
    avg_warm = statistics.mean(warm_latencies)
    median_warm = statistics.median(warm_latencies)
    min_warm = min(warm_latencies)
    max_warm = max(warm_latencies)
    
    red_from_baseline = ((V2923_BASELINE_MS - avg_warm) / V2923_BASELINE_MS) * 100

    print(f"  v2.9.23 Baseline Latency  : {V2923_BASELINE_MS:10.2f} ms")
    print(f"  v2.10.0-rc1 Cold Latency   : {cold_latency:10.2f} ms")
    print(f"  v2.10.0-rc1 Warm Avg (n=9) : {avg_warm:10.2f} ms")
    print(f"  v2.10.0-rc1 Warm Median    : {median_warm:10.2f} ms")
    print(f"  v2.10.0-rc1 Min / Max      : {min_warm:.2f} ms / {max_warm:.2f} ms")
    print(f"  -------------------------------------------------------------")
    print(f"  TOTAL LATENCY REDUCTION    : {red_from_baseline:9.2f} % (from {V2923_BASELINE_MS:.1f}ms -> {avg_warm:.2f}ms)")
    print("=" * 80)

    if sample_snap:
        print("\n[DATA INTEGRITY & FIELD PRESERVATION]")
        print(f"  Snapshot ID          : {sample_snap.get('id')}")
        print(f"  Timestamp            : {sample_snap.get('timestamp')}")
        print(f"  File Count           : {sample_snap.get('file_count')}")
        print(f"  Total Bytes          : {sample_snap.get('total_bytes')}")
        print(f"  Offsite Status       : {sample_snap.get('offsite_status')}")
        print(f"  Is Offsite Protected : {sample_snap.get('is_offsite_protected')}")
        print(f"  Is Local Protected   : {sample_snap.get('is_local_protected')}")
print("=" * 80)
