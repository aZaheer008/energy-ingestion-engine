# Day 4 - 2026-09-27

### Lesson

Learned how the Saga pattern coordinates a multi-step workflow across services when one database transaction cannot cover every system. The orchestrator runs forward actions in order. If a step fails, it calls compensating actions for previously successful steps in reverse order.

A compensation is a new operation intended to counteract an earlier operation; it is not a database rollback. Each action may succeed or fail independently, so a Saga can require retries, reconciliation, or manual recovery.

### Forward and compensation flow

```text
Forward:      Reserve credit -> Allocate position -> Log compliance (fails)
Compensate:                         Deallocate position -> Cancel credit
```

Only steps that completed successfully are placed on the compensation stack. The stack is reversed so later successful actions are undone before earlier ones, usually respecting their dependencies.

### TypeScript orchestrator

```typescript
interface SagaStep {
	name: string;
	// Contract: true means the action completed; false or a rejection means failure.
	execute: () => Promise<boolean>;
	compensate: () => Promise<void>;
}

function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

export class PostTradeSagaOrchestrator {
	private tradeId: string;

	constructor(tradeId: string) {
		this.tradeId = tradeId;
	}

	public async runPipeline(steps: SagaStep[]): Promise<boolean> {
		// Keep history local to this run so reusing the orchestrator cannot roll back old steps.
		const executedSteps: SagaStep[] = [];
		console.log(`[SAGA START] Beginning post-trade pipeline for Trade: ${this.tradeId}`);

		for (const step of steps) {
			try {
				console.log(`[SAGA STEP] Executing forward action: ${step.name}...`);
				const success = await step.execute();

				if (!success) {
					throw new Error(`Step [${step.name}] reported failure.`);
				}

				// Add only confirmed successful steps; these are the actions to compensate.
				executedSteps.push(step);
			} catch (error: unknown) {
				console.error(`[SAGA FAILURE] Step [${step.name}] failed: ${errorMessage(error)}`);
				await this.triggerCompensationPipeline(executedSteps);
				return false;
			}
		}

		console.log(`[SAGA SUCCESS] All forward steps completed for Trade: ${this.tradeId}`);
		return true;
	}

	private async triggerCompensationPipeline(steps: SagaStep[]): Promise<void> {
		console.log("[COMPENSATION START] Reversing completed steps...");		
		let allCompensationsSucceeded = true;
		for (const step of [...steps].reverse()) {
			try {
				console.log(`[COMPENSATION] Reversing: ${step.name}`);
				await step.compensate();
			} catch (error: unknown) {
				allCompensationsSucceeded = false;
				console.error(`[COMPENSATION FAILURE] ${step.name}: ${errorMessage(error)}`);
			}
		}

		if (allCompensationsSucceeded) {
			console.log("[COMPENSATION COMPLETE] All completed steps were compensated.");
		} else {
			console.error("[RECOVERY INCOMPLETE] Reconciliation or manual recovery is required.");
		}
	}
}
```

The example keeps the successful-step list inside `runPipeline`, so separate runs do not share rollback history. It also continues attempting remaining compensations if one fails, but reports incomplete recovery instead of claiming the system is restored. The `boolean` result reports whether all forward steps succeeded; inspect logs or extend the result type if callers also need the compensation outcome.

### Mock failure simulation

```typescript
const CreditService = {
	reserve: async () => {
		console.log("  -> [API] Credit reserved in Redis (+$50k exposure)");
		return true;
	},
	release: async () => {
		console.log("  -> [API] Credit reservation released (-$50k exposure)");
	}
};

const PositionService = {
	allocate: async () => {
		console.log("  -> [DB] 10 MW allocated to the ERCOT_HOUSTON_HUB book");
		return true;
	},
	deallocate: async () => {
		console.log("  -> [DB] 10 MW allocation removed from the ERCOT_HOUSTON_HUB book");
	}
};

const ComplianceService = {
	logTimeout: async () => {
		throw new Error("ETRM API Gateway connection timed out (ECONNREFUSED).");
	}
};

async function runSagaFailureSimulation() {
	const orchestrator = new PostTradeSagaOrchestrator("trade-555-volatile-power-deal");
	const pipeline: SagaStep[] = [
		{
			name: "Credit Exposure Reservation",
			execute: () => CreditService.reserve(),
			compensate: () => CreditService.release()
		},
		{
			name: "Volumetric Position Allocation",
			execute: () => PositionService.allocate(),
			compensate: () => PositionService.deallocate()
		},
		{
			name: "Compliance Logging",
			execute: () => ComplianceService.logTimeout(),
			// This is safe only for this mock, where the failing action writes nothing.
			compensate: async () => {
				console.log("  -> No compliance record was written in this mock.");
			}
		}
	];

	await orchestrator.runPipeline(pipeline);
}

runSagaFailureSimulation();
```

