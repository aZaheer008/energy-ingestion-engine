import fastify from "fastify";
import { Redis } from "ioredis";
import knex, { Knex } from "knex";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

// Import your Day 6 immutable shared domain data contract layer
import { 
    isPowerTradePayload, 
    ProductType
} from "@energy-engine/shared-types";

// ============================================================================
// 1. STATE MACHINE LIFECYCLE REPLICATION 
// ============================================================================
enum TradeState { NEW_CAPTURE = "NEW_CAPTURE", PENDING_CHECKS = "PENDING_CHECKS", POST_TRADE_VALIDATED = "POST_TRADE_VALIDATED", REJECTED = "REJECTED" }
enum TradeEvent { TRIGGER_CHECKS = "TRIGGER_CHECKS", RISK_VAL_PASSED = "RISK_VAL_PASSED", RISK_VAL_FAILED = "RISK_VAL_FAILED" }

const StateTransitionMatrix: Record<TradeState, Partial<Record<TradeEvent, TradeState>>> = {
    [TradeState.NEW_CAPTURE]: { [TradeEvent.TRIGGER_CHECKS]: TradeState.PENDING_CHECKS },
    [TradeState.PENDING_CHECKS]: { [TradeEvent.RISK_VAL_PASSED]: TradeState.POST_TRADE_VALIDATED, [TradeEvent.RISK_VAL_FAILED]: TradeState.REJECTED },
    [TradeState.POST_TRADE_VALIDATED]: {},
    [TradeState.REJECTED]: {}
};

class LocalTradeStateMachine {
    public currentState: TradeState = TradeState.NEW_CAPTURE;
    public transition(event: TradeEvent): void {
        const nextState = StateTransitionMatrix[this.currentState]?.[event];
        if (!nextState) throw new Error("INVALID_STATE_TRANSITION");
        this.currentState = nextState;
    }
}

// ============================================================================
// 2. SERVER ORCHESTRATION & CONNECTION POOLING BOOTSTRAP
// ============================================================================
const app = fastify({ logger: true });

// Initialize Redis Client
const redis = new Redis({
    host: process.env.REDIS_HOST || "127.0.0.1",
    port: parseInt(process.env.REDIS_PORT || "6379", 10)
});

// Initialize Enterprise-Grade Knex.js Database Connection Pool
const db: Knex = knex({
  client: 'postgresql',
  connection: {
    host: process.env.DB_HOST || '127.0.0.1',
    database: process.env.DB_NAME || 'energy_trading_db',
    user:     process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    port:     parseInt(process.env.DB_PORT || '5432')
  },
  pool: {
    min: 2,
    max: 10 // Safe scale concurrency pool bounds for Houston desk volume
  }
});

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const auditLogPath = path.join(__dirname, "../../trade_audit_ledger.json_lines");

app.get("/health", async (_request, reply) => {
    await Promise.all([redis.ping(), db.raw("SELECT 1")]);
    return reply.send({ status: "ok" });
});

// Warm up Redis mock risk pools on boot
app.ready(async () => {
    await redis.set("credit:limits:vitol_energy_us", "1000000"); // \$1M limit
    await redis.set("credit:limits:jpmorgan_commodities", "5000000"); // \$5M limit
});

