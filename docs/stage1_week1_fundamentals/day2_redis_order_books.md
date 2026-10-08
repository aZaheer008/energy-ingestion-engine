# Day 2 - 2026-09-25

### Lesson

Learned how Redis sorted sets can store an order book with price-priority ordering. The bid and ask sides use separate keys, and each order is stored as a JSON string with a price-derived sorted-set score.

### Order-book keys and values

| Key or field | Value type and rules | Meaning in this example |
| --- | --- | --- |
| `market:ercot:houston_hub:bids` | Redis sorted set (ZSET) | Orders on the bid side |
| `market:ercot:houston_hub:asks` | Redis sorted set (ZSET) | Orders on the ask side |
| ZSET score | Number | Sort value; the positive bid quote of `USD 44.50` per unit is stored as score `-44.50` so higher bids sort first in ascending order. The negative score is not a negative quoted price. |
| ZSET member | JSON string | Order record containing `orderId`, `volume`, and `timestamp` |
| `orderId` | String | Identifier for an order, such as `ord_101` |
| `volume` | Number | Order quantity; `15` means 15 MW. |
| Per-unit price | Number | The bid quote is USD 44.50 per unit; the ask quote is USD 45.00 per unit. The price denominator is not specified separately in the code. |
| `timestamp` | Integer epoch milliseconds | Order time represented as milliseconds since the Unix epoch; the sample values represent UTC instants |

### Key concepts

- Redis sorted sets order members by score. `ZRANGE` reads scores in ascending order, so the most negative bid score represents the highest bid; the lowest ask price is already first in ascending order.
- The bid's `-44.50` score is an ordering trick for a positive bid quote of USD 44.50 per unit. It does not mean the buyer is offering a negative price. The order size is 15 MW and the currency is USD; the price denominator is not stated separately, so don't assume it is USD/MW or USD/MWh from this snippet alone.
- A ZSET score is a number, while the order JSON is the member. `WITHSCORES` returns the score along with the member.
- `ZRANGE ... 0 0` reads one member, so the example requests one best-priced order from each side (Level 1).
- The stored timestamp does not make this a time-priority book. If two orders have the same price score, Redis orders tied-score members lexicographically by their member strings, not by the timestamp inside the JSON.
- Individual Redis commands are atomic, but this sequence is not one atomic operation across both book writes and reads. Concurrent updates can occur between commands, so the two returned sides may not represent the same instant. A transaction or server-side Lua script can group related operations when a consistent snapshot is required.
- To implement true price-time priority, preserve an arrival sequence within each price level; a timestamp stored in JSON alone does not enforce it. Price precision or tick size also still needs to be defined.

### Code example

```javascript
// Structural mapping for the Order Book keys in Redis
const BID_BOOK_KEY = "market:ercot:houston_hub:bids";
const ASK_BOOK_KEY = "market:ercot:houston_hub:asks";

// 1. Adding a Bid: Sorted by Price (High to Low)
// Because Redis ZSETs sort ascending by default, store the bid's score as the negative
// of its positive quoted price so the highest bid sorts first.
await redis.zadd(BID_BOOK_KEY, -44.50, JSON.stringify({ orderId: "ord_101", volume: 15, timestamp: 1719878400000 }));

// 2. Adding an Ask: Sorted by Price (Low to High)
// Standard ascending sort behavior works perfectly here.
await redis.zadd(ASK_BOOK_KEY, 45.00, JSON.stringify({ orderId: "ord_102", volume: 10, timestamp: 1719878405000 }));whta

// 3. Fetching the "Best Market Depth" (Level 1)
const bestBid = await redis.zrange(BID_BOOK_KEY, 0, 0, { WITHSCORES: true }); // Top element (Highest Bid)
const bestAsk = await redis.zrange(ASK_BOOK_KEY, 0, 0, { WITHSCORES: true }); // Top element (Lowest Ask)
```

### Tick-size validation example

This example uses a hypothetical USD 0.05 tick to demonstrate validation; it is not a statement of ERCOT's tick size. Prices are represented as integer cents so the check does not depend on floating-point decimal arithmetic.

```javascript
const TICK_SIZE_CENTS = 5; // Hypothetical USD 0.05 tick

function priceToTicks(priceCents) {
	if (!Number.isInteger(priceCents) || priceCents % TICK_SIZE_CENTS !== 0) {
		throw new Error("Price is not aligned to the tick size");
	}

	return priceCents / TICK_SIZE_CENTS;
}

const bidTicks = priceToTicks(4450); // USD 44.50 becomes 890 ticks
// priceToTicks(4453) throws: USD 44.53 is not a multiple of USD 0.05
```

`4450` represents USD 44.50 in cents. Since the hypothetical tick is 5 cents, valid prices must have a cents value divisible by 5. In a real system, take the tick size from the rules for the specific market product.

### References

- [Redis sorted sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/): official Redis documentation for sorted-set scores, members, and ordering.