The `$50k` exposure and `10 MW` allocation are synthetic demonstration values. A real timeout is ambiguous: the remote service may have committed an action even though the client did not receive confirmation. Production steps need idempotency and status reconciliation, and a compensation must account for possible partial completion. A no-op compensation for compliance logging is not generally safe if a log might already have been written.

### Expected output

For these mocks, the first two actions succeed, compliance logging throws, and the orchestrator compensates the completed actions in reverse order:

```text
[SAGA START] Beginning post-trade pipeline for Trade: trade-555-volatile-power-deal
[SAGA STEP] Executing forward action: Credit Exposure Reservation...
  -> [API] Credit reserved in Redis (+$50k exposure)
[SAGA STEP] Executing forward action: Volumetric Position Allocation...
  -> [DB] 10 MW allocated to the ERCOT_HOUSTON_HUB book
[SAGA STEP] Executing forward action: Compliance Logging...
[SAGA FAILURE] Step [Compliance Logging] failed: ETRM API Gateway connection timed out (ECONNREFUSED).
[COMPENSATION START] Reversing completed steps...
[COMPENSATION] Reversing: Volumetric Position Allocation
  -> [DB] 10 MW allocation removed from the ERCOT_HOUSTON_HUB book
[COMPENSATION] Reversing: Credit Exposure Reservation
  -> [API] Credit reservation released (-$50k exposure)
[COMPENSATION COMPLETE] All completed steps were compensated.
```

This output is correct only for the successful compensation mocks above. If a compensation fails, the code logs `[RECOVERY INCOMPLETE]` and continues trying the remaining compensations; it does not guarantee that all external systems have been restored.

### Side note:

A **timeout does not tell the caller whether the operation happened**. For example, the Saga sends a request to write a compliance record. The service may save the record successfully, but its response gets lost or arrives too late. The caller sees a timeout, but the record may already exist.

That uncertainty matters here: the orchestrator adds a step to its compensation list only after `execute()` reports success. If compliance logging writes the record and then times out, the step is treated as failed and isn't compensated. The Saga could release the credit and position while leaving the compliance record behind.

### Interview case study: Out-of-order credit events

#### The problem

A credit reservation command and its compensation can arrive at the Credit Service in a different order from the order in which the Saga created them. For example, `RESERVE_CREDIT` for trade `TRADE-101` is delayed, while `COMPENSATE_RELEASE` arrives first. If the service ignores the release because no reservation row exists, the delayed reserve may later debit the credit pool for a trade that was already cancelled.

#### How ordering can change

- A network delay or retry can make one message arrive later than a message produced afterward. Redelivery can also produce duplicates.
- Kafka preserves record order within a partition. Publishing a trade's events to the same topic with `tradeId` as the key helps preserve broker order for that trade. It does not create a total order across different topics, and a consumer that dispatches work concurrently can finish processing out of order unless it preserves per-trade serialization.
- Database contention can delay one worker while another transaction completes. This is a possible source of processing delay, not a guarantee that a later command will overtake an earlier one.

#### Tombstone and version strategy

Treat the cancellation as durable intent, even when no reservation row exists yet. Store a tombstone keyed by the unique `tradeId`, with the cancellation's version and a cancelled status. The tombstone is a negative record: it says this trade must not be newly reserved.

| Arrival order | Ledger behavior | Credit-pool effect |
| --- | --- | --- |
| Cancel v2 arrives first | Create a cancellation tombstone at version 2 with no allocated amount. | None; no reservation has been applied. |
| Delayed reserve v1 arrives | See the newer cancellation tombstone, record/suppress the stale reserve, and do not replace the tombstone with version 1. | None; the pool remains unchanged. |
| Reserve v1 arrives first, then cancel v2 | Reserve once; on the newer cancellation, move the row to a neutralized state and release the amount recorded on that reservation. | Debit once, then credit the same allocation once. |

