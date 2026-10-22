# Day 24 - Portfolio Project 4: Vectorized Risk Calculator

## Project overview

This project brings together Polars lazy queries and grouped analytics in a small nodal-price risk-reporting demo. It generates synthetic data, writes it to Parquet, and calculates summary metrics by node and zone.

## What we added to the code

The script creates 1.5 million synthetic price records and stores them in a temporary Parquet file. It scans the file lazily, filters to the `HB_NORTH` and `HB_HOUSTON` zones, selects the columns needed for the calculation, and groups records by node and zone. For each group, it computes mean, standard deviation, peak price, count of prices above 200, total tick count, and spike frequency. It prints the optimized query plan, measures query collection time, sorts by volatility, and displays the top ten groups.

## Practical note

The input prices, timestamps, and zones are synthetic, and the generated timestamps are simple integer values rather than real market datetimes. The metrics demonstrate a query pipeline; they are not a validated financial risk model. The script reports the collection duration separately from mock-data generation and Parquet writing, so that timing does not represent the full pipeline. Polars may optimize scans and aggregations, but actual I/O, memory use, and speed depend on the data and environment.

## Interview takeaway

I would use a lazy scan when working with large columnar files, apply filters and column selection before aggregation, and express grouped calculations with native Polars operations. I would inspect the optimized plan and benchmark end-to-end work on representative data. Before using metrics for decisions, I would validate units, timestamps, thresholds, and calculation definitions with the relevant market and business requirements.
