const { v4: uuidv4 } = require('uuid');

exports.seed = async function(knex) {
  console.log("🚀 Initializing High-Throughput Bulk Data Ingestion Engine...");

  // Generate 10,000 simulated 5-minute market ticks across four nodes
  const totalRecords = 10000;
  const mockMarketTicks = [];
  
  const targetNodes = ['NODE_HOUSTON_SUB_1', 'NODE_HOUSTON_SUB_2', 'NODE_HOUSTON_SUB_3', 'NODE_HOUSTON_SUB_4'];
  const marketStartTime = Date.UTC(2026, 9, 13);
  
  console.log(`[PREP] Generating ${totalRecords} mock time-series data records in memory...`);
  
  for (let i = 0; i < totalRecords; i++) {
    const intervalIndex = Math.floor(i / targetNodes.length);
    const executedAt = new Date(marketStartTime + intervalIndex * 5 * 60 * 1000).toISOString();

    const baseEnergy = 35.00 + Math.sin(i / 100) * 10;
    const congestion = Math.random() > 0.95 ? 150.00 : 2.50; // Simulate volatile congestion price spikes
    const loss = 1.10;
    
    mockMarketTicks.push({
      tick_id: uuidv4(),
      executed_at: executedAt,
      market_operator: 'ERCOT',
      node_id: targetNodes[i % targetNodes.length],
      congestion_component: congestion,
      loss_component: loss,
      energy_component: baseEnergy,
      final_lmp: parseFloat((baseEnergy + congestion + loss).toFixed(2))
    });
  }

  console.log("🏁 Data generation complete. Beginning chunked database transaction processing...");

  const startTime = Date.now();
  const chunkSize = 1000; // Our optimized "shuttle bus" passenger capacity capacity

  try {
    // Execute Knex high-performance batch insertion mapping layer
    await knex.batchInsert('nodal_market_ticks', mockMarketTicks, chunkSize)
      .transacting(knex); // Run within an atomic transaction for write integrity

    const duration = (Date.now() - startTime) / 1000;
    const throughput = Math.floor(totalRecords / duration);
    console.log(`\n🟢 BULK INGESTION COMPLETED CLANLY!`);
    console.log(`- Total Records Processed: ${totalRecords}`);
    console.log(`- Execution Time: ${duration} seconds`);
    console.log(`- System Throughput Speed: ${throughput} row writes / second\n`);

  } catch (error) {
    console.error(`🚨 CRITICAL BATCH LOADER FAILURE: ${error.message}`);
    throw error;
  }
};