Include a stable `eventId` as well as `tradeId` and a monotonically assigned per-trade version. The event ID detects redelivery of the same message; the version lets the service recognize an older command after a newer cancellation has been recorded. A timestamp is useful for audit, but should not be the ordering authority because clocks and delivery times do not establish causal order.

#### Transactional handling sketch

This is pseudocode for the required database behavior, not a drop-in implementation. The repository must make the steps inside the transaction atomic and enforce uniqueness for both the trade ID and processed event ID.

```text
BEGIN TRANSACTION
	Claim eventId once; if already processed, return without changing balances.
	Atomically create or lock the ledger entry for tradeId.

	If event is COMPENSATE_RELEASE:
		If no entry exists, write a cancelled tombstone at this event's version.
		Else if the entry is RESERVED and this event is newer:
			Release the amount stored on the reservation, not an untrusted message amount.
			Change the entry to NEUTRALIZED and store the newer version.

	If event is RESERVE_CREDIT:
		If a newer cancellation tombstone exists, record this reserve as suppressed.
			Do not debit the pool or replace the tombstone with the older version.
		Else if the event is stale or already applied, do nothing.
		Else if sufficient credit exists:
			Debit the pool and write the RESERVED ledger entry together.
		Else:
			Record the defined insufficient-credit outcome without reserving.

	Record eventId as processed in the same transaction.
COMMIT
```

Creating or locking a row must also handle the no-row-yet race: two consumers can both observe no row. Use a unique constraint with an atomic insert/upsert, a per-trade lock, or an equivalent conditional transaction, and retry serialization conflicts. A plain `findById()` followed by `save()` is not atomic.

#### Reviewing the supplied in-memory example

The example's sequential simulation illustrates the tombstone idea: cancellation version 2 creates a row without changing the $5,000,000 pool; delayed reserve version 1 sees that row and is suppressed, so the pool remains $5,000,000. But the provided `findById()`/`save()` pair has a time-of-check/time-of-use race under concurrent consumers. Its `Map` and `currentCreditPool` are also separate in-memory state, not a durable atomic ledger. It therefore demonstrates the logic but does not guarantee production concurrency safety.

In production, update the credit balance and its ledger record atomically within the authoritative credit system. If the balance and ledger live in different services or databases, use explicit coordination such as an idempotent command protocol with an outbox/inbox and reconciliation; a local database transaction cannot make two independent stores atomic. Keep tombstones for at least the maximum retry/replay window, or retain a durable version/high-water mark, so an old reserve cannot become valid after its cancellation marker is discarded.

#### Interview summary

I would preserve per-trade ordering where possible by routing events with the same `tradeId` key, but I would not rely on Kafka ordering alone. The Credit Service should be authoritative: atomically deduplicate each event, compare its version with the ledger, persist a cancellation tombstone when cancellation arrives first, and apply a reservation or release exactly once with the balance update. This handles both arrival orders and makes retries safe, while acknowledging that failed or ambiguous operations still require reconciliation.

### PostgreSQL + TypeScript reference implementation

The following reference implementation makes the concurrency boundary concrete. It assumes one Credit Service owns both the credit account balance and per-trade ledger in the same PostgreSQL database. A single database transaction can then update those records atomically. It does not make PostgreSQL, Kafka, or other services one distributed transaction.

Assumptions for this example:

- Amounts are integer US cents; `15000000` means USD 150,000. Integer minor units avoid floating-point money arithmetic.
- Each credit reservation attempt has a unique `tradeId` within an `accountId`. A cancelled attempt is terminal; a genuinely new attempt gets a new trade ID.
- The orchestrator assigns a stable `eventId` for redelivery deduplication and a strictly increasing version for each trade's events. Versions are encoded as decimal strings in JSON so JavaScript does not lose precision on large integers.
- Reserve and cancel events are commands for one reservation. A cancel event does not supply an amount to refund; the Credit Service reads the amount it actually reserved from its ledger.

#### Database schema

