# Day 3 - 2026-09-26

### Lesson

Learned how a post-trade check pipeline can be modeled as a deterministic state machine. After a trade is captured, only explicitly allowed events may move it through validation and settlement. A failed risk check rejects the trade; an event that is not allowed in the current state is rejected without changing the state.

The lesson calls this example the "Trafigura Pattern." Treat that as the name used for this educational example, not as a claim that every company or market follows the same internal workflow.

### Lifecycle diagram

```text
[NEW_CAPTURE]
	  |
	  | TRIGGER_CHECKS
	  v
[PENDING_CHECKS] -- RISK_VAL_FAILED --> [REJECTED] (terminal)
	  |
	  | RISK_VAL_PASSED
	  v
[POST_TRADE_VALIDATED]
	  |
	  | COUNTERPARTY_AFFIRMED
	  v
[AFFIRMED]
	  |
	  | CLEARINGHOUSE_SETTLED
	  v
[SETTLED] (terminal)
```

### Key concepts

- A **state** describes where the trade is in its lifecycle. An **event** requests a transition from the current state.
- The transition matrix is an allowlist: if a state/event pair is absent, the engine throws an error and leaves the current state unchanged.
- `REJECTED` and `SETTLED` have no outgoing transitions in the supplied matrix, so they are terminal states in this example.
- This state machine controls lifecycle sequencing; it does not perform risk calculations, contact a counterparty, or settle a trade. External services would need to perform those tasks and emit trusted events.
- The example is an in-memory demonstration. Production systems also need durable state, audit/event history, duplicate-event handling, access controls, and carefully designed concurrency and recovery behavior.

### Important consistency check

The TypeScript implementation below includes the diagram's `AFFIRMED` state and `COUNTERPARTY_AFFIRMED` event. It requires counterparty affirmation after risk validation and before clearinghouse settlement, matching the lifecycle shown above.

The error message says "Transaction locked," but the code does not lock a database or distributed trade record. It throws before mutating this in-memory object's state when the transition is invalid.

### TypeScript state-machine example

```typescript
export enum TradeState {
	NEW_CAPTURE = "NEW_CAPTURE",
	PENDING_CHECKS = "PENDING_CHECKS",
	POST_TRADE_VALIDATED = "POST_TRADE_VALIDATED",
	AFFIRMED = "AFFIRMED",
	REJECTED = "REJECTED",
	SETTLED = "SETTLED"
}

export enum TradeEvent {
	TRIGGER_CHECKS = "TRIGGER_CHECKS",
	RISK_VAL_PASSED = "RISK_VAL_PASSED",
	RISK_VAL_FAILED = "RISK_VAL_FAILED",
	COUNTERPARTY_AFFIRMED = "COUNTERPARTY_AFFIRMED",
	CLEARINGHOUSE_SETTLED = "CLEARINGHOUSE_SETTLED"
}

const StateTransitionMatrix: Record<TradeState, Partial<Record<TradeEvent, TradeState>>> = {
	[TradeState.NEW_CAPTURE]: {
		[TradeEvent.TRIGGER_CHECKS]: TradeState.PENDING_CHECKS
	},
	[TradeState.PENDING_CHECKS]: {
		[TradeEvent.RISK_VAL_PASSED]: TradeState.POST_TRADE_VALIDATED,
		[TradeEvent.RISK_VAL_FAILED]: TradeState.REJECTED
	},
	[TradeState.POST_TRADE_VALIDATED]: {
		[TradeEvent.COUNTERPARTY_AFFIRMED]: TradeState.AFFIRMED
	},
	[TradeState.AFFIRMED]: {
		[TradeEvent.CLEARINGHOUSE_SETTLED]: TradeState.SETTLED
	},
	[TradeState.REJECTED]: {},
	[TradeState.SETTLED]: {}
};

export class TradeStateMachine {
	private currentState: TradeState;
	private tradeId: string;

	constructor(tradeId: string, initialState: TradeState = TradeState.NEW_CAPTURE) {
		this.tradeId = tradeId;
		this.currentState = initialState;
	}

	public getStatus(): TradeState {
		return this.currentState;
	}

	public transition(event: TradeEvent): TradeState {
		const nextState = StateTransitionMatrix[this.currentState]?.[event];

		if (!nextState) {
			throw new Error(
				`CRITICAL SYSTEM FAILURE: Invalid trade transition attempted on Trade [${this.tradeId}]. ` +
				`Cannot execute Event [${event}] while in State [${this.currentState}]. Transaction locked.`
			);
		}

		this.currentState = nextState;
		return this.currentState;
	}
}
```

The `Record` type makes the matrix provide an entry for every declared state. `Partial<Record<TradeEvent, TradeState>>` allows each state's event map to contain only the events that are valid there. The runtime check still matters: it handles invalid state/event combinations when the program runs.

### Simulation example

