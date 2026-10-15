exports.up = async function(knex) {
  // 1. Initialize custom enums natively in PostgreSQL using raw drivers
  await knex.raw(`CREATE TYPE trade_direction AS ENUM ('BUY', 'SELL');`);
  await knex.raw(`CREATE TYPE product_type AS ENUM ('PHYSICAL_POWER', 'FINANCIAL_SWAP');`);
  await knex.raw(`CREATE TYPE market_operator AS ENUM ('ERCOT', 'PJM', 'MISO');`);

  // 2. Build the Polymorphic Master Trade Ledger
  await knex.schema.createTable('trade_ledger', (table) => {
    table.uuid('trade_id').primary().defaultTo(knex.raw('gen_random_uuid()'));
    table.integer('version').notNullable().defaultTo(1);
    table.timestamp('executed_at', { useTz: true }).notNullable();
    table.string('trader_id', 64).notNullable();
    table.string('book_id', 64).notNullable();
    table.string('counterparty', 128).notNullable();
    
    // Wire custom raw enums safely to tracking columns
    table.specificType('direction', 'trade_direction').notNullable();
    table.specificType('product', 'product_type').notNullable();
    table.specificType('market_operator', 'market_operator').notNullable();

    table.decimal('volume_mw', 12, 4).notNullable();
    table.decimal('price_per_mwh', 12, 2).notNullable();
    table.string('currency', 3).notNullable().defaultTo('USD');
    
    // The polymorphic JSONB document container asset storage engine
    table.jsonb('asset_attributes').notNullable();
    table.timestamp('created_at', { useTz: true }).defaultTo(knex.fn.now());

    // Indexes for high-speed metadata lookups
    table.index(['book_id'], 'idx_trade_ledger_book');
    table.index(['counterparty'], 'idx_trade_ledger_counterparty');
  });

  // Inject structural check constraints and GIN indexes over the ledger
 await knex.raw(`
  ALTER TABLE trade_ledger ADD CONSTRAINT enforce_asset_integrity CHECK (
    (product = 'PHYSICAL_POWER'
      AND jsonb_exists(asset_attributes, 'nerc_etag')
      AND jsonb_exists(asset_attributes, 'substation_node')) OR
    (product = 'FINANCIAL_SWAP'
      AND jsonb_exists(asset_attributes, 'settlement_index')
      AND jsonb_exists(asset_attributes, 'margin_profile'))
  );
`);
  await knex.raw(`CREATE INDEX idx_trade_ledger_asset_attrs ON trade_ledger USING GIN (asset_attributes);`);

  // 3. Build the Time-Series Nodal Market Ticks Table with partitioning
  // Standard knex schema generation lacks range partitioning definitions, so we execute via raw commands
  await knex.raw(`
    CREATE TABLE nodal_market_ticks (
        tick_id UUID NOT NULL,
        executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
        market_operator market_operator NOT NULL,
        node_id VARCHAR(128) NOT NULL,
        congestion_component NUMERIC(10, 2) NOT NULL,
        loss_component NUMERIC(10, 2) NOT NULL,
        energy_component NUMERIC(10, 2) NOT NULL,
        final_lmp NUMERIC(10, 2) NOT NULL,
        PRIMARY KEY (node_id, executed_at)
    ) PARTITION BY RANGE (executed_at);
  `);

  // Provision the Fail-Safe Default Partition
  await knex.raw(`CREATE TABLE nodal_ticks_default PARTITION OF nodal_market_ticks DEFAULT;`);
  
  // Provision a baseline current daily table partition chunk to support immediate local testing
  await knex.raw(`
    CREATE TABLE nodal_ticks_y2026_m10_d13 PARTITION OF nodal_market_ticks
    FOR VALUES FROM ('2026-10-13 00:00:00+00') TO ('2026-10-14 00:00:00+00');
  `);

  // Build the time-series composite speed index
  await knex.raw(`CREATE INDEX idx_nodal_ticks_node_time ON nodal_market_ticks (node_id, executed_at DESC);`);
};

exports.down = async function(knex) {
  // Gracefully dismantle infrastructure in strict reverse order to respect dependency constraints
  await knex.schema.dropTableIfExists('nodal_market_ticks');
  await knex.schema.dropTableIfExists('trade_ledger');
  
  await knex.raw(`DROP TYPE IF EXISTS market_operator;`);
  await knex.raw(`DROP TYPE IF EXISTS product_type;`);
  await knex.raw(`DROP TYPE IF EXISTS trade_direction;`);
};
