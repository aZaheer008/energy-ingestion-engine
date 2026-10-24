# Days 25 to 30: Summary

This summary gathers the implementation, validation, and profiling work completed from Day 25 through Day 30.

## Day 25: Compute-grid tests and edge cases

Added pytest coverage for the compute-grid volatility worker and Polars risk calculator. The tests cover worker sizing, process-pool execution, empty inputs, negative and zero prices, invalid iteration or row counts, partial datasets, and risk aggregation and spike metrics.

The related fixes made negative-price volatility results finite and non-negative, handled empty and partial input data, and validated invalid counts explicitly. Pytest and CPU-compatible Polars dependencies were added to the compute-grid requirements.

**Validation:** All 14 tests passed.

## Day 26: TypeScript-Python type boundary

Ran static checks across the Python and TypeScript parts of the monorepo and hardened the data boundary between them. Python shared-memory and lock handling received clearer types. In the shared TypeScript payload validation, untrusted input is handled as `unknown`, record and enum values are checked safely, and non-finite numbers are rejected while valid negative prices remain supported. The API also avoids unsafe casts and handles unknown errors more carefully.

**Validation:** Mypy passed across 15 Python files; both TypeScript builds, all 14 pytest tests, and focused payload-guard runtime checks passed.

## Day 27: Local containers and orchestration

Expanded the root Docker Compose setup to run PostgreSQL, Redis, and the Fastify ingestion API together. The services have health checks, persistent data volumes, dependency ordering, and migration-before-API-start behavior. The API Dockerfile uses a multi-stage build, `.dockerignore` excludes unnecessary build inputs, and the API and Redis connection settings can be configured. The README was updated with local orchestration instructions.

**Validation:** Compose configuration, TypeScript checks, and an `npm ci --dry-run` check passed. The container image and full service startup were not verified because Docker Desktop's Linux engine was unavailable.

## Day 28: Performance profiling and memory observations

Profiled representative volatility and Polars workloads using `cProfile`, optimized query-plan inspection, elapsed-time measurements, and Windows process working-set sampling.

| Workload | Sample | Observed result |
|---|---|---|
| Volatility worker | 50,000 prices × 100 iterations, direct worker profile | About **0.032 s**; nearly all Python-visible time was in the worker function. |
| Volatility CLI | 50,000 nodes × 100 iterations, 2 workers | **0.6306 s** reported by the CLI, approximately **79,284 nodes/s**. |
| Multiprocessing load | 200,000 nodes × 10,000 iterations, 4 configured workers | **6.5957 s** reported by the CLI, approximately **30,323 nodes/s**. The external run took about **7.42 s**. |
| Process-tree memory | Sampled during the multiprocessing run | Peak aggregate working set observed was about **184.5 MiB**; sampling saw up to 7 processes, including the parent and helper processes. |
| Polars lazy risk query | 1.5 million rows; Parquet file about **10.90 MiB** | Collection took **0.0321 s**, **0.0261 s**, and **0.0213 s** across three runs. The optimized plan pushed down the zone filter and selected 3 of 4 columns. |
| Repeated memory workload | 16 cycles of generating and processing 250,000 rows | Baseline working set was **48.3 MiB**. The final 8 post-cleanup samples ranged from **104.1 to 108.0 MiB**. |

**How to interpret the results:** These are encouraging initial measurements: the sample workloads completed quickly, and the repeated-run memory samples appeared to level off rather than keep rising. It is fair to call this a **promising baseline**, but not to label it definitively good or average without a prior version, a target threshold, or repeated controlled runs on comparable hardware. The memory observations do **not** prove that the program has zero leaks; native allocators and runtime caching can retain working set.

**Profiling limitations:** The Pylance CPU sampler could not run because it requires Python 3.15.0b3 or newer and the selected environment was Python 3.13.2. Polars 2.0.0 no longer provides `LazyFrame.profile()`, so query-plan inspection and collection timing were used instead; `cProfile` cannot break down work inside Polars' native Rust execution. The first CLI attempt also needed `PYTHONIOENCODING=utf-8` to avoid a Windows console encoding error. No source code was changed for this profiling work.

## Day 29: Code review and practice

Reviewed the existing code and re-practiced the concepts from the previous days, including the compute-grid tests, type boundaries, container setup, and profiling approach. No new implementation or performance claim is recorded for this day.

## Day 30: Code review and practice

Continued reviewing and re-practicing the existing code and workflows to reinforce the concepts from Days 25–29. No additional code changes or benchmark results are recorded for this day.