// ============================================================================
// 3. CORE INGESTION CONTROLLER (Wired to PostgreSQL)
// ============================================================================
app.post("/api/v1/trades", async (request, reply) => {
    const rawPayload: unknown = request.body;

    // STEP 1: Execute Runtime Type Guard Check
    if (!isPowerTradePayload(rawPayload)) {
        return reply.status(400).send({
            error: "BAD_REQUEST",
            message: "Schema validation breached. Corrupt payload format structural parameters."
        });
    }

    const { tradeId, version, timestamp, traderId, bookId, counterparty, direction, product, marketOperator, financials, location } = rawPayload;
    const creditKey = `credit:limits:${counterparty.toLowerCase()}`;
    const exposureAmount = financials.volumeMW * financials.pricePerMWh;

    const fsm = new LocalTradeStateMachine();
    fsm.transition(TradeEvent.TRIGGER_CHECKS);

    // STEP 2: Atomic Redis In-Memory Credit Verification Check
    let creditVerificationPassed = false;
    await redis.watch(creditKey);

    const currentBalanceStr = await redis.get(creditKey);
    const currentBalance = currentBalanceStr ? parseFloat(currentBalanceStr) : 0;

    if (currentBalance >= exposureAmount) {
        const pipeline = redis.multi();
        pipeline.set(creditKey, (currentBalance - exposureAmount).toString());
        const execResult = await pipeline.exec();

        if (execResult !== null) {
            creditVerificationPassed = true;
            fsm.transition(TradeEvent.RISK_VAL_PASSED);
        }
    } else {
        await redis.unwatch();
    }

    if (!creditVerificationPassed) {
        fsm.transition(TradeEvent.RISK_VAL_FAILED);
        return reply.status(403).send({
            error: "LIMIT_BREACHED",
            message: `Trade ID [${tradeId}] rejected. Counterparty risk limit threshold exceeded or collision occurred.`
        });
    }

    // STEP 3: Write Directly to the Polymorphic PostgreSQL Base Ledger
    try {
        // Extract asset-specific attributes dynamically from payload to put inside the polymorphic JSONB container
        const assetAttributes = product === ProductType.PHYSICAL_POWER 
            ? { nerc_etag: `TAG-${tradeId.substring(0,8).toUpperCase()}`, substation_node: location.name, delivery_block: rawPayload.deliveryPeriod.timeOfUseBlock }
            : { settlement_index: "ERCOT_REALTIME_LMP_INDEX", margin_profile: { initial_margin: 50000, maintenance_margin: 25000 } };

        // Knex automatically grabs an available idle connection from the pre-warmed pool
        await db("trade_ledger").insert({
            trade_id: tradeId,
            version: version,
            executed_at: timestamp,
            trader_id: traderId,
            book_id: bookId,
            counterparty: counterparty,
            direction,
            product,
            market_operator: marketOperator,
            volume_mw: financials.volumeMW,
            price_per_mwh: financials.pricePerMWh,
            currency: financials.currency,
            asset_attributes: JSON.stringify(assetAttributes) // Structured Polymorphic String Serialization
        });

    } catch (dbError: unknown) {
        app.log.error(`🚨 POSTGRESQL PERSISTENCE CRASH: ${dbError instanceof Error ? dbError.message : String(dbError)}`);
        
        // Critical System Event: Revert credit pool allocations in Redis immediately to prevent lockups
        await redis.set(creditKey, (currentBalance).toString());
        
        return reply.status(500).send({
            error: "INTERNAL_SERVER_ERROR",
            message: "System data synchronization failure. Relational write aborted."
        });
    }

    // STEP 4: Append to Local Immutable Compliance File Logs
    const auditRecord = {
        tradeId,
        finalState: fsm.currentState,
        timestamp: new Date().toISOString(),
        exposureProcessed: exposureAmount
    };
    fs.appendFileSync(auditLogPath, JSON.stringify(auditRecord) + "\n");

    return reply.status(201).send({
        status: "ACCEPTED",
        tradeId,
        currentState: fsm.currentState,
        persistenceEngine: "POSTGRESQL_JSONB",
        remainingCredit: currentBalance - exposureAmount
    });
});

// Boot Server Gateway
const startServer = async () => {
    try {
        const port = parseInt(process.env.API_PORT || "3000", 10);
        const host = process.env.API_HOST || "127.0.0.1";
        await app.listen({ port, host });
        console.log(`⚡ Integrated Ingestion API Gateway online on ${host}:${port}...`);
    } catch (err) {
        app.log.error(err);
        process.exit(1);
    }
};

startServer();