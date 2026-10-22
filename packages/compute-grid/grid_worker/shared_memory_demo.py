#!/usr/bin/env python3
"""
Day 16: Zero-Copy Inter-Process Communication (IPC) via Shared Memory
Demonstrates passing large arrays between processes without serialization overhead.
"""

import time
import os
from multiprocessing import shared_memory, Lock
from multiprocessing.synchronize import Lock as LockType
from concurrent.futures import ProcessPoolExecutor
import numpy as np

def worker_task(
    shm_name: str,
    shape: tuple[int, ...],
    dtype: str,
    index: int,
    lock: LockType,
) -> None:
    # Attach to the existing shared memory block by its unique name
    existing_shm = shared_memory.SharedMemory(name=shm_name)
    
    # Create a NumPy array view backed by the shared memory buffer (Zero Copy!)
    shared_array: np.ndarray = np.ndarray(shape, dtype=dtype, buffer=existing_shm.buf)
    
    pid = os.getpid()
    print(f"[Worker PID {pid}] Attached to shared memory. Processing index {index}...")
    
    # Perform in-place calculation and update shared memory atomically using a Lock
    with lock:
        # Simulate computing volatility adjustment and writing directly back to shared RAM
        shared_array[index] = shared_array[index] * 1.15 + 5.0
        
    # Close the handle (does not free the shared memory block)
    existing_shm.close()
    print(f"[Worker PID {pid}] Updated index {index} successfully in shared RAM.")

if __name__ == "__main__":
    print(f"=== HOUSTON TRADING INFRASTRUCTURE: SHARED MEMORY IPC ===")
    
    # Initialize a sample time-series pricing vector (e.g., 5 nodal prices)
    initial_data = np.array([45.50, 48.20, 52.10, 39.80, 50.00], dtype=np.float64)
    
    # 1. Allocate a shared memory block large enough to hold our NumPy array
    shm = shared_memory.SharedMemory(create=True, size=initial_data.nbytes)
    
    # 2. Create a NumPy array view on the newly allocated shared memory block
    shared_prices: np.ndarray = np.ndarray(
        initial_data.shape, dtype=initial_data.dtype, buffer=shm.buf
    )
    
    # Copy initial data into the shared memory block
    shared_prices[:] = initial_data[:]
    
    print(f"Allocated Shared Memory Block Name: {shm.name}")
    print(f"Initial Shared Prices Vector: {shared_prices}")
    
    # Create a multiprocessing Lock for atomic updates
    lock = Lock()
    
    # Execute parallel updates across multiple processes using ProcessPoolExecutor
    cpu_count = os.cpu_count() or 2
    print(f"\nSpawning worker pool across available cores (Max Workers: {min(cpu_count, 5)})...")
    
    with ProcessPoolExecutor(max_workers=min(cpu_count, 5)) as executor:
        futures = [
            executor.submit(worker_task, shm.name, initial_data.shape, str(initial_data.dtype), i, lock)
            for i in range(len(initial_data))
        ]
        # Wait for all workers to complete
        for f in futures:
            f.result()
            
    print(f"\nFinal Updated Shared Prices Vector in RAM: {shared_prices}")
    
    # Clean up and destroy the shared memory block
    shm.close()
    shm.unlink()
    print("Shared memory block successfully unlinked and released from kernel.")