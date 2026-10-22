#!/usr/bin/env python3
"""
Day 24: Portfolio Project #4 – The Vectorized Risk Calculator
Consumes large-scale historical nodal data via Polars LazyFrames, applies predicate 
pushdowns, calculates multi-node risk metrics, and generates a structured risk report.
"""

import time
import tempfile
from pathlib import Path
import polars as pl
import numpy as np

def generate_mock_historical_data(file_path: Path, num_rows: int = 2_000_000) -> None:
    """Generates a large-scale synthetic historical pricing dataset and saves to Parquet."""
    if num_rows < 0:
        raise ValueError("num_rows must be non-negative")

    print(f"[*] Generating synthetic historical dataset ({num_rows:,} rows)...")
    num_ticks = (num_rows + 49) // 50
    rng = np.random.default_rng(42)
    
    data = {
        "timestamp": np.repeat(np.arange(num_ticks), 50)[:num_rows], # 50 nodes per tick
        "node_id": np.tile(np.arange(1000, 1050), num_ticks)[:num_rows],
        "lmp": rng.uniform(15.0, 350.0, size=num_rows),
        "zone": np.repeat(rng.choice(["HB_NORTH", "HB_SOUTH", "HB_WEST", "HB_HOUSTON"], size=num_ticks), 50)[:num_rows]
    }
    
    df = pl.DataFrame(data)
    df.write_parquet(file_path)
    print(f"[+] Dataset successfully written to disk: {file_path}")

def run_vectorized_risk_engine(file_path: Path) -> pl.DataFrame:
    """
    Executes an optimized Polars lazy query plan to compute nodal risk metrics:
    - Mean LMP
    - LMP Volatility (Standard Deviation)
    - Price Spike Frequency (LMP > $200)
    """
    print("\n[*] Initializing Polars LazyFrame and Query Optimization Plan...")
    
    # Construct Lazy Query Pipeline
    lazy_risk_pipeline = (
        pl.scan_parquet(file_path)
        .filter(pl.col("zone").is_in(["HB_NORTH", "HB_HOUSTON"])) # Predicate pushdown filter
        .select(["timestamp", "node_id", "zone", "lmp"])          # Projection minimization
        .group_by(["node_id", "zone"])
        .agg([
            pl.col("lmp").mean().alias("mean_lmp"),
            pl.col("lmp").std().alias("volatility_lmp"),
            pl.col("lmp").max().alias("peak_lmp"),
            # Count price spikes where LMP exceeds $200
            (pl.col("lmp") > 200.0).sum().alias("spike_count"),
            pl.count("lmp").alias("total_ticks")
        ])
        .with_columns(
            # Calculate spike frequency percentage
            (pl.col("spike_count") / pl.col("total_ticks") * 100).alias("spike_frequency_pct")
        )
        .sort("volatility_lmp", descending=True)
    )
    
    # Print Optimized Query Plan
    print("\n--- Optimized Query Execution Plan ---")
    print(lazy_risk_pipeline.explain(optimized=True))
    print("--------------------------------------\n")
    
    # Execute Collection
    print("[*] Executing optimized risk computation across multi-core Rust engine...")
    start_time = time.perf_counter()
    result_df = lazy_risk_pipeline.collect()
    duration = time.perf_counter() - start_time
    
    print(f"[+] Risk computation completed in {duration:.4f} seconds.")
    return result_df

if __name__ == "__main__":
    print("=" * 70)
    print(" ⚡ HOUSTON TRADING INFRASTRUCTURE: PORTFOLIO PROJECT #4")
    print(" 🚀 VECTORIZED RISK CALCULATOR (POLARS / RUST ENGINE)")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        parquet_file = Path(tmpdir) / "large_historical_nodal_prices.parquet"
        
        # Step 1: Generate Mock Data
        generate_mock_historical_data(parquet_file, num_rows=1_500_000)
        
        # Step 2: Run Risk Engine
        risk_report = run_vectorized_risk_engine(parquet_file)
        
        # Step 3: Display Structured Risk Report
        print("\n" + "=" * 70)
        print(" 📊 STAGE 1, WEEK 4: STRUCTURED NODAL RISK REPORT (Top 10)")
        print("=" * 70)
        print(risk_report.head(10))
        print("\n[+] Portfolio Project #4 successfully executed and validated.")