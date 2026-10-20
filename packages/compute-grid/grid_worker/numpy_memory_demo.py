#!/usr/bin/env python3
"""
Day 20: NumPy Memory Management & Array Manipulation
Demonstrates contiguous memory layouts, strides, views vs. copies, and broadcasting.
"""

import numpy as np

def inspect_array_metadata(name: str, arr: np.ndarray) -> None:
    print(f"--- Metadata for: {name} ---")
    print(f"  Shape          : {arr.shape}")
    print(f"  Data Type      : {arr.dtype}")
    print(f"  Strides        : {arr.strides}")
    print(f"  C-Contiguous   : {arr.flags['C_CONTIGUOUS']}")
    print(f"  Memory Address : {arr.ctypes.data}")
    print(f"  Item Size      : {arr.itemsize} bytes\n")

if __name__ == "__main__":
    print("=== HOUSTON TRADING INFRASTRUCTURE: NUMPY MEMORY DEMO ===\n")
    
    # 1. Initialize a synthetic pricing matrix (e.g., 5 nodes, 4 time intervals)
    # Simulating PJM/ERCOT nodal time-series prices
    pricing_matrix = np.array([
        [45.5, 46.2, 47.0, 48.1],
        [39.0, 40.2, 41.5, 42.0],
        [52.1, 53.0, 54.2, 55.8],
        [30.5, 31.0, 31.5, 32.2],
        [50.0, 51.2, 52.0, 53.5]
    ], dtype=np.float64)
    
    inspect_array_metadata("Master Pricing Matrix", pricing_matrix)
    
    # 2. Demonstrate Views vs. Copies (The Slicing Trap)
    print("[*] Demonstrating Slicing View vs. Copy...")
    node_slice = pricing_matrix[0:2, :] # Standard slice creates a VIEW
    inspect_array_metadata("Node Slice (View)", node_slice)
    
    # Prove they share memory
    print(f"Do slice and master share memory? {np.shares_memory(pricing_matrix, node_slice)}")
    
    # Mutating the view affects the master!
    node_slice[0, 0] = 999.0
    print(f"Master matrix element [0,0] after mutating view: {pricing_matrix[0, 0]} (Corrupted!)")
    
    # Reset master
    pricing_matrix[0, 0] = 45.5
    
    # Safe isolation via explicit copy
    safe_subset = pricing_matrix[0:2, :].copy()
    safe_subset[0, 0] = 999.0
    print(f"Master matrix element [0,0] after mutating explicit copy: {pricing_matrix[0, 0]} (Protected!)")
    
    # 3. Demonstrate Broadcasting (Applying a nodal multiplier vector)
    print("\n[*] Demonstrating Broadcasting (Applying Loss Factors)...")
    # Loss factors vector for 5 nodes (shape: (5,))
    loss_factors = np.array([1.02, 1.01, 1.05, 1.03, 1.04], dtype=np.float64)
    
    # Broadcast vector across 2D matrix columns: shape (5, 4) multiplied by shape (5, 1) reshaped
    adjusted_prices = pricing_matrix * loss_factors[:, np.newaxis]
    
    print(f"Original Row 2 Prices : {pricing_matrix[2]}")
    print(f"Adjusted Row 2 Prices : {adjusted_prices[2]}")
    print("\n[+] NumPy memory management & broadcasting demonstration successfully completed.")