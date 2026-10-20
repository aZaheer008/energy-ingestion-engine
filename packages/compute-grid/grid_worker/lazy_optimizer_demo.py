#!/usr/bin/env python3
"""
Day 22: Lazy Evaluation & Query Optimization Trees
Demonstrates Polars LazyFrames, predicate pushdown, and execution plan optimization.
"""

import tempfile
import time
from pathlib import Path
import polars as pl
import numpy as np

if __name__ == "__main__":
    print("=" * 70)
    print(" ⚡ HOUSTON TRADING INFRASTRUCTURE: LAZY QUERY OPTIMIZER DEMO")
    print("=" * 70)
    
    # Create a temporary directory for mock parquet storage
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "historical_nodal_prices.parquet"
        
        # 1. Generate and save synthetic historical pricing dataset (500,000 rows)
        num_rows = 500_000
        print(f"[*] Generating mock historical dataset ({num_rows:,} rows) to disk...")
        
        np.random.seed(42)
        data = {
            "node_id": np.random.randint(1000, 1020, size=num_rows),
            "lmp": np.random.uniform(15.0, 300.0, size=num_rows),
            "hour": np.random.randint(0, 24, size=num_rows),
            "zone": np.random.choice(["HB_NORTH", "HB_SOUTH", "HB_WEST", "HB_HOUSTON"], size=num_rows)
        }
        
        # Save eagerly as a parquet file on disk
        df_eager = pl.DataFrame(data)
        df_eager.write_parquet(file_path)
        print(f"[*] Parquet dataset written successfully to: {file_path.name}\n")
        
        # 2. Build a Lazy Query Plan (Deferred Execution)
        print("[*] Constructing Polars Lazy Query Chain...")
        lazy_query = (
            pl.scan_parquet(file_path)
            .filter(pl.col("zone") == "HB_HOUSTON")  # Predicate filter
            .filter(pl.col("lmp") > 100.0)           # Price spike filter
            .select(["node_id", "lmp", "hour"])      # Column projection
            .group_by("node_id")
            .agg(
                pl.col("lmp").mean().alias("avg_spike_lmp"),
                pl.count("lmp").alias("spike_count")
            )
            .sort("avg_spike_lmp", descending=True)
        )
        
        # Inspect the Optimized Execution Plan (Query Optimization Tree)
        print("\n" + "-" * 50)
        print(" 🌲 OPTIMIZED QUERY EXECUTION PLAN (EXPLAIN)")
        print("-" * 50)
        print(lazy_query.explain(optimized=True))
        print("-" * 50)
        
        # 3. Execute the Lazy Plan via .collect()
        print("\n[*] Collecting optimized query results...")
        start_time = time.perf_counter()
        result_df = lazy_query.collect()
        duration = time.perf_counter() - start_time
        
        print("\n" + "=" * 70)
        print(" 📊 LAZY EXECUTION TELEMETRY")
        print("=" * 70)
        print(f"-> Collection Duration         : {duration:.4f} seconds")
        print(f"-> Result Records Found        : {len(result_df)}")
        print("\nTop Houston Pricing Spike Summary:")
        print(result_df.head(5))
        print("\n[+] Lazy evaluation and query optimization demonstration successfully completed.")