#!/usr/bin/env python3
"""
Day 23: Merging & Cleaning Heterogeneous Nodal Datasets
Demonstrates time-series alignment, handling missing intervals, and resampling using Polars.
"""

import polars as pl
from datetime import datetime, timedelta

if __name__ == "__main__":
    print("=" * 70)
    print(" ⚡ HOUSTON TRADING INFRASTRUCTURE: DATASET CLEANING & ALIGNMENT")
    print("=" * 70)
    
    # 1. Simulate messy raw nodal telemetry with missing 5-minute intervals
    print("[*] Generating messy raw telemetry stream with missing intervals...")
    base_time = datetime(2026, 11, 1, 1, 0, 0) # Fall-back transition simulation context
    
    # Intentionally drop interval index 2 (1:10 AM) to simulate a dropped API tick
    timestamps = [
        base_time,
        base_time + timedelta(minutes=5),
        base_time + timedelta(minutes=15), # Missing 1:10 AM!
        base_time + timedelta(minutes=20),
        base_time + timedelta(minutes=25)
    ]
    node_ids = [1001, 1001, 1001, 1001, 1001]
    raw_lmps = [45.2, 46.0, 48.5, 49.1, 50.3]
    
    raw_df = pl.DataFrame({
        "timestamp": timestamps,
        "node_id": node_ids,
        "lmp": raw_lmps
    })
    
    print("Raw Input DataFrame (Notice missing 01:10:00):")
    print(raw_df)
    
    # 2. Enforce Temporal Regularization & Gap-Filling via Polars Resampling
    print("\n[*] Normalizing and aligning time-series intervals (5-minute grid)...")
    
    # Ensure datetime is parsed as proper timestamp type and sort
    cleaned_df = (
        raw_df
        .sort("timestamp")
        .upsample(time_column="timestamp", every="5m", group_by="node_id")
        .select(
            pl.col("timestamp"),
            pl.col("node_id"),
            # Forward-fill missing LMP ticks from the last known valid price
            pl.col("lmp").forward_fill().alias("lmp_filled")
        )
    )
    
    print("\n" + "=" * 70)
    print(" 📊 CLEANED & ALIGNED TELEMETRY RESULT")
    print("=" * 70)
    print(cleaned_df)
    print("\n[+] Heterogeneous dataset cleaning and time-alignment successfully completed.")