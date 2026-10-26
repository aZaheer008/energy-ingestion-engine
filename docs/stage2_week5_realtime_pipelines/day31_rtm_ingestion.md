# Day 31 - Ingesting Real-Time Market (RTM) Streams

## Project overview

This exercise introduces a small TypeScript service for polling Real-Time Market (RTM) data. It focuses on two practical ingestion concerns: recovering from temporary upstream failures without blocking the Node.js event loop, and preserving negative locational marginal prices (LMPs) in the data.

## What we added to the code

The `RTMPollingService` provides an asynchronous polling method with up to three attempts. If a request fails, it waits before retrying. The delay grows exponentially based on the attempt number, with a small random jitter added so that clients are less likely to retry in sync. With the current 500 ms base delay, the first and second retry waits are approximately 1,000 ms and 2,000 ms, plus up to 100 ms of jitter. If the final attempt fails, the service reports an ingestion error.

The example API call is simulated: it sometimes throws a timeout and otherwise returns a few sample five-minute ticks. The payload validation converts node IDs and zones to strings and parses LMP values as numbers. Because LMPs are represented as signed numbers, a valid negative price such as `-12.75` is retained rather than rejected.

The file also includes a small command-line harness that runs the service and displays the returned ticks. This provides a simple way to observe the success and retry behavior during development.

## Practical note

This is a learning example, not a production-ready ISO connector. The upstream request and five-minute data are mocked; no live ERCOT or PJM endpoint is contacted. The current retry policy has a fixed three-attempt limit and no maximum-delay setting because the attempt count is bounded. The jitter is a random addition of up to 100 ms.

The price check rejects values that parse to `NaN`, but it does not check that the value is finite or enforce market-specific price bounds. A production ingestion boundary should validate the complete payload shape, timestamps, finite numeric values, and any rules required by the relevant market. It should also preserve useful upstream error details while avoiding accidental exposure of sensitive data.

## Interview takeaway

I would make upstream polling asynchronous so waiting for a response does not block other Node.js work. For transient failures, bounded exponential back-off with jitter spaces out retries and reduces synchronized request bursts. I would also treat market prices as signed numeric values so negative prices remain valid, while validating their format and domain-specific limits explicitly. Before production use, I would test retry behavior, set operational limits, and replace the simulated API with a properly monitored and validated ISO integration.
