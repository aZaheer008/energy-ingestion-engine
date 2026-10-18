# Day 17 - Process Pools and Work Distribution

## Lesson

A process pool is useful when work is CPU-bound, independent, and easy to divide. The goal is to keep workers busy in parallel without creating more processes than the machine or container can support.

## What we added to the code

The dynamic allocator creates a synthetic pricing vector of 10,000 values, chooses a worker count using `os.cpu_count()` with an N-1 rule, and divides the vector into evenly sized chunks with `np.array_split`. It submits each chunk to a `ProcessPoolExecutor`, where a worker applies a sample volatility-like calculation. The parent collects the results, joins them back into one array, and reports the elapsed time.

## Kubernetes-aware allocator sample

The additional `core_allocator_with_kubernetees_limit.py` script demonstrates checking the standard cgroup v2 `cpu.max` file and cgroup v1 quota/period files to estimate a container's CPU allowance. If it cannot find a limit, it falls back to `os.cpu_count()`, then applies the N-1 worker rule. This shows why container resource limits should be considered instead of sizing a pool solely from host CPU count.

This is an educational example, not a complete container-detection library: cgroup mount paths and runtime configurations can vary. It also floors fractional CPU quotas and enforces at least one worker, so a container limited to less than one CPU can still be assigned one process and be throttled. Validate worker sizing against the actual deployment limits and workload.

## Container resource limits

In Kubernetes or Docker, the host may have more CPUs than a container is allowed to use. Depending on the runtime and Python version, `os.cpu_count()` may not reflect the container's CPU quota. Creating a pool from the host count can oversubscribe the pod, leading to contention and CPU throttling. Production worker sizing should use the CPU resources available to the process, taking configured container limits or cgroup quotas into account, with a safe minimum and maximum.

Reserving one core for the coordinator can be a useful starting point for mixed workloads, but N-1 is a heuristic, not a universal rule. For CPU-bound tasks, benchmark against the CPU capacity actually allocated to the container; use fewer workers if orchestration and I/O also need substantial CPU.

## Chunking and interview takeaway

Equal-sized chunks work well when each node takes roughly the same amount of computation. If task costs vary, smaller tasks from a work queue can let faster workers pick up more work, at the cost of additional scheduling overhead. Chunk size should be measured with representative data.

If asked how to size a Kubernetes process pool, I would explain that I first determine the CPU capacity allocated to the container rather than blindly relying on host core count. I then choose a worker count suited to the workload, leave headroom for coordination where needed, and benchmark throughput and throttling. A useful reminder is: **one core for the captain, the rest for the crew**—but only when the container's actual CPU allocation is known.

The original `core_allocator.py` demo uses `os.cpu_count()` and does not inspect Kubernetes settings or cgroup quotas; `core_allocator_with_kubernetees_limit.py` is the separate sample that demonstrates reading standard cgroup quota files.
