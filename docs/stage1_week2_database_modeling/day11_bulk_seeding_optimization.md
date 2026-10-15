# Day 11 - Bulk Seeding Optimization

## Lesson

For time-series data, inserting records one at a time creates unnecessary database round-trips. Knex's `batchInsert` groups rows into multi-row inserts, while chunking keeps each insert to a manageable size. The right batch size depends on the database and workload, so measure it with representative data.

## What we added to the code

- **Seed script:** `seed_nodal_market_data.js` generates 10,000 synthetic ERCOT price ticks across four Houston nodes and bulk-inserts them in batches of 1,000. It logs elapsed time and calculated rows per second, and reports then rethrows insertion errors.
- **Seed command:** The database package includes a `seed:run` script to invoke the Knex seed runner.
- **Knex configuration:** `knexfile.js` supplies the development PostgreSQL connection and migration settings used by the infrastructure package.
- **Migration:** The existing initial migration defines the `nodal_market_ticks` range-partitioned table, a default partition, one example daily partition, and a node/time index used by this seed.

## Practical note

This example creates all 10,000 rows in an in-memory array before inserting them. Chunked inserts limit the size of each database statement, but the seed is not stream-backed and does not keep total application memory constant. The generated values are synthetic; the timing and throughput output are measurements of the local run, not a performance guarantee. The migration's dated partition is also only a demonstration, not automated partition management.

## Interview takeaway

I would avoid row-by-row inserts and start with measured, multi-row batches. For larger imports, I would also stream or incrementally read the source so the whole dataset does not need to stay in memory, then tune batch size and transaction boundaries against the target PostgreSQL environment.
