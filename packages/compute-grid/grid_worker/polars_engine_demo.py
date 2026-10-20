#!/usr/bin/env python3
"""
Day 21: High-Performance DataFrames via Polars
Demonstrates multi-threaded columnar aggregations on large nodal pricing datasets.
"""

import time
import polars as pl
import numpy as np

if __name__ == "__main__":
    print("=" * 70)
    print(" ⚡ HOUSTON TRADING INFRASTRUCTURE: POLARS ENGINE BENCHMARK")
    print("=" * 70)
    
    # 1. Generate large synthetic telemetry dataset (1,000,000 rows)
    # Simulating 5-minute LMP ticks across multiple grid nodes
    num_rows = 1_000_000
    print(f"[*] Generating synthetic dataset with {num_rows:,} rows...")
    
    np.random.seed(42)
    node_ids = np.random.randint(1000, 1050, size=num_rows)
    prices = np.random.uniform(20.0, 250.0, size=num_rows)
    timestamps = np.arange(num_rows) # Mock chronological ticks
    
    # Load into a Polars DataFrame (Zero-copy Arrow backed)
    start_load = time.perf_counter()
    df = pl.DataFrame({
        "node_id": node_ids,
        "lmp": prices,
        "timestamp": timestamps
    })
    load_duration = time.perf_counter() - start_load
    print(f"[*] Data loaded into Polars DataFrame in {load_duration:.4f} seconds.")
    print(f"[*] DataFrame Shape: {df.shape}")
    
    # 2. Perform High-Performance Multi-Threaded Aggregation
    print("\n[*] Executing multi-threaded group-by and volatility calculation...")
    start_agg = time.perf_counter()
    
    # Calculate mean and standard deviation of LMP per node using Polars expressions
    summary_df = df.group_by("node_id").agg([
        pl.col("lmp").mean().alias("mean_lmp"),
        pl.col("lmp").std().alias("volatility_lmp"),
        pl.count("lmp").alias("tick_count")
    ]).sort("node_id")
    
    agg_duration = time.perf_counter() - start_agg
    
    print("\n" + "=" * 70)
    print(" 📊 POLARS AGGREGATION TELEMETRY RESULTS")
    print("=" * 70)
    print(f"-> Aggregation Duration        : {agg_duration:.4f} seconds")
    print(f"-> Processed Records / Sec     : {num_rows / agg_duration:,.2f}")
    print("\nSample Aggregation Output Head:")
    print(summary_df.head(5))
    print("\n[+] Polars high-performance execution successfully completed.")