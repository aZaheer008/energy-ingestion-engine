# Day 5 - 2026-10-08

## Lesson

Optimistic locking lets concurrent workers read a shared value without holding a distributed mutex. Each worker watches the value, performs validation, and then attempts to commit a change atomically. Redis rejects the transaction if another client changes the watched key before `EXEC`.

This is an excellent fit for a short-lived credit-pool check, but it is not a complete credit system. The Redis key is a cache or concurrency guard; an authoritative ledger, idempotency, reconciliation, and product-specific controls still belong in the owning service.

## The concurrency choice

### Pessimistic locking

A pessimistic lock protects the whole row or resource for the duration of the operation:

1. Acquire a lock.
2. Read the balance.
3. Validate the exposure.
4. Update the balance.
5. Release the lock.

This is simple and gives strong serialization, but every worker may wait. During a market event, a long validation or database call can create queueing, timeouts, and backpressure.

### Optimistic locking

Optimistic locking allows workers to proceed concurrently:

1. Watch the shared key.
2. Read the current value.
3. Validate the exposure.
4. Queue the update with `MULTI`.
5. Execute the transaction with `EXEC`.
6. Retry if the watched key changed.

Redis validates the watch condition at commit time. A failed `EXEC` returns `null`; the transaction is discarded and no partial update occurs.

> Optimistic locking does not make a shared resource safe by itself. The application must watch every value that participates in the decision and must retry safely.

## Redis primitives

- `WATCH key` monitors the key for changes.
- `MULTI` queues commands but does not execute them.
- `EXEC` applies the queued commands only when all watched keys are unchanged.
- `null` from `EXEC` means the watched key changed; the queued commands were not applied.
- `UNWATCH` releases the watch state when the transaction is abandoned or an error occurs.

A watched key is not an application lock. It is a version check performed at commit time.

## Integer money and tenant isolation

The example uses integer minor units. One USD unit equals `100` minor units, so `1,000,000` USD is `100000000` minor units. This avoids binary floating-point rounding in financial accounting.

A key should include both the tenant and the protected resource:

```text
credit:limits:{tenantId}:{counterpartyId}
```

The tenant identifier must be part of the key and must not be inferred from a shared Redis connection. A Redis key is not a tenant authorization boundary; the caller still needs permission to operate on the tenant.

## TypeScript architecture pattern

The following implementation is an educational reference. It uses a Redis key as a concurrency guard and returns a typed result instead of relying on a boolean alone.

```typescript
import Redis from "ioredis";

export type CreditDecision =
	| { kind: "accepted"; remainingMinorUnits: bigint }
	| { kind: "insufficient-funds"; balanceMinorUnits: bigint }
	| { kind: "conflict" }
	| { kind: "retries-exhausted" };

export interface CreditValidationOptions {
	maxRetries?: number;
	initialBackoffMs?: number;
	maxBackoffMs?: number;
}

export class ResilientCreditValidationEngine {
	private readonly redis: Redis;
	private readonly maxRetries: number;
	private readonly initialBackoffMs: number;
	private readonly maxBackoffMs: number;

	constructor(redis: Redis, options: CreditValidationOptions = {}) {
		this.redis = redis;
		this.maxRetries = options.maxRetries ?? 3;
		this.initialBackoffMs = options.initialBackoffMs ?? 25;
		this.maxBackoffMs = options.maxBackoffMs ?? 500;
	}

	public async validateAndDeductCredit(
		tenantId: string,
		counterpartyId: string,
		exposureMinorUnits: bigint,
	): Promise<CreditDecision> {
		if (exposureMinorUnits <= 0n) {
			throw new Error("Exposure must be greater than zero.");
		}

		const creditKey = `credit:limits:${tenantId}:${counterpartyId}`;
		let backoffMs = this.initialBackoffMs;

		for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
			await this.redis.watch(creditKey);

			try {
				const balanceText = await this.redis.get(creditKey);
				const balanceMinorUnits = balanceText === null
					? 0n
					: this.parseMinorUnits(balanceText, creditKey);

				if (balanceMinorUnits < exposureMinorUnits) {
					await this.redis.unwatch();
					return {
						kind: "insufficient-funds",
						balanceMinorUnits,
					};
				}

				const remainingMinorUnits = balanceMinorUnits - exposureMinorUnits;
				const transaction = this.redis.multi();
				transaction.set(creditKey, remainingMinorUnits.toString());

				const result = await transaction.exec();
				if (result === null) {
					console.warn(
						`[credit] Conflict for ${creditKey}; retrying attempt ${attempt}/${this.maxRetries}`,
					);
					await this.sleep(backoffMs);
					backoffMs = Math.min(backoffMs * 2, this.maxBackoffMs);
					continue;
				}

				return {
					kind: "accepted",
					remainingMinorUnits,
				};
			} catch (error) {
				await this.redis.unwatch();
				throw error;
			} finally {
				// A successful EXEC has already completed the transaction.
				// The explicit UNWATCH above is retained for failure paths and callers that
				// need to release state before an exception is propagated.
				if (this.redis.isOpen()) {
					await this.redis.unwatch();
				}
			}
		}

		return { kind: "retries-exhausted" };
	}

	private parseMinorUnits(value: string, key: string): bigint {
		if (!/^\d+$/.test(value)) {
			throw new Error(`Invalid minor-unit balance for Redis key ${key}: ${value}`);
		}

		return BigInt(value);
	}

	private sleep(milliseconds: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, milliseconds));
	}
}
```

