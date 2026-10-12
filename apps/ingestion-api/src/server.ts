import fastify from "fastify";
import { Redis } from "ioredis";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

// Import your Day 6 immutable shared domain data contract layer
import { isPowerTradePayload } from "@energy-engine/shared-types";

// ============================================================================
// 1. COMPONENT REPLICATION FROM CONCEPTUAL ARCHITECTURE
// ============================================================================

// Day 3: The Rigid Deterministic State Machine Engine
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
// 2. SERVER ORCHESTRATION BOOTSTRAPPING
// ============================================================================
const app = fastify({ logger: true });

// Initialize connection profile targeting the Day 5/6 containerized Redis core
const redis = new Redis({ host: "127.0.0.1", port: 6379 });

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const auditLogPath = path.join(__dirname, "../../trade_audit_ledger.json_lines");

// Initialize mock corporate account balances down the network interface
app.ready(async () => {
    await redis.set("credit:limits:vitol_energy_us", "1000000"); // \$1M Risk Pool Allocation
});

// ============================================================================
// 3. THE HIGH-THROUGHPUT INGESTION ROUTE (HTTP POST)
// ============================================================================
app.post("/api/v1/trades", async (request, reply) => {
    const rawPayload = request.body;

    // STEP 1: Execute Runtime Type Guard Boundary Ingestion Check
    if (!isPowerTradePayload(rawPayload)) {
        return reply.status(400).send({
            error: "BAD_REQUEST",
            message: "Schema validation breached. Corrupt payload format structural parameters."
        });
    }

    const { tradeId, counterparty, financials } = rawPayload;
    const creditKey = `credit:limits:${counterparty.toLowerCase()}`;
    const exposureAmount = financials.volumeMW * financials.pricePerMWh;

    // Instantiate your internal state tracking machine engine wrapper loop
    const fsm = new LocalTradeStateMachine();

    // Move state forward into evaluation phase
    fsm.transition(TradeEvent.TRIGGER_CHECKS);

    // STEP 2: Execute Day 5 Atomic In-Memory Optimistic Credit Verification Check
    let transactionCommitted = false;
    await redis.watch(creditKey);

    const currentBalanceStr = await redis.get(creditKey);
    const currentBalance = currentBalanceStr ? parseFloat(currentBalanceStr) : 0;

    if (currentBalance >= exposureAmount) {
        const pipeline = redis.multi();
        pipeline.set(creditKey, (currentBalance - exposureAmount).toString());
        const execResult = await pipeline.exec();

        if (execResult !== null) {
            transactionCommitted = true;
            fsm.transition(TradeEvent.RISK_VAL_PASSED);
        }
    } else {
        await redis.unwatch();
    }

    if (!transactionCommitted) {
        fsm.transition(TradeEvent.RISK_VAL_FAILED);
        return reply.status(403).send({
            error: "LIMIT_BREACHED",
            message: `Trade ID [${tradeId}] rejected. Counterparty risk limit threshold exceeded or collision occurred.`
        });
    }

    // STEP 3: Persist Transaction to the Append-Only Audit Trail Log Ledger
    const auditRecord = {
        tradeId,
        finalState: fsm.currentState,
        timestamp: new Date().toISOString(),
        exposureProcessed: exposureAmount,
        payload: rawPayload
    };

    fs.appendFileSync(auditLogPath, JSON.stringify(auditRecord) + "\n");

    // Return the successful creation packet block to the transaction venue client
    return reply.status(201).send({
        status: "ACCEPTED",
        tradeId,
        currentState: fsm.currentState,
        remainingCredit: currentBalance - exposureAmount
    });
});

// Boot the network server listener engine thread
const startServer = async () => {
    try {
        await app.listen({ port: 3000, host: "127.0.0.1" });
        console.log("⚡ Ingestion API Gateway online and listening on port 3000...");
    } catch (err) {
        app.log.error(err);
        process.exit(1);
    }
};

startServer();
