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
export function isPowerTradePayload(payload: any): payload is PowerTradePayload {
    if (!payload || typeof payload !== "object") return false;

    // Validate Metadata Strings & Integers
    if (typeof payload.tradeId !== "string" || payload.tradeId.trim() === "") return false;
    if (typeof payload.version !== "number" || payload.version < 1) return false;
    if (typeof payload.timestamp !== "string" || isNaN(Date.parse(payload.timestamp))) return false;
    if (typeof payload.traderId !== "string" || payload.traderId.trim() === "") return false;
    if (typeof payload.bookId !== "string" || payload.bookId.trim() === "") return false;
    if (typeof payload.counterparty !== "string" || payload.counterparty.trim() === "") return false;

    // Validate Direct Enums
    if (!Object.values(TradeDirection).includes(payload.direction)) return false;
    if (!Object.values(ProductType).includes(payload.product)) return false;
    if (!Object.values(MarketOperator).includes(payload.marketOperator)) return false;

    // Validate Location Object
    if (!payload.location || typeof payload.location !== "object") return false;
    if (!Object.values(LocationType).includes(payload.location.type)) return false;
    if (typeof payload.location.name !== "string" || payload.location.name.trim() === "") return false;

    // Validate Delivery Period & Time Order Logic
    if (!payload.deliveryPeriod || typeof payload.deliveryPeriod !== "object") return false;
    if (typeof payload.deliveryPeriod.startTime !== "string" || isNaN(Date.parse(payload.deliveryPeriod.startTime))) return false;
    if (typeof payload.deliveryPeriod.endTime !== "string" || isNaN(Date.parse(payload.deliveryPeriod.endTime))) return false;
    if (!Object.values(TimeOfUseBlock).includes(payload.deliveryPeriod.timeOfUseBlock)) return false;

    // Physical Rule: Delivery cannot end before it starts
    const start = new Date(payload.deliveryPeriod.startTime).getTime();
    const end = new Date(payload.deliveryPeriod.endTime).getTime();
    if (end <= start) return false;

    // Validate Financial Metrics
    if (!payload.financials || typeof payload.financials !== "object") return false;
    if (typeof payload.financials.volumeMW !== "number" || payload.financials.volumeMW <= 0) return false;
    if (typeof payload.financials.pricePerMWh !== "number") return false; // Allows negative metrics
    if (payload.financials.currency !== "USD") return false;

    return true;
}
