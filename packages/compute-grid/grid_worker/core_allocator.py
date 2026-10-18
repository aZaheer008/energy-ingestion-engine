#!/usr/bin/env python3
"""
Day 17: Dynamic Core Allocation & Process Pool Distribution Engine
Dynamically sizes worker pools and chunks pricing vectors for parallel execution.
"""

import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List
import numpy as np

def compute_chunk_volatility(chunk_id: int, sub_prices: np.ndarray) -> np.ndarray:
    pid = os.getpid()
    print(f"[Worker PID {pid}] Processing chunk {chunk_id} containing {len(sub_prices)} nodes.")
    # Simulate heavy vector math: rolling standard deviation / volatility scaling
    results = np.sqrt(sub_prices * 0.001) + np.mean(sub_prices)
    return results

def get_optimal_worker_count() -> int:
    # Respect container limits or default to system core count minus 1 (reserving 1 for coordinator)
    total_cores = os.cpu_count() or 2
    optimal = max(1, total_cores - 1)
    return optimal

if __name__ == "__main__":
    print(f"=== HOUSTON TRADING INFRASTRUCTURE: DYNAMIC CORE ALLOCATOR ===")
    
    # Generate synthetic high-volume pricing matrix (e.g., 10,000 grid nodes)
    total_nodes = 10_000
    pricing_matrix = np.linspace(30.0, 120.0, total_nodes)
    
    workers = get_optimal_worker_count()
    print(f"Detected System Cores: {os.cpu_count()}")
    print(f"Assigned Optimal Workers (N - 1 rule): {workers}")
    
    # Chunk the pricing matrix evenly across available workers
    chunks = np.array_split(pricing_matrix, workers)
    
    print(f"\nDistributing {total_nodes} nodes across {workers} parallel processes...")
    start_time = time.perf_counter()
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(compute_chunk_volatility, i, chunk)
            for i, chunk in enumerate(chunks)
        ]
        
        # Gather results
        processed_chunks = [f.result() for f in futures]
        
    total_duration = time.perf_counter() - start_time
    
    # Reassemble distributed matrix
    final_output = np.concatenate(processed_chunks)
    
    print(f"\n=== COMPUTATION COMPLETE ===")
    print(f"Total Nodes Processed: {len(final_output)}")
    print(f"Execution Duration: {total_duration:.4f} seconds")
    print(f"Sample Output Head: {final_output[:5]}")