```typescript
import { TradeStateMachine, TradeState, TradeEvent } from "./TradeStateMachine";

function runSuccessfulTradeSimulation() {
	console.log("--- STARTING SCENARIO 1: HAPPY PATH ---");

	const ercotTradeId = "uuid-9999-ercot-physical-peak";
	const tradeEngine = new TradeStateMachine(ercotTradeId, TradeState.NEW_CAPTURE);
	console.log(`[INIT] Trade ${ercotTradeId} spawned. Current Status: ${tradeEngine.getStatus()}`);

	tradeEngine.transition(TradeEvent.TRIGGER_CHECKS);
	console.log(`[TRANSITION] Verification triggered. Current Status: ${tradeEngine.getStatus()}`);

	tradeEngine.transition(TradeEvent.RISK_VAL_PASSED);
	console.log(`[TRANSITION] Risk validation passed. Current Status: ${tradeEngine.getStatus()}`);

	tradeEngine.transition(TradeEvent.COUNTERPARTY_AFFIRMED);
	console.log(`[TRANSITION] Counterparty affirmed. Current Status: ${tradeEngine.getStatus()}`);

	tradeEngine.transition(TradeEvent.CLEARINGHOUSE_SETTLED);
	console.log(`[TERMINAL] Account cleared. Current Status: ${tradeEngine.getStatus()}`);

	console.log("SCENARIO 1 COMPLETED: Trade safely settled with zero errors.\n");
}

function runBypassedCheckSimulation() {
	console.log("--- STARTING SCENARIO 2: REJECTING ILLEGAL SKIP ---");

	const highRiskTradeId = "uuid-1111-rogue-algorithmic-deal";
	const tradeEngine = new TradeStateMachine(highRiskTradeId, TradeState.NEW_CAPTURE);
	console.log(`[INIT] Trade ${highRiskTradeId} spawned. Current Status: ${tradeEngine.getStatus()}`);

	tradeEngine.transition(TradeEvent.TRIGGER_CHECKS);
	console.log(`[TRANSITION] Verification triggered. Current Status: ${tradeEngine.getStatus()}`);

	try {
		console.log("[ALERT] Late worker attempts CLEARINGHOUSE_SETTLED directly...");
		tradeEngine.transition(TradeEvent.CLEARINGHOUSE_SETTLED);
	} catch (error: unknown) {
		const message = error instanceof Error ? error.message : String(error);
		console.error("TRANSACTION ABORTED BY STATE-MACHINE CHECK");
		console.error(`Reason: ${message}`);
	}

	console.log(`[CHECK] Trade remains at status: ${tradeEngine.getStatus()}`);
	console.log("SCENARIO 2 COMPLETED: Invalid transition was rejected.\n");
}

runSuccessfulTradeSimulation();
runBypassedCheckSimulation();
```

### Expected behavior

In the happy path, the implementation transitions through `NEW_CAPTURE`, `PENDING_CHECKS`, `POST_TRADE_VALIDATED`, `AFFIRMED`, and finally `SETTLED`. `CLEARINGHOUSE_SETTLED` is invalid before counterparty affirmation.

In the violation path, `CLEARINGHOUSE_SETTLED` is not allowed while the trade is `PENDING_CHECKS`. The method throws an error before assigning a new state, so `getStatus()` still returns `PENDING_CHECKS`.

### Simulation output

The originally supplied logs were from the earlier version: they omitted the counterparty affirmation step and used messages that are no longer in the simulation. This corrected output matches the current code. It demonstrates state transitions only; it does not perform real risk validation, clearing, alerting, or distributed transaction locking.

```text
--- STARTING SCENARIO 1: HAPPY PATH ---
[INIT] Trade uuid-9999-ercot-physical-peak spawned. Current Status: NEW_CAPTURE
[TRANSITION] Verification triggered. Current Status: PENDING_CHECKS
[TRANSITION] Risk validation passed. Current Status: POST_TRADE_VALIDATED
[TRANSITION] Counterparty affirmed. Current Status: AFFIRMED
[TERMINAL] Account cleared. Current Status: SETTLED
SCENARIO 1 COMPLETED: Trade safely settled with zero errors.

--- STARTING SCENARIO 2: REJECTING ILLEGAL SKIP ---
[INIT] Trade uuid-1111-rogue-algorithmic-deal spawned. Current Status: NEW_CAPTURE
[TRANSITION] Verification triggered. Current Status: PENDING_CHECKS
[ALERT] Late worker attempts CLEARINGHOUSE_SETTLED directly...
TRANSACTION ABORTED BY STATE-MACHINE CHECK
Reason: CRITICAL SYSTEM FAILURE: Invalid trade transition attempted on Trade [uuid-1111-rogue-algorithmic-deal]. Cannot execute Event [CLEARINGHOUSE_SETTLED] while in State [PENDING_CHECKS]. Transaction locked.
[CHECK] Trade remains at status: PENDING_CHECKS
SCENARIO 2 COMPLETED: Invalid transition was rejected.
```

