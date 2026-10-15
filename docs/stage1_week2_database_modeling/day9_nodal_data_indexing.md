# Day 9 - Nodal Data Indexing

## Lesson

Nodal electricity prices are time-series data: each observation belongs to a market node and a time. At a scale of 10,000 nodes with a five-minute interval, the illustrative volume is:

```text
10,000 nodes x 12 intervals/hour x 24 hours/day = 2,880,000 rows/day
```

The exact volume depends on the market, the number of nodes, and the data interval. As a table grows, time-based partitioning can make it easier to isolate recent writes, narrow time-bounded queries, and manage old data.

## Range partitioning and indexes

The example uses PostgreSQL declarative range partitioning on `executed_at`. The parent table describes the shared row shape; each child partition stores rows for a timestamp range. PostgreSQL routes an insert to the matching child, and queries with a restrictive time predicate can use **partition pruning** to skip partitions that cannot contain matching rows.

A composite B-tree index on `(node_id, executed_at)` can support lookups by node and time range. Indexes should reflect real query patterns and be validated with `EXPLAIN (ANALYZE, BUFFERS)` on representative data.

Partitioning is not a guarantee of sub-millisecond queries and does not eliminate all read/write contention. It can reduce the amount of data a query must consider and make retention operations easier, but actual performance depends on workload, hardware, partition count, query design, and indexes. Dropping an old partition can be much cheaper than deleting its rows individually, but retention and compliance requirements must be considered first.

## Partition lifecycle: the interview question

For a static demonstration, creating a few dated child partitions with SQL is fine. In production, I would not rely on someone remembering to provision each day manually. If a timestamp has no matching partition and there is no default partition, inserts for that timestamp fail.

Partition creation should be automated and observable. A scheduled maintenance process, such as a configured `pg_partman` job or an infrastructure-managed worker, can create partitions ahead of time. The schedule should provide a look-ahead buffer, report failures, and alert operators before the available partitions run out. `pg_partman` is an extension that must be installed and configured; it does not autonomously run maintenance without a scheduler or other mechanism invoking it. Exact setup depends on the deployed extension version.

A PostgreSQL default partition is an optional safety net for rows that do not fit an explicitly defined range. It keeps those inserts from failing solely because a matching partition is absent, but it is not a replacement for partition lifecycle automation: it can accumulate out-of-range data and complicate attaching a later partition if that data overlaps the new range. Monitor it and move any affected rows before creating overlapping partitions.

## How I remember the pattern

I picture a filing cabinet with a separate drawer for each day. Today's observations go into today's drawer, and a query for a known date range can focus on the relevant drawers. The drawers make the data easier to locate and manage, but they do not guarantee a particular query speed or mean that every drawer gets created without an operational process.

## Interview takeaway

I would partition the time-series parent table by the timestamp used in common queries, add a composite index that fits the node-and-time lookup pattern, and verify pruning with an execution plan. For daily partitions, I would automate pre-creation with a monitored maintenance job and create a reasonable look-ahead window. A default partition may provide a fallback, but I would monitor it and have an explicit process for draining it. I would also measure query latency and concurrency under representative conditions rather than promise sub-millisecond results from partitioning alone.

## PostgreSQL time-series partitioning blueprint

The following schema and index layout is retained from the lecture. It assumes the `market_operator` type and UUID support are already available in the database.

```sql
-- Master Time-Series Nodal Market Ticks Definition (The Virtual Routing Core)
CREATE TABLE nodal_market_ticks (
    tick_id UUID NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    market_operator market_operator NOT NULL,
    node_id VARCHAR(128) NOT NULL,
    
    -- Wholesale LMP Financial Matrix Components
    congestion_component NUMERIC(10, 2) NOT NULL,
    loss_component NUMERIC(10, 2) NOT NULL,
    energy_component NUMERIC(10, 2) NOT NULL,
    final_lmp NUMERIC(10, 2) NOT NULL, -- The summed total of all components
    
    -- Ensure the partition key column (executed_at) is explicitly mapped into the primary key composite
    PRIMARY KEY (node_id, executed_at)
) PARTITION BY RANGE (executed_at);

-- ============================================================================
-- PROVISIONING EXPLICIT INDEPENDENT DAILY STORAGE CHILD PARTITIONS
-- ============================================================================

-- Daily Partition for October 12, 2026
CREATE TABLE nodal_ticks_y2026_m10_d12 PARTITION OF nodal_market_ticks
    FOR VALUES FROM ('2026-10-12 00:00:00+00') TO ('2026-10-13 00:00:00+00');

-- Daily Partition for October 13, 2026 (Current Date Boundary Window)
CREATE TABLE nodal_ticks_y2026_m10_d13 PARTITION OF nodal_market_ticks
    FOR VALUES FROM ('2026-10-13 00:00:00+00') TO ('2026-10-14 00:00:00+00');

-- Daily Partition for October 14, 2026
CREATE TABLE nodal_ticks_y2026_m10_d14 PARTITION OF nodal_market_ticks
    FOR VALUES FROM ('2026-10-14 00:00:00+00') TO ('2026-10-15 00:00:00+00');

-- ============================================================================
-- HIGH-PERFORMANCE TIME-SERIES COMPOSITE INDEX DESIGN
-- ============================================================================

-- This composite index executes instantly on the pruned daily partition table file on disk
CREATE INDEX idx_nodal_ticks_node_time 
ON nodal_market_ticks (node_id, executed_at DESC);
```

