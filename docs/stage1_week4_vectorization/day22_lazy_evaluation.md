# Day 22 - Lazy Evaluation with Polars

## Lesson

An eager DataFrame runs each operation as it is called. A Polars `LazyFrame` instead builds a query plan and executes it when requested, for example with `.collect()`. Deferring execution gives Polars the opportunity to optimize the overall query, such as pushing filters and column selection closer to the data scan.

## What we added to the code

The `lazy_optimizer_demo.py` script creates 500,000 synthetic nodal-price rows, writes them to a temporary Parquet file, and builds a lazy query with filters for Houston-zone prices above 100, a column selection, and a per-node average and count. It prints Polars' optimized query plan, executes the plan with `.collect()`, and reports the collection time and a sample of the results. The temporary dataset is removed when the script exits.

## Why it matters

When reading supported columnar sources such as Parquet, predicate and projection pushdown may let the engine read fewer rows or columns. Whether it can skip particular row groups depends on the file metadata and query. Lazy execution does not mean that a query uses no memory before collection, nor does it guarantee every filter avoids disk reads.

## Practical note

The example demonstrates query planning, not a controlled eager-versus-lazy benchmark. Its prices and zones are synthetic, and it writes the Parquet file during the run. Lazy plans can make transformations more efficient, but actual I/O, memory use, and runtime depend on the data source, file layout, query, and Polars version. Arrow-backed columns and native execution are useful parts of Polars' design, but filtering is not universally zero-copy, and a specific SIMD path or latency improvement should not be assumed. Inspect the optimized plan and benchmark with representative data.

## Interview takeaway

I would use lazy execution when several transformations can be planned together, especially when filtering and selecting columns from large Parquet datasets. I would verify that the plan applies the expected pushdowns and measure the result, rather than claim that the entire dataset is never materialized or that all irrelevant data is always skipped.
