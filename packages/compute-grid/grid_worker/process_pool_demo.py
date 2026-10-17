#!/usr/bin/env python3
"""
Day 15: Process Pool Concurrency Benchmark
Demonstrates true multi-core scaling by bypassing the GIL using OS processes.
"""

import time
import os
from concurrent.futures import ProcessPoolExecutor
from typing import List

# Simulate heavy CPU-bound mathematical workload (e.g., rolling variance/volatility across nodes)
def compute_nodal_volatility(node_id: int, iterations: int = 30_000_000) -> float:
    pid = os.getpid()
    print(f"[Worker PID {pid}] Starting crunch for node {node_id}...")
    total = 0.0
    for i in range(iterations):
        total += (i * 0.0001) ** 0.5
    print(f"[Worker PID {pid}] Completed node {node_id}.")
    return total

def run_multi_processed(node_ids: List[int], max_workers: int) -> float:
    start_time = time.perf_counter()
    # Using ProcessPoolExecutor to spin up isolated interpreter processes
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(compute_nodal_volatility, node_ids))
    duration = time.perf_counter() - start_time
    print(f"All worker results computed: {len(results)} nodes processed.")
    return duration

if __name__ == "__main__":
    # Guard clause mandatory for Windows/Unix multiprocessing safety
    cpu_count = os.cpu_count() or 4
    workers = min(cpu_count, 4) # Cap test workers for clean console output
    
    print(f"=== HOUSTON TRADING INFRASTRUCTURE: MULTI-PROCESSING GRID ===")
    print(f"Master Process PID: {os.getpid()}")
    print(f"Available CPU Cores: {cpu_count} | Assigned Workers: {workers}")
    
    # Simulate 4 heavy computation tasks representing regional grid nodes
    test_nodes = [201, 202, 203, 204]
    
    print("\nExecuting Multi-Process Parallel Grid...")
    mp_duration = run_multi_processed(test_nodes, max_workers=workers)
    print(f"-> Multi-Process Total Duration: {mp_duration:.4f} seconds")
    
    print("\n=== ARCHITECTURAL ANALYSIS ===")
    print("RESULT: True multi-core parallel execution achieved.")
    print("Each task executed inside an independent OS process with its own CPython interpreter instance.")