# Energy Ingestion Engine

A documentation-first repository for learning and evolving a distributed energy-trading ingestion architecture.

## Purpose

This repository separates conceptual learning from implementation. The documentation explains payload contracts, order-book behavior, state transitions, saga recovery, and concurrency patterns before application code is introduced.

## Repository Structure

```text
energy-ingestion-engine/
├── README.md
├── docs/
│   └── stage1_week1_fundamentals/
│       ├── day1_nodal_trade_schemas.md
│       ├── day2_redis_order_books.md
│       ├── day3_deterministic_fsm.md
│       └── day4_saga_tombstones.md
├── apps/
│   ├── ingestion-api/
│   └── post-trade-worker/
└── packages/
    ├── state-machine/
    └── shared-types/
```

## Learning Progression

1. **Day 1 — Nodal trade schemas:** Validate trade payloads, locations, delivery periods, and market-specific assumptions.
2. **Day 2 — Redis order books:** Understand sorted-set ordering, price-time priority, and atomic updates.
3. **Day 3 — Deterministic FSM:** Model post-trade checks and permitted state transitions.
4. **Day 4 — Saga and tombstones:** Coordinate asynchronous work and recover from out-of-order events.
5. **Day 5 — Optimistic locking and multi-tenant limits:** Handle concurrent credit checks with Redis transactions while keeping tenant-scoped state isolated.

## Current Stage

The first commit contains the executive blueprint and documentation only. Application code, package configuration, and implementation tests will be added in later commits.

## Scope and Assumptions

The examples are educational and are not production trading software or universal market rules. Product definitions, price ticks, time zones, settlement conventions, currencies, and regulatory requirements must be confirmed for the intended market and jurisdiction.

## Planned Workspaces

- `apps/ingestion-api`: Receives and validates trade ingestion requests.
- `apps/post-trade-worker`: Consumes accepted events and executes post-trade workflows.
- `packages/state-machine`: Contains reusable deterministic state-machine behavior.
- `packages/shared-types`: Contains shared contracts and validation types.