The implementation has several important properties:

- It rejects non-positive exposure values before touching Redis.
- It stores money as an exact integer, not a floating-point number.
- It uses an isolated key per tenant and counterparty.
- It retries only after a watch conflict or infrastructure error is handled by the caller.
- It releases the watch state after every attempt.
- It returns a conflict result rather than treating a transaction collision as a successful debit.

The `finally` block calls `UNWATCH` even after a successful `EXEC`. Calling it after a committed transaction is harmless, but the code should be reviewed against the exact `ioredis` behavior for the deployed version.

## Important correctness boundaries

### Watch the complete decision set

Watching only the balance is sufficient only when the balance is the sole condition and the update is a single atomic change. If the decision also depends on a rate, limit, account status, product, or version, those values must be watched or the decision must be enforced in the authoritative database transaction.

### Retry with an idempotent operation

A retry must not create a second credit event if the first transaction committed but the caller did not receive the response. The service should use a stable trade or event identifier and an idempotency record or durable ledger entry.

### Keep Redis as a concurrency guard, not the source of truth

A Redis key can be lost, restarted, or changed by another service. The authoritative service should persist the balance mutation and event receipt in a database. Redis can then be used for a fast check, a distributed lock, or a consistency guard, but the durable ledger must define reconciliation and repair.

### Multi-tenant isolation

Use tenant-scoped keys and enforce authorization before calling the service. Also define:

- Which tenant owns a counterparty.
- Which counterparty may draw from which pool.
- How products and currencies are separated.
- How a failed or unknown tenant is handled.
- How key names remain valid across Redis deployments and key prefixes.

A shared counterparty pool should not be represented by a single global key unless the business rules explicitly require one.

## Collision simulation

The next example shows the behavior at a conceptual level. It uses two independent Redis clients and deliberately changes the watched key between the two workers' reads and commits.

```typescript
import Redis from "ioredis";

async function runOptimisticLockSimulation(): Promise<void> {
	const redis = new Redis({ host: "127.0.0.1", port: 6379 });
	const workerA = new Redis({ host: "127.0.0.1", port: 6379 });
	const workerB = new Redis({ host: "127.0.0.1", port: 6379 });
	const engineA = new ResilientCreditValidationEngine(workerA);
	const engineB = new ResilientCreditValidationEngine(workerB);
	const key = "credit:limits:tenant-a:counterparty-a";

	await redis.set(key, "100000000");

	const [resultA, resultB] = await Promise.all([
		engineA.validateAndDeductCredit("tenant-a", "counterparty-a", 20_000_000n),
		engineB.validateAndDeductCredit("tenant-a", "counterparty-a", 30_000_000n),
	]);

	console.log(resultA);
	console.log(resultB);
	console.log(`Final balance: ${await redis.get(key)}`);

	await redis.quit();
	await workerA.quit();
	await workerB.quit();
}

runOptimisticLockSimulation();
```

This simulation is not deterministic because two concurrent workers may complete in a favorable order. For a deterministic test, use a controlled test hook or a lower-level transaction test that records the watch/read/commit sequence. Do not add a production hook solely to make a test deterministic; place the test in a support module or use an integration test with a controllable Redis proxy.

The expected behavior is one accepted debit and one conflict retry. The retry may then succeed only if the current balance still permits the second exposure. The final balance is the result of the accepted commit, not the sum of both attempts.

## Simulated output

The exact order of output may vary. A possible outcome is:

```text
{ kind: "accepted", remainingMinorUnits: 80000000n }
{ kind: "accepted", remainingMinorUnits: 50000000n }
Final balance: 50000000
```

The first transaction may win and the second may retry. The second result could also be `insufficient-funds` if the newer balance cannot cover its exposure. A retry is valid only when the current balance still satisfies the decision.

## Production rollout checklist

Before using this pattern in a production credit service:

1. Define the authoritative source of truth and the reconciliation mechanism.
2. Use a stable, unique operation identifier for idempotency.
3. Validate exposure, currency, tenant, counterparty, and product rules.
4. Watch all fields that affect the decision.
5. Persist each accepted debit in a durable ledger.
6. Add transaction-conflict retry tests and a bounded retry policy.
7. Define maximum contention, retry limits, and operational alerts.
8. Add dead-letter or manual-recovery handling for exhausted retries.
9. Verify that Redis failures do not falsely report a committed debit.
10. Test multi-tenant key isolation and authorization boundaries.

## Key takeaway

Optimistic locking is a low-contention concurrency control that makes a conflict visible at commit time. It avoids holding a lock across a long validation period, but it is not a substitute for durable accounting, idempotency, authorization, or reconciliation.

The educational pattern is safe only when the watched key represents the complete protected decision and the application handles conflict and retry outcomes correctly.