```sql
CREATE TABLE credit_accounts (
    account_id TEXT PRIMARY KEY,
    credit_limit_cents BIGINT NOT NULL CHECK (credit_limit_cents >= 0),
    reserved_cents BIGINT NOT NULL DEFAULT 0,
    CHECK (reserved_cents >= 0 AND reserved_cents <= credit_limit_cents)
);

CREATE TABLE credit_ledger (
    account_id TEXT NOT NULL REFERENCES credit_accounts(account_id),
    trade_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('OPEN', 'RESERVED', 'CANCELLED', 'NEUTRALIZED', 'REJECTED')
    ),
    version BIGINT NOT NULL DEFAULT 0 CHECK (version >= 0),
    reserved_cents BIGINT NOT NULL DEFAULT 0 CHECK (reserved_cents >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (account_id, trade_id),
    CHECK (
        (status = 'RESERVED' AND reserved_cents > 0)
        OR (status <> 'RESERVED' AND reserved_cents = 0)
    )
);

CREATE TABLE credit_event_receipts (
    event_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    version BIGINT NOT NULL CHECK (version > 0),
    event_type TEXT NOT NULL CHECK (event_type IN ('RESERVE', 'CANCEL')),
    amount_cents BIGINT,
    outcome TEXT NOT NULL CHECK (
        outcome IN (
            'PROCESSING', 'APPLIED', 'TOMBSTONED', 'SUPPRESSED', 'STALE',
			'INSUFFICIENT_CREDIT', 'ALREADY_RESERVED', 'ALREADY_REJECTED', 'ALREADY_TERMINAL'
        )
    ),
    processed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (account_id, trade_id, version),
    FOREIGN KEY (account_id, trade_id)
        REFERENCES credit_ledger(account_id, trade_id) ON DELETE CASCADE,
    CHECK (amount_cents IS NULL OR amount_cents > 0),
    CHECK (
        (event_type = 'RESERVE' AND amount_cents IS NOT NULL)
        OR (event_type = 'CANCEL' AND amount_cents IS NULL)
    )
);
```

`credit_ledger` has one row per account/trade, including before either command has been applied. `OPEN` is a transaction-local starting state; it must be changed before commit. The primary key prevents two durable ledger rows for the same reservation. The receipt table makes an `eventId` idempotent and rejects two different events claiming the same per-trade version. The account check prevents the aggregate reserved amount from exceeding the credit limit.

Seed an account before consuming events, for example with a USD 5,000,000 limit:

```sql
INSERT INTO credit_accounts (account_id, credit_limit_cents)
VALUES ('ercot-houston-desk', 500000000);
```

#### Event types and transaction handler

This code uses the `pg` package. PostgreSQL `BIGINT` values are read as strings by `pg`; the code converts them to `bigint` for arithmetic and sends decimal strings back to SQL. It handles both arrival orders and commits the event receipt, per-trade state, and account balance in one transaction.

```typescript
import { Pool, PoolClient } from "pg";

type CreditEvent = {
	eventId: string;
	accountId: string;
	tradeId: string;
	version: string;
} & (
	| { kind: "RESERVE"; amountCents: string }
	| { kind: "CANCEL" }
);

type LedgerStatus =
	| "OPEN"
	| "RESERVED"
	| "CANCELLED"
	| "NEUTRALIZED"
	| "REJECTED";

type EventOutcome =
	| "APPLIED"
	| "TOMBSTONED"
	| "SUPPRESSED"
	| "STALE"
	| "INSUFFICIENT_CREDIT"
	| "ALREADY_RESERVED"
	| "ALREADY_REJECTED"
	| "ALREADY_TERMINAL";

interface LedgerRow {
	status: LedgerStatus;
	version: string;
	reservedCents: string;
}

interface AccountRow {
	creditLimitCents: string;
	reservedCents: string;
}

interface ReceiptRow {
	eventId: string;
	accountId: string;
	tradeId: string;
	version: string;
	eventType: CreditEvent["kind"];
	amountCents: string | null;
	outcome: EventOutcome | "PROCESSING";
}

interface ProcessResult {
	outcome: EventOutcome;
	duplicate: boolean;
}

function validateEvent(event: CreditEvent): void {
	// Reject the event if any identity field needed to route and deduplicate it is missing.
	if (!event.eventId || !event.accountId || !event.tradeId) {
		throw new Error("eventId, accountId, and tradeId are required");
	}
	// Reject non-positive or non-integer versions before converting them to bigint.
	if (!/^[1-9][0-9]*$/.test(event.version)) {
		throw new Error("version must be a positive integer string");
	}
	// Reserve events must carry a positive integer amount in cents; cancel events have no amount.
	if (event.kind === "RESERVE" && !/^[1-9][0-9]*$/.test(event.amountCents)) {
		throw new Error("amountCents must be a positive integer string");
	}
}

function samePayload(receipt: ReceiptRow, event: CreditEvent): boolean {
	const amountCents = event.kind === "RESERVE" ? event.amountCents : null;
	return receipt.eventId === event.eventId
		&& receipt.accountId === event.accountId
		&& receipt.tradeId === event.tradeId
		&& receipt.version === event.version
		&& receipt.eventType === event.kind
		&& receipt.amountCents === amountCents;
}

function postgresErrorCode(error: unknown): string | undefined {
	// Inspect structured error objects for PostgreSQL's SQLSTATE code; other values have no code.
	if (typeof error === "object" && error !== null && "code" in error) {
		const code = (error as { code?: unknown }).code;
		return typeof code === "string" ? code : undefined;
	}
	return undefined;
}

function wait(milliseconds: number): Promise<void> {
	return new Promise<void>(resolve => setTimeout(resolve, milliseconds));
}

export async function processCreditEvent(
	pool: Pool,
	event: CreditEvent
): Promise<ProcessResult> {
	validateEvent(event);

	// Retry only transaction-level serialization/deadlock failures. Do not blindly
	// retry validation errors or conflicting event IDs/versions.
	for (let attempt = 0; attempt < 3; attempt++) {
		try {
			return await processCreditEventOnce(pool, event);
		} catch (error: unknown) {
			const code = postgresErrorCode(error);
			const retryable = code === "40001" || code === "40P01";
			// Retry serialization/deadlock errors, but propagate other errors or the final failed attempt.
			if (!retryable || attempt === 2) {
				throw error;
			}
			const backoffMs = 20 * (2 ** attempt) + Math.floor(Math.random() * 20);
			await wait(backoffMs);
		}
	}

	throw new Error("unreachable retry state");
}

async function processCreditEventOnce(
	pool: Pool,
	event: CreditEvent
): Promise<ProcessResult> {
	const client: PoolClient = await pool.connect();
	try {
		await client.query("BEGIN ISOLATION LEVEL READ COMMITTED");

		// Create the per-trade row if it is absent. The unique key makes concurrent
		// first inserts serialize; SELECT FOR UPDATE then serializes later decisions.
		await client.query(
			`INSERT INTO credit_ledger (account_id, trade_id, status, version, reserved_cents)
			 VALUES ($1, $2, 'OPEN', 0, 0)
			 ON CONFLICT (account_id, trade_id) DO NOTHING`,
			[event.accountId, event.tradeId]
		);

		const ledgerResult = await client.query<LedgerRow>(
			`SELECT status, version::text AS version,
			        reserved_cents::text AS "reservedCents"
			 FROM credit_ledger
			 WHERE account_id = $1 AND trade_id = $2
			 FOR UPDATE`,
			[event.accountId, event.tradeId]
		);
		const ledger = ledgerResult.rows[0];
		// Abort the transaction if the expected ledger row was not created or found.
		if (!ledger) {
			throw new Error("credit ledger row missing after insert/upsert");
		}

		const amountCents = event.kind === "RESERVE" ? event.amountCents : null;
		const claim = await client.query(
			`INSERT INTO credit_event_receipts
			    (event_id, account_id, trade_id, version, event_type, amount_cents, outcome)
			 VALUES ($1, $2, $3, $4, $5, $6, 'PROCESSING')
			 ON CONFLICT (event_id) DO NOTHING
			 RETURNING event_id`,
			[event.eventId, event.accountId, event.tradeId, event.version, event.kind, amountCents]
		);

		// If this event ID was already claimed, load its receipt and avoid applying its effects again.
		if (claim.rows.length === 0) {
			const priorResult = await client.query<ReceiptRow>(
				`SELECT event_id AS "eventId", account_id AS "accountId",
				        trade_id AS "tradeId", version::text AS version,
				        event_type AS "eventType", amount_cents::text AS "amountCents",
				        outcome
				 FROM credit_event_receipts
				 WHERE event_id = $1`,
				[event.eventId]
			);
			const prior = priorResult.rows[0];
			// Reject a reused event ID with a different payload instead of treating it as a duplicate.
			if (!prior || !samePayload(prior, event)) {
				throw new Error("eventId was reused with a different payload");
			}
			await client.query("COMMIT");
			return { outcome: prior.outcome as EventOutcome, duplicate: true };
		}

		const finish = async (outcome: EventOutcome): Promise<ProcessResult> => {
			await client.query(
				`UPDATE credit_event_receipts SET outcome = $2 WHERE event_id = $1`,
				[event.eventId, outcome]
			);
			await client.query("COMMIT");
			return { outcome, duplicate: false };
		};

		const incomingVersion = BigInt(event.version);
		const storedVersion = BigInt(ledger.version);
		// Mark an event at or below the ledger version stale and leave the business state unchanged.
		if (incomingVersion <= storedVersion) {
			return finish("STALE");
		}

		// Handle reservation commands separately from cancellation commands.
		if (event.kind === "RESERVE") {
			// Preserve the cancellation tombstone and suppress any later-arriving reserve command.
			if (ledger.status === "CANCELLED" || ledger.status === "NEUTRALIZED") {
				await client.query(
					`UPDATE credit_ledger SET version = $3, updated_at = clock_timestamp()
					 WHERE account_id = $1 AND trade_id = $2`,
					[event.accountId, event.tradeId, event.version]
				);
				return finish("SUPPRESSED");
			}
			// Do not debit the account again when the trade already has an active reservation.
			if (ledger.status === "RESERVED") {
				await client.query(
					`UPDATE credit_ledger SET version = $3, updated_at = clock_timestamp()
					 WHERE account_id = $1 AND trade_id = $2`,
					[event.accountId, event.tradeId, event.version]
				);
				return finish("ALREADY_RESERVED");
			}
			// Keep a credit-rejected trade terminal instead of allowing a later reserve to revive it.
			if (ledger.status === "REJECTED") {
				await client.query(
					`UPDATE credit_ledger SET version = $3, updated_at = clock_timestamp()
					 WHERE account_id = $1 AND trade_id = $2`,
					[event.accountId, event.tradeId, event.version]
				);
				return finish("ALREADY_REJECTED");
			}

			// Lock the account after the ledger row. All code paths use this lock order.
			const accountResult = await client.query<AccountRow>(
				`SELECT credit_limit_cents::text AS "creditLimitCents",
				        reserved_cents::text AS "reservedCents"
				 FROM credit_accounts WHERE account_id = $1 FOR UPDATE`,
				[event.accountId]
			);
			const account = accountResult.rows[0];
			// Fail and roll back if the requested credit account does not exist.
			if (!account) {
				throw new Error(`unknown credit account: ${event.accountId}`);
			}

			const amount = BigInt(event.amountCents);
			const reserved = BigInt(account.reservedCents);
			const limit = BigInt(account.creditLimitCents);
			// Record a terminal insufficient-credit result without changing the account balance.
			if (reserved + amount > limit) {
				await client.query(
					`UPDATE credit_ledger
					 SET status = 'REJECTED', version = $3, reserved_cents = 0,
					     updated_at = clock_timestamp()
					 WHERE account_id = $1 AND trade_id = $2`,
					[event.accountId, event.tradeId, event.version]
				);
				return finish("INSUFFICIENT_CREDIT");
			}

			await client.query(
				`UPDATE credit_accounts
				 SET reserved_cents = reserved_cents + $2
				 WHERE account_id = $1`,
				[event.accountId, amount.toString()]
			);
			await client.query(
				`UPDATE credit_ledger
				 SET status = 'RESERVED', version = $3, reserved_cents = $4,
				     updated_at = clock_timestamp()
				 WHERE account_id = $1 AND trade_id = $2`,
				[event.accountId, event.tradeId, event.version, amount.toString()]
			);
			return finish("APPLIED");
		}

		// CANCEL is a durable tombstone when no reserve has been applied yet.
		// If credit is reserved, lock its account and release the ledger's recorded allocation.
		if (ledger.status === "RESERVED") {
			const accountResult = await client.query<AccountRow>(
				`SELECT credit_limit_cents::text AS "creditLimitCents",
				        reserved_cents::text AS "reservedCents"
				 FROM credit_accounts WHERE account_id = $1 FOR UPDATE`,
				[event.accountId]
			);
			const account = accountResult.rows[0];
			// Fail and roll back if the reservation's account unexpectedly cannot be found.
			if (!account) {
				throw new Error(`unknown credit account: ${event.accountId}`);
			}

			const reserved = BigInt(account.reservedCents);
			const allocation = BigInt(ledger.reservedCents);
			// Stop rather than creating a negative account balance if ledger and account disagree.
			if (reserved < allocation) {
				throw new Error("credit ledger/account balance invariant violated");
			}
			await client.query(
				`UPDATE credit_accounts SET reserved_cents = reserved_cents - $2
				 WHERE account_id = $1`,
				[event.accountId, allocation.toString()]
			);
			await client.query(
				`UPDATE credit_ledger
				 SET status = 'NEUTRALIZED', version = $3, reserved_cents = 0,
				     updated_at = clock_timestamp()
				 WHERE account_id = $1 AND trade_id = $2`,
				[event.accountId, event.tradeId, event.version]
			);
			return finish("APPLIED");
		}

		// Create a tombstone when cancellation arrives before reservation, or after a reserve was rejected.
		if (ledger.status === "OPEN" || ledger.status === "REJECTED") {
			await client.query(
				`UPDATE credit_ledger
				 SET status = 'CANCELLED', version = $3, reserved_cents = 0,
				     updated_at = clock_timestamp()
				 WHERE account_id = $1 AND trade_id = $2`,
				[event.accountId, event.tradeId, event.version]
			);
			return finish("TOMBSTONED");
		}

		// A later cancellation of an already cancelled/neutralized reservation is a no-op.
		await client.query(
			`UPDATE credit_ledger SET version = $3, updated_at = clock_timestamp()
			 WHERE account_id = $1 AND trade_id = $2`,
			[event.accountId, event.tradeId, event.version]
		);
		return finish("ALREADY_TERMINAL");
	} catch (error: unknown) {
		// A failed COMMIT can have an ambiguous outcome. Redelivery with the same
		// eventId is safe because the receipt is committed with the balance changes.
		await client.query("ROLLBACK").catch(() => undefined);
		throw error;
	} finally {
		client.release();
	}
}
```

#### Why the handler is safe for this database boundary

- **No-row race:** the unique `(account_id, trade_id)` primary key and `INSERT ... ON CONFLICT DO NOTHING` establish one row. `SELECT ... FOR UPDATE` serializes decisions for that reservation, including the first insert race.
- **Account limit race:** reserve and cancel paths lock the ledger first and account second. The account row lock serializes reservations for different trades competing for the same credit pool. The database check constraint is a final invariant guard.
- **Duplicate delivery:** the event receipt and its result commit in the same transaction as the balance and ledger changes. A redelivery with the same `eventId` returns the recorded outcome without applying the balance change again. Reusing an ID with a different payload is rejected.
- **Out-of-order delivery:** a cancellation with a higher version creates a durable `CANCELLED` tombstone. A delayed lower-version reserve is recorded as stale and cannot debit the account. If reserve happens first, a later cancellation releases the amount stored in the ledger.
- **Serialization failures:** PostgreSQL SQLSTATE `40001` and deadlock `40P01` are retried with bounded backoff. Other errors are surfaced for the consumer's retry or dead-letter policy; a conflicting version is not silently treated as a harmless retry.
- **Atomic balance invariant:** the account total, per-trade allocation, and event receipt share one PostgreSQL transaction. This is valid only because the example puts them in the same database and authoritative service.

The event version must be assigned by a trusted producer in causal order for that trade. If versions are produced independently by multiple services, define a sequencing authority or use a richer state-transition protocol; timestamps are not a substitute. The service should acknowledge a Kafka message only after the database transaction commits. If the service must publish a follow-up Kafka event, write an outbox row in this same transaction and publish it asynchronously; consumers of that event must also be idempotent.

#### Integration-test scenarios

Run these against an isolated PostgreSQL test database with a clean test account. Assert database state, not only log output:

```typescript
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { Pool } from "pg";

async function testCancelBeforeReserve(pool: Pool): Promise<void> {
	const accountId = `test-${randomUUID()}`;
	const tradeId = randomUUID();
	await pool.query(
		`INSERT INTO credit_accounts (account_id, credit_limit_cents)
		 VALUES ($1, 500000000)`,
		[accountId]
	);

	try {
		const cancel = {
			eventId: randomUUID(), accountId, tradeId, version: "2", kind: "CANCEL"
		} as const;
		const reserve = {
			eventId: randomUUID(), accountId, tradeId, version: "1",
			kind: "RESERVE", amountCents: "15000000"
		} as const;

		assert.equal((await processCreditEvent(pool, cancel)).outcome, "TOMBSTONED");
		assert.equal((await processCreditEvent(pool, reserve)).outcome, "STALE");

		const account = await pool.query(
			`SELECT reserved_cents::text AS reserved FROM credit_accounts WHERE account_id = $1`,
			[accountId]
		);
		const ledger = await pool.query(
			`SELECT status FROM credit_ledger WHERE account_id = $1 AND trade_id = $2`,
			[accountId, tradeId]
		);
		assert.equal(account.rows[0].reserved, "0");
		assert.equal(ledger.rows[0].status, "CANCELLED");
	} finally {
		await pool.query(`DELETE FROM credit_ledger WHERE account_id = $1`, [accountId]);
		await pool.query(`DELETE FROM credit_accounts WHERE account_id = $1`, [accountId]);
	}
}

async function testConcurrentReserveAndCancel(pool: Pool): Promise<void> {
	const accountId = `test-${randomUUID()}`;
	const tradeId = randomUUID();
	await pool.query(
		`INSERT INTO credit_accounts (account_id, credit_limit_cents)
		 VALUES ($1, 500000000)`,
		[accountId]
	);

	try {
		const reserve = {
			eventId: randomUUID(), accountId, tradeId, version: "1",
			kind: "RESERVE", amountCents: "15000000"
		} as const;
		const cancel = {
			eventId: randomUUID(), accountId, tradeId, version: "2", kind: "CANCEL"
		} as const;

		await Promise.all([
			processCreditEvent(pool, reserve),
			processCreditEvent(pool, cancel)
		]);

		const account = await pool.query(
			`SELECT reserved_cents::text AS reserved FROM credit_accounts WHERE account_id = $1`,
			[accountId]
		);
		const ledger = await pool.query(
			`SELECT status, version::text AS version FROM credit_ledger
			 WHERE account_id = $1 AND trade_id = $2`,
			[accountId, tradeId]
		);
		assert.equal(account.rows[0].reserved, "0");
		assert.ok(["CANCELLED", "NEUTRALIZED"].includes(ledger.rows[0].status));
		assert.equal(ledger.rows[0].version, "2");
	} finally {
		await pool.query(`DELETE FROM credit_ledger WHERE account_id = $1`, [accountId]);
		await pool.query(`DELETE FROM credit_accounts WHERE account_id = $1`, [accountId]);
	}
}

async function testDuplicateReserveIsAppliedOnce(pool: Pool): Promise<void> {
	const accountId = `test-${randomUUID()}`;
	const tradeId = randomUUID();
	await pool.query(
		`INSERT INTO credit_accounts (account_id, credit_limit_cents)
		 VALUES ($1, 500000000)`,
		[accountId]
	);

	try {
		const reserve = {
			eventId: randomUUID(), accountId, tradeId, version: "1",
			kind: "RESERVE", amountCents: "15000000"
		} as const;
		await processCreditEvent(pool, reserve);
		const duplicate = await processCreditEvent(pool, reserve);
		assert.equal(duplicate.duplicate, true);

		const account = await pool.query(
			`SELECT reserved_cents::text AS reserved FROM credit_accounts WHERE account_id = $1`,
			[accountId]
		);
		assert.equal(account.rows[0].reserved, "15000000");
	} finally {
		await pool.query(`DELETE FROM credit_ledger WHERE account_id = $1`, [accountId]);
		await pool.query(`DELETE FROM credit_accounts WHERE account_id = $1`, [accountId]);
	}
}
```

These tests cover the late-reserve tombstone, both lock acquisition orders under concurrency, and duplicate delivery. A production test suite should also cover insufficient credit, conflicting versions, reused event IDs with different payloads, deadlock/serialization retries, database restart and broker redelivery, and recovery when a downstream side effect has an ambiguous outcome.

#### Operational boundary

This implementation is production-shaped for one service and one PostgreSQL transaction boundary; it is not a complete exchange or enterprise trading platform. Production readiness still requires managed schema migrations, authenticated and authorized messages, broker consumer-group configuration, durable retry/dead-letter handling, metrics and alerts, audit retention, key rotation, load testing, disaster recovery, and an outbox if database changes generate new messages. The credit ledger remains the authority; Kafka ordering is an optimization, not the correctness mechanism.

