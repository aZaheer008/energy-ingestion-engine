# Day 1 - 2026-09-24

### Lesson

Learned how to read a JSON Schema for a power-trade record. A schema describes the shape and validation rules for data; it is not itself a trade or a market-data feed.

### Top-level keys

| Key | Value type and rules | Meaning in this schema |
| --- | --- | --- |
| `tradeId` | String formatted as a UUID | Unique trade identifier |
| `version` | Integer, minimum `1` | Trade version for amendments and audit history |
| `timestamp` | Date-time string | Execution time; the description specifies UTC |
| `traderId` | String | Trader, desk agent, or automated process identifier |
| `bookId` | String | Portfolio or risk-book identifier |
| `counterparty` | String | Legal name of the other party |
| `direction` | String: `BUY` or `SELL` | Trade direction |
| `product` | String: `PHYSICAL_POWER` or `FINANCIAL_SWAP` | Product category |
| `marketOperator` | String: `ERCOT`, `PJM`, or `MISO` | Market operator associated with the trade |
| `location` | Object; requires `type` and `name` | Delivery location |
| `deliveryPeriod` | Object; requires `startTime`, `endTime`, and `timeOfUseBlock` | Delivery interval and peak classification |
| `financials` | Object; requires `volumeMW`, `pricePerMWh`, and `currency` | Trade volume and price details |

All 12 top-level keys above are listed in the schema's `required` array.

### Nested fields and value types

- `location.type`: string, either `HUB` or `NODE`.
- `location.name`: string. The example `ERCOT_HOUSTON_HUB` is descriptive only; the schema does not enumerate or validate actual ERCOT locations.
- `deliveryPeriod.startTime` and `deliveryPeriod.endTime`: date-time strings.
- `deliveryPeriod.timeOfUseBlock`: string, either `ON_PEAK` or `OFF_PEAK`.
- `financials.volumeMW`: number with a minimum of `0.1` MW.
- `financials.pricePerMWh`: number; negative values are permitted by the schema. Together with the `USD` currency field, the intended unit is USD/MWh.
- `financials.currency`: string, currently restricted to `USD`.
- Delivery intervals are five minutes for this lesson. The schema stores `startTime` and `endTime`, but does not itself enforce five-minute boundaries or include a separate interval-length field.
- Use the time zone applicable to the ERCOT delivery territory for delivery-period times, and include an explicit offset when representing date-time values. The schema describes the trade execution `timestamp` as UTC; keep that separate from delivery-period time handling.

### Key concepts

- `required` makes a key mandatory; `properties` describes its expected type and constraints.
- Enums restrict a string to a known set of values. Numeric minimums restrict the allowed range.
- The schema is named `US_Physical_Power_Trade` and allows ERCOT, PJM, and MISO, so it is a multi-operator trade-record schema, not an ERCOT-only schema.
- It describes categories such as physical power and financial swaps, but does not define the detailed scheduling, settlement, or market rules for those products.
- It does not set `additionalProperties` to `false`, so extra fields are not explicitly prohibited by this schema.

### References

- [ERCOT API Explorer](https://apiexplorer.ercot.com/): official site for exploring ERCOT APIs.

### Complete schema

```json
{
	"$schema": "http://json-schema.org",
	"title": "US_Physical_Power_Trade",
	"type": "object",
	"required": [
		"tradeId",
		"version",
		"timestamp",
		"traderId",
		"bookId",
		"counterparty",
		"direction",
		"product",
		"marketOperator",
		"location",
		"deliveryPeriod",
		"financials"
	],
	"properties": {
		"tradeId": {
			"type": "string",
			"format": "uuid",
			"description": "Unique immutable identifier for the transaction tracking lifecycle."
		},
		"version": {
			"type": "integer",
			"minimum": 1,
			"description": "Incremental version code to handle regulatory audit trails on amendments."
		},
		"timestamp": {
			"type": "string",
			"format": "date-time",
			"description": "UTC timestamp of exact transaction execution."
		},
		"traderId": {
			"type": "string",
			"description": "Identifier of execution desk agent or automated python script."
		},
		"bookId": {
			"type": "string",
			"description": "Logical portfolio bucket tracking shared risk aggregations."
		},
		"counterparty": {
			"type": "string",
			"description": "Validated corporate entity legal name on the opposite ledger."
		},
		"direction": {
			"type": "string",
			"enum": ["BUY", "SELL"]
		},
		"product": {
			"type": "string",
			"enum": ["PHYSICAL_POWER", "FINANCIAL_SWAP"],
			"description": "Determines downstream physical scheduling pipelines vs cash settlement."
		},
		"marketOperator": {
			"type": "string",
			"enum": ["ERCOT", "PJM", "MISO"],
			"description": "The specific regional market clearing boundary rules to execute against."
		},
		"location": {
			"type": "object",
			"required": ["type", "name"],
			"properties": {
				"type": {
					"type": "string",
					"enum": ["HUB", "NODE"]
				},
				"name": {
					"type": "string",
					"description": "Valid system asset name (e.g., ERCOT_HOUSTON_HUB)."
				}
			}
		},
		"deliveryPeriod": {
			"type": "object",
			"required": ["startTime", "endTime", "timeOfUseBlock"],
			"properties": {
				"startTime": {
					"type": "string",
					"format": "date-time"
				},
				"endTime": {
					"type": "string",
					"format": "date-time"
				},
				"timeOfUseBlock": {
					"type": "string",
					"enum": ["ON_PEAK", "OFF_PEAK"],
					"description": "Dictates temporal pricing profiles across market segments."
				}
			}
		},
		"financials": {
			"type": "object",
			"required": ["volumeMW", "pricePerMWh", "currency"],
			"properties": {
				"volumeMW": {
					"type": "number",
					"minimum": 0.1,
					"description": "Continuous capacity delivery flow rate."
				},
				"pricePerMWh": {
					"type": "number",
					"description": "Contractual rate in USD. Can accept negative metrics on extreme over-generation."
				},
				"currency": {
					"type": "string",
					"enum": ["USD"]
				}
			}
		}
	}
}
```

