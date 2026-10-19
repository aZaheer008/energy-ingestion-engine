#!/usr/bin/env python3
"""
Day 19: Financial Vectorization vs. Nested For-Loops Benchmark
Demonstrates order-of-magnitude performance gains using vectorized array operations.
"""

import time
import numpy as np

def run_nested_loops_spark_spread(power_prices: np.ndarray, gas_prices: np.ndarray, heat_rate: float) -> np.ndarray:
    """Naive unscaled approach using Python loops (Anti-Pattern)."""
    n = len(power_prices)
    spreads = np.zeros(n, dtype=np.float64)
    for i in range(n):
        # Naive nested calculation simulating inefficient quant logic
        # Spark Spread = Power Price - (Gas Price * Heat Rate)
        cost = 0.0
        for _ in range(10):  # Simulate internal factor loop
            cost = gas_prices[i] * heat_rate
        spreads[i] = power_prices[i] - cost
    return spreads

def run_vectorized_spark_spread(power_prices: np.ndarray, gas_prices: np.ndarray, heat_rate: float) -> np.ndarray:
    """Optimized vectorized array expression using contiguous memory & SIMD."""
    # Entire array computed in a single compiled C-level vectorized operation
    return power_prices - (gas_prices * heat_rate)

if __name__ == "__main__":
    print("=== HOUSTON TRADING INFRASTRUCTURE: VECTORIZATION BENCHMARK ===")
    
    # Generate 100,000 synthetic nodal price points
    size = 100_000
    np.random.seed(42)
    power_prices = np.random.uniform(25.0, 150.0, size=size)
    gas_prices = np.random.uniform(2.0, 6.0, size=size)
    heat_rate = 7.5  # Typical heat rate constant
    
    print(f"Dataset Size: {size:,} grid nodes")
    
    # 1. Benchmark Naive Nested Loops
    print("\nExecuting Naive Nested For-Loops...")
    start_time = time.perf_counter()
    loop_result = run_nested_loops_spark_spread(power_prices, gas_prices, heat_rate)
    loop_duration = time.perf_counter() - start_time
    print(f"-> Nested Loops Duration : {loop_duration:.4f} seconds")
    
    # 2. Benchmark Vectorized Array Expression
    print("\nExecuting Vectorized Array Expression...")
    start_time = time.perf_counter()
    vec_result = run_vectorized_spark_spread(power_prices, gas_prices, heat_rate)
    vec_duration = time.perf_counter() - start_time
    print(f"-> Vectorized Duration   : {vec_duration:.4f} seconds")
    
    # Verify mathematical parity
    assert np.allclose(loop_result, vec_result), "Mathematical mismatch between loops and vectors!"
    
    # Calculate speedup factor
    speedup = loop_duration / vec_duration if vec_duration > 0 else 0
    print("\n=== PERFORMANCE TELEMETRY ===")
    print(f"Speedup Factor Achieved: {speedup:,.1f}x faster using vectorization!")
    print(f"Sample Vectorized Output Head: {vec_result[:3]}")