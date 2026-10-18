#!/usr/bin/env python3
"""
Container-Aware Core Discovery for Kubernetes & Cgroups
Inspects Linux cgroups v1/v2 to determine precise pod CPU limits.
"""

import os
from pathlib import Path
from typing import Optional

def get_container_cpu_limit() -> Optional[float]:
    """
    Inspects cgroup v1 and v2 paths to determine Kubernetes CPU resource limits.
    Returns the exact fractional or integer core limit allocated to the container,
    or None if running unconstrained on bare metal.
    """
    try:
        # 1. Check Cgroup v2 path (/sys/fs/cgroup/cpu.max or /sys/fs/cgroup/somescope/cpu.max)
        # Standard path in modern container runtimes
        cgroup_v2_path = Path("/sys/fs/cgroup/cpu.max")
        if cgroup_v2_path.exists():
            content = cgroup_v2_path.read_text().strip().split()
            if content and content[0] != "max":
                quota = float(content[0])
                period = float(content[1]) if len(content) > 1 else 100000.0
                return quota / period

        # 2. Check Cgroup v1 paths (Common in older K8s deployments)
        quota_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
        period_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
        
        if quota_path.exists() and period_path.exists():
            quota_text = quota_path.read_text().strip()
            period_text = period_path.read_text().strip()
            
            quota = float(quota_text)
            period = float(period_text)
            
            if quota > 0 and period > 0:
                return quota / period

    except Exception as e:
        # Fail gracefully back to system inspection if permission or I/O errors occur
        print(f"[Warning] Failed to parse cgroups: {e}")

    return None

def get_production_worker_count() -> int:
    """
    Determines optimal worker process count by prioritizing Kubernetes cgroup limits
    over host hardware limits, applying the N-1 rule for cluster stability.
    """
    # Check container limit first
    container_limit = get_container_cpu_limit()
    
    if container_limit is not None:
        # Floor the container limit to an integer core count
        effective_cores = max(1, int(container_limit))
        print(f"[Infrastructure] Detected Kubernetes Cgroup CPU Limit: {container_limit:.2f} cores")
    else:
        # Fallback to physical host core count if running outside a container
        effective_cores = os.cpu_count() or 2
        print(f"[Infrastructure] No cgroup limit found. Falling back to host os.cpu_count(): {effective_cores}")

    # Apply the N-1 production rule (reserve 1 core for the main event loop/IPC coordinator)
    optimal_workers = max(1, effective_cores - 1)
    return optimal_workers

if __name__ == "__main__":
    workers = get_production_worker_count()
    print(f"-> Assigned Production Process Pool Workers: {workers}")