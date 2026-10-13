# Day 8 - Polymorphic Schemas

## Lesson

Energy portfolios can contain trades that share basic transaction details but represent very different things. A physical power trade may need delivery and grid-routing information, while a financial swap may instead need a settlement index and margin terms. The challenge is to keep their shared data consistent without forcing unrelated fields into one rigid shape.

## Choosing a relational pattern

There are three common approaches:

- **One wide table:** Store every possible field on `trades` and leave fields empty when they do not apply. This is straightforward at first, but many nullable, type-specific columns make the model harder to validate and maintain.
- **Joined detail tables:** Keep common fields in a base table and put physical and financial details in separate tables. This gives a clear relational structure, but reading complete trades requires joins across the relevant tables.
- **Base ledger with JSONB attributes:** Store common transaction and financial fields as regular typed columns, then put asset-specific attributes in a PostgreSQL `JSONB` column. This keeps the shared ledger consistent while allowing different products to carry different details.

For the example below, the third pattern is used. It is a practical balance when product attributes vary, while common fields still need relational constraints and indexes. JSONB is not a substitute for schema design: the database constraint checks required keys, and the application should validate payload shape and values before insertion. GIN indexing can support JSONB searches such as containment queries; actual query speed depends on data, indexes, and workload and should be measured.

## How I remember the pattern

I think of the base row as a standard shipping container: each trade has the same outer structure for its identity and shared terms, while the `asset_attributes` payload holds the contents that differ by product. The container analogy is about the shared interface, not about treating the JSON as unstructured or unvalidated data.

## Interview takeaway

I would explain that I keep fields common to every trade—such as trade identity, book, counterparty, product, volume, and price—in typed relational columns. Product-specific fields live in `JSONB`, with database constraints for essential requirements and application-level validation for the full payload. Standard indexes serve common ledger filters; a GIN index supports selected JSONB searches. This avoids both a huge table of mostly irrelevant columns and a requirement to join detail tables for every read, while retaining useful integrity checks.

The right choice depends on query patterns and how stable each product's attributes are. If JSONB fields become central to reporting, require extensive relational constraints, or are frequently joined, dedicated columns or detail tables may be a better fit.

## PostgreSQL schema migration blueprint

```sql
-- Ensure database layer has UUID engine active
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Define explicit custom lookup validation states
CREATE TYPE trade_direction AS ENUM ('BUY', 'SELL');
CREATE TYPE product_type AS ENUM ('PHYSICAL_POWER', 'FINANCIAL_SWAP');
CREATE TYPE market_operator AS ENUM ('ERCOT', 'PJM', 'MISO');

-- Master Abstract Base Ledger Table Configuration
CREATE TABLE trade_ledger (
    trade_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version INT NOT NULL DEFAULT 1,
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    trader_id VARCHAR(64) NOT NULL,
    book_id VARCHAR(64) NOT NULL,
    counterparty VARCHAR(128) NOT NULL,
    direction trade_direction NOT NULL,
    product product_type NOT NULL,
    market_operator market_operator NOT NULL,
    
    -- Shared Core Financial Terms
    volume_mw NUMERIC(12, 4) NOT NULL CHECK (volume_mw > 0),
    price_per_mwh NUMERIC(12, 2) NOT NULL, -- Allows negative prices natively
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- The Polymorphic Container Asset Engine
    asset_attributes JSONB NOT NULL,
    
    -- Operational Compliance Audit Trail Layer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Strict Table Constraint: Enforce structural parameters inside the JSONB block
    CONSTRAINT enforce_asset_integrity CHECK (
        (product = 'PHYSICAL_POWER' AND asset_attributes ? 'nerc_etag' AND asset_attributes ? 'substation_node') OR
        (product = 'FINANCIAL_SWAP' AND asset_attributes ? 'settlement_index' AND asset_attributes ? 'margin_profile')
    )
);

-- ============================================================================
-- HIGH-PERFORMANCE INDEXING ENGINE LAYOUT
-- ============================================================================

-- B-Tree Indexes for fast primary column filtering and ledger lookups
CREATE INDEX idx_trade_ledger_book ON trade_ledger(book_id);
CREATE INDEX idx_trade_ledger_counterparty ON trade_ledger(counterparty);
CREATE INDEX idx_trade_ledger_executed ON trade_ledger(executed_at DESC);

-- GIN (Generalized Inverted Index) over JSONB for deep attribute search
CREATE INDEX idx_trade_ledger_asset_attrs ON trade_ledger USING GIN (asset_attributes);
```

## Practical execution simulation

The examples insert a physical power trade and a financial swap into the same ledger table. Each row shares the same core columns, while the product-specific JSONB payload carries the required attributes. The final query uses JSONB containment to find a trade for a particular substation node.

```sql
-- 1. INSERTING A PHYSICAL POWER TRADE PAYLOAD (Requires NERC E-Tag and Node)
INSERT INTO trade_ledger (
    executed_at, trader_id, book_id, counterparty, direction, product, market_operator, volume_mw, price_per_mwh, asset_attributes
) VALUES (
    NOW(), 'trader_houston_1', 'book_ercot_peak', 'Vitol_Energy_US', 'BUY', 'PHYSICAL_POWER', 'ERCOT', 
    10.0000, 45.50, 
    '{"nerc_etag": "TX-20261012-99812-E", "substation_node": "SUB_WEST_HOUSTON_4", "delivery_block": "ON_PEAK"}'::jsonb
);

-- 2. INSERTING A FINANCIAL SWAP PAYLOAD (Requires Settlement Index and Margin Profile)
INSERT INTO trade_ledger (
    executed_at, trader_id, book_id, counterparty, direction, product, market_operator, volume_mw, price_per_mwh, asset_attributes
) VALUES (
    NOW(), 'trader_houston_1', 'book_hedges', 'JPMorgan_Commodities', 'SELL', 'FINANCIAL_SWAP', 'ERCOT', 
    25.0000, -12.00, -- Simulating handling a negative price hedge state
    '{"settlement_index": "ERCOT_REALTIME_LMP_INDEX", "margin_profile": {"initial_margin": 50000, "maintenance_margin": 25000}}'::jsonb
);

-- 3. TEST HIGH-SPEED GIN QUERY: Fetch only trades matching a specific substation node inside JSONB
SELECT trade_id, product, volume_mw, asset_attributes->>'substation_node' as node
FROM trade_ledger
WHERE asset_attributes @> '{"substation_node": "SUB_WEST_HOUSTON_4"}';
```
