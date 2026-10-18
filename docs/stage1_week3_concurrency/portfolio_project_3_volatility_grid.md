# Portfolio Project 3 - Multi-Processed Volatility Grid

## Project overview

This project brings the compute-grid examples together in a command-line tool. It generates synthetic nodal prices, divides them into chunks, and uses separate worker processes to calculate a sample volatility measure. The goal is to demonstrate CPU-parallel work distribution and basic runtime telemetry.

## What we added to the code

The CLI accepts options for the number of nodes, calculation iterations, and worker processes. If no worker count is supplied, it attempts to read CPU quotas from standard Linux cgroup v1 or v2 files, falls back to `os.cpu_count()` when it finds no limit, and applies an N-1 rule. NumPy splits the generated price vector into chunks, which a `ProcessPoolExecutor` sends to worker processes. The CLI then combines the returned arrays and reports elapsed time, calculated throughput, and sample results.

## Practical notes

This is an educational benchmark using generated prices and a synthetic volatility calculation, not a production pricing engine. The cgroup paths are common examples rather than a guarantee that every container runtime or Kubernetes setup will expose limits in those exact locations. Also, an explicit `--workers` value bypasses automatic sizing, so it can exceed the CPU allocation if set too high.

Although `np.array_split` divides the vector into chunks, passing those arrays to `ProcessPoolExecutor` does not make the process-to-process transfer zero-copy; task arguments are serialized for worker processes. For large datasets, measure this transfer overhead and consider shared memory only if it is justified by the workload.

## Interview takeaway

I would explain that worker sizing should follow the CPU capacity allocated to the container, not blindly use host hardware counts. I would treat N-1 as a tunable starting point, validate it against the actual Kubernetes or Docker limits, and benchmark both computation and data-transfer costs. The CLI demonstrates these ideas, but production use would need more robust container-limit discovery and validation of worker overrides.
