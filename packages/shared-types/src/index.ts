// ============================================================================
// 1. DOMAIN ENUMS (Rigid Data Boundaries)
// ============================================================================
export enum TradeDirection {
    BUY = "BUY",
    SELL = "SELL"
}

export enum ProductType {
    PHYSICAL_POWER = "PHYSICAL_POWER",
    FINANCIAL_SWAP = "FINANCIAL_SWAP"
}

export enum MarketOperator {
    ERCOT = "ERCOT",
    PJM = "PJM",
    MISO = "MISO"
}

export enum LocationType {
    HUB = "HUB",
    NODE = "NODE"
}

export enum TimeOfUseBlock {
    ON_PEAK = "ON_PEAK",
    OFF_PEAK = "OFF_PEAK"
}

// ============================================================================
// 2. INTERFACE PAYLOAD CONTRACTS
// ============================================================================
export interface TradeLocation {
    type: LocationType;
    name: string;
}

export interface DeliveryPeriod {
    startTime: string; // ISO 8601 Date String
    endTime: string;   // ISO 8601 Date String
    timeOfUseBlock: TimeOfUseBlock;
}

export interface Financials {
    volumeMW: number;
    pricePerMWh: number;
    currency: "USD";
}

export interface PowerTradePayload {
    tradeId: string;
    version: number;
    timestamp: string;
    traderId: string;
    bookId: string;
    counterparty: string;
    direction: TradeDirection;
    product: ProductType;
    marketOperator: MarketOperator;
    location: TradeLocation;
    deliveryPeriod: DeliveryPeriod;
    financials: Financials;
}

// ============================================================================
// 3. RUNTIME TYPE GUARDS (Boundary Protection Systems)
// ============================================================================

/**
 * Validates whether an untrusted JSON object strictly conforms to the PowerTradePayload contract.
 * Protects against database contamination from out-of-order or corrupt bot payloads.
 */
function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isEnumValue<T extends Record<string, string>>(
    enumObject: T,
    value: unknown
): value is T[keyof T] {
    return Object.values(enumObject).some((enumValue) => enumValue === value);
}

export function isPowerTradePayload(payload: unknown): payload is PowerTradePayload {
    if (!isRecord(payload)) return false;

    // Validate Metadata Strings & Integers
    if (typeof payload.tradeId !== "string" || payload.tradeId.trim() === "") return false;
    if (typeof payload.version !== "number" || !Number.isFinite(payload.version) || payload.version < 1) return false;
    if (typeof payload.timestamp !== "string" || isNaN(Date.parse(payload.timestamp))) return false;
    if (typeof payload.traderId !== "string" || payload.traderId.trim() === "") return false;
    if (typeof payload.bookId !== "string" || payload.bookId.trim() === "") return false;
    if (typeof payload.counterparty !== "string" || payload.counterparty.trim() === "") return false;

    // Validate Direct Enums
    if (!isEnumValue(TradeDirection, payload.direction)) return false;
    if (!isEnumValue(ProductType, payload.product)) return false;
    if (!isEnumValue(MarketOperator, payload.marketOperator)) return false;

    // Validate Location Object
    const location = payload.location;
    if (!isRecord(location)) return false;
    if (!isEnumValue(LocationType, location.type)) return false;
    if (typeof location.name !== "string" || location.name.trim() === "") return false;

    // Validate Delivery Period & Time Order Logic
    const deliveryPeriod = payload.deliveryPeriod;
    if (!isRecord(deliveryPeriod)) return false;
    if (typeof deliveryPeriod.startTime !== "string" || isNaN(Date.parse(deliveryPeriod.startTime))) return false;
    if (typeof deliveryPeriod.endTime !== "string" || isNaN(Date.parse(deliveryPeriod.endTime))) return false;
    if (!isEnumValue(TimeOfUseBlock, deliveryPeriod.timeOfUseBlock)) return false;

    // Physical Rule: Delivery cannot end before it starts
    const start = new Date(deliveryPeriod.startTime).getTime();
    const end = new Date(deliveryPeriod.endTime).getTime();
    if (end <= start) return false;

    // Validate Financial Metrics
    const financials = payload.financials;
    if (!isRecord(financials)) return false;
    if (typeof financials.volumeMW !== "number" || !Number.isFinite(financials.volumeMW) || financials.volumeMW <= 0) return false;
    if (typeof financials.pricePerMWh !== "number" || !Number.isFinite(financials.pricePerMWh)) return false; // Allows negative metrics
    if (financials.currency !== "USD") return false;

    return true;
}