## Automated partition lifecycle and default partition example

The default partition is optional. The `pg_partman` example is conceptual configuration from the lecture, not a complete, version-independent installation or scheduling procedure.

```sql
-- ============================================================================
-- THE PRODUCTION-GRADE AUTOMATED FAIL-SAFE INFRASTRUCTURE
-- ============================================================================

-- 1. Create the Catch-All Default Partition
-- This acts as your safety net. If midnight hits and pg_partman hasn't spun up 
-- tomorrow's table yet, the system routes data here instead of crashing the API.
CREATE TABLE nodal_ticks_default PARTITION OF nodal_market_ticks DEFAULT;

-- 2. Conceptual pg_partman Production Setup Configuration
-- This is how you instruct the database engine to manage itself automatically
-- (Executed once during infrastructure provisioning):
-- SELECT partman.create_parent(
--     p_parent_table := 'public.nodal_market_ticks',
--     p_control := 'executed_at',
--     p_type := 'native',
--     p_interval := 'daily',
--     p_premake := 7 -- Automatically builds 7 days of partitions in advance!
-- );
```

## Practical execution simulation

These examples show timestamp-based routing, a lookup against one child partition, and an execution plan for a node-and-time query. Run the plan against representative data to confirm pruning and index use in the target PostgreSQL environment.

```sql
-- 1. SIMULATING REAL-TIME FIVE-MINUTE INGESTION DATA PACKETS
-- Notice how the core engine automatically streams these into completely separate underlying daily files!
INSERT INTO nodal_market_ticks VALUES 
(uuid_generate_v4(), '2026-10-12 14:05:00+00', 'ERCOT', 'NODE_HOUSTON_SUB_4', -2.50, 1.10, 35.00, 33.60),
(uuid_generate_v4(), '2026-10-13 09:15:00+00', 'ERCOT', 'NODE_HOUSTON_SUB_4', 15.00, 1.20, 42.00, 58.20),
(uuid_generate_v4(), '2026-10-13 09:20:00+00', 'ERCOT', 'NODE_HOUSTON_SUB_4', 250.00, 1.40, 45.00, 296.40); -- Heavy congestion spike!

-- 2. VERIFY PHYSICAL TABLE ISOLATION (Querying the explicit child partition directly)
-- This proves the data did not group up into one single file on disk
SELECT count(*), AVG(final_lmp) FROM nodal_ticks_y2026_m10_d13;

-- 3. THE ANALYTICAL LOOKUP PLAN EXPLAINED (The Recruiter-Proof Verification)
-- Execute an EXPLAIN sequence to verify that Partition Pruning is active
EXPLAIN ANALYZE
SELECT executed_at, final_lmp 
FROM nodal_market_ticks 
WHERE node_id = 'NODE_HOUSTON_SUB_4' 
  AND executed_at BETWEEN '2026-10-13 00:00:00+00' AND '2026-10-13 23:59:59+00';
```

The lecture's anticipated plan output is illustrative; actual output varies with PostgreSQL version, statistics, indexes, and data volume.

```text
Result  (cost=0.15..8.30 rows=1 width=40) (actual time=0.042..0.045 rows=2 loops=1)
  ->  Index Scan using nodal_ticks_y2026_m10_d13_node_id_executed_at_idx on nodal_ticks_y2026_m10_d13  (cost=0.15..8.30 rows=1 width=40)
        Index Cond: ((node_id)::text = 'NODE_HOUSTON_SUB_4'::text) AND (executed_at >= '2026-10-13 00:00:00+00') AND (executed_at <= '2026-10-13 23:59:59+00')
```
