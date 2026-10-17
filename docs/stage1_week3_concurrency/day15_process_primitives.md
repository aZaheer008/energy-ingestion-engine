# Day 15 - Processes and Parallel Computing

## Lesson

Processes can run CPU-bound Python work in separate interpreter instances, allowing work to use multiple CPU cores without being limited by the GIL in a single process. This is different from threads, which share one process and are often a better fit for work spent waiting on I/O.

## What we added to the code

The process-pool demo simulates four CPU-heavy nodal calculations. It uses `ProcessPoolExecutor` to distribute node IDs across worker processes, logs each worker's process ID, collects the results, and measures the elapsed time. The worker count is capped at four, based on the available CPU count. A main-module guard makes the script safer to launch with multiprocessing on Windows.

## Practical note

The calculation is a synthetic CPU workload rather than real volatility analysis. The demo illustrates process isolation and timing; actual speedup depends on the machine, process startup cost, and the amount of work per task. Process pools also have overhead for starting workers and transferring task inputs and results, so keep tasks substantial and measure representative workloads. This example does not implement shared memory.

## Interview takeaway

I would use a process pool for independent, CPU-bound analytics and reserve threads or asynchronous I/O for network- and disk-bound tasks. I would benchmark the full workload—including startup and data-transfer costs—before selecting the worker count or adding shared-memory complexity.
