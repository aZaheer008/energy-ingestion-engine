#!/usr/bin/env python3
"""
Day 14: GIL Contention Benchmark Script
Demonstrates how multi-threading fails to scale CPU-bound matrix math in CPython.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import List
import os

# Simulate heavy CPU-bound mathematical workload (e.g., rolling variance/volatility)
def compute_nodal_volatility(node_id: int, iterations: int = 30_000_000) -> float:
    total = 0.0
    # Heavy mathematical crunching loop simulating price variance calculations
    for i in range(iterations):
        total += (i * 0.0001) ** 0.5
    return total

def run_single_threaded(node_ids: List[int]) -> float:
    start_time = time.perf_counter()
    for nid in node_ids:
        compute_nodal_volatility(nid)
    return time.perf_counter() - start_time

def run_multi_threaded(node_ids: List[int], max_workers: int) -> float:
    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(compute_nodal_volatility, node_ids))
    return time.perf_counter() - start_time

if __name__ == "__main__":
    cpu_count = os.cpu_count() or 4
    print(f"=== HOUSTON TRADING INFRASTRUCTURE: GIL BENCHMARK ===")
    print(f"Detected System CPU Cores: {cpu_count}")
    
    # Simulate 4 heavy computation tasks representing regional grid nodes
    test_nodes = [101, 102, 103, 104]
    
    print("\nExecuting Single-Threaded Benchmark...")
    st_duration = run_single_threaded(test_nodes)
    print(f"-> Single-Threaded Duration: {st_duration:.4f} seconds")
    
    print(f"\nExecuting Multi-Threaded Benchmark (Workers: {cpu_count})...")
    mt_duration = run_multi_threaded(test_nodes, max_workers=cpu_count)
    print(f"-> Multi-Threaded Duration:  {mt_duration:.4f} seconds")
    
    print("\n=== ARCHITECTURAL ANALYSIS ===")
    if mt_duration >= (st_duration * 0.8):
        print("RESULT: Conclusive GIL Bottleneck Proven.")
        print("Multi-threading offered zero or negative speedup due to mutex contention.")
    else:
        print("RESULT: Workload completed (verify if tasks yielded I/O).")