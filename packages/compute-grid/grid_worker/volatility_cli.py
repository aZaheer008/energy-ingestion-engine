#!/usr/bin/env python3
"""
Day 18: Portfolio Project #3 – The Multi-Processed Volatility Grid CLI
A production-grade parallel Python CLI analytics engine for high-volume nodal pricing volatility.
"""

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Optional
import numpy as np

def get_container_cpu_limit() -> Optional[float]:
    """Inspects cgroup v1 and v2 paths to determine Kubernetes CPU resource limits."""
    try:
        cgroup_v2_path = Path("/sys/fs/cgroup/cpu.max")
        if cgroup_v2_path.exists():
            content = cgroup_v2_path.read_text().strip().split()
            if content and content[0] != "max":
                quota = float(content[0])
                period = float(content[1]) if len(content) > 1 else 100000.0
                return quota / period

        quota_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
        period_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
        
        if quota_path.exists() and period_path.exists():
            quota = float(quota_path.read_text().strip())
            period = float(period_path.read_text().strip())
            if quota > 0 and period > 0:
                return quota / period
    except Exception:
        pass
    return None

def resolve_optimal_workers(requested_workers: Optional[int]) -> int:
    """Resolves worker count using container limits and the N-1 production rule."""
    if requested_workers and requested_workers > 0:
        return requested_workers

    container_limit = get_container_cpu_limit()
    if container_limit is not None:
        effective_cores = max(1, int(container_limit))
    else:
        effective_cores = os.cpu_count() or 2

    # N-1 rule: Reserve 1 core for the master coordinator loop
    return max(1, effective_cores - 1)

def compute_node_chunk_volatility(chunk_id: int, prices: np.ndarray, iterations: int) -> np.ndarray:
    """Worker function executed inside an isolated OS process."""
    pid = os.getpid()
    # Simulate heavy quantitative calculation (rolling volatility proxy)
    accumulator = np.zeros_like(prices)
    for i in range(iterations):
        accumulator += np.sqrt(prices * (0.0001 * (i % 5 + 1)))
    
    # Calculate synthetic volatility metric
    volatility_metric = np.std(accumulator) * np.mean(prices) / 100.0
    # Return array filled with computed metric mapped to chunk size
    return np.full_shape_like if hasattr(np, 'full_shape_like') else np.full(prices.shape, volatility_metric)

def main() -> None:
    parser = argparse.ArgumentParser(description="HOUSTON ENERGY TRADING: Multi-Processed Volatility Grid Engine")
    parser.add_argument("--nodes", type=int, default=10000, help="Total number of grid nodes to simulate (default: 10,000)")
    parser.add_argument("--iterations", type=int, default=500, help="Mathematical intensity iterations per worker (default: 500)")
    parser.add_argument("--workers", type=int, default=None, help="Explicit worker process count (defaults to container/host N-1)")
    
    args = parser.parse_args()

    print("=" * 70)
    print(" ⚡ HOUSTON INFRASTRUCTURE: MULTI-PROCESSED VOLATILITY GRID ENGINE")
    print("=" * 70)

    workers = resolve_optimal_workers(args.workers)
    print(f"[*] Master Process PID         : {os.getpid()}")
    print(f"[*] Target Grid Nodes          : {args.nodes:,}")
    print(f"[*] Calculation Iterations     : {args.iterations:,}")
    print(f"[*] Allocated Worker Processes : {workers}")

    # Generate synthetic nodal pricing matrix (e.g., ERCOT/PJM node LMP vectors)
    np.random.seed(42)
    pricing_matrix = np.random.uniform(25.0, 150.0, size=args.nodes)

    # Chunk matrix across worker pool
    chunks = np.array_split(pricing_matrix, workers)

    print(f"\n[*] Distributing pricing matrix into {len(chunks)} chunks across process pool...")
    start_time = time.perf_counter()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(compute_node_chunk_volatility, i, chunk, args.iterations)
            for i, chunk in enumerate(chunks)
        ]
        results = [f.result() for f in futures]

    duration = time.perf_counter() - start_time
    combined_output = np.concatenate(results)

    print("\n" + "=" * 70)
    print(" 📊 EXECUTION BENCHMARK & TELEMETRY")
    print("=" * 70)
    print(f"-> Total Processed Nodes       : {len(combined_output):,}")
    print(f"-> Total Execution Duration    : {duration:.4f} seconds")
    print(f"-> Throughput                  : {args.nodes / duration:,.2f} nodes/sec")
    print(f"-> Sample Volatility Result Head : {combined_output[:3]}\n")
    print("[+] Portfolio Project #3 execution successfully completed.")

if __name__ == "__main__":
    main()