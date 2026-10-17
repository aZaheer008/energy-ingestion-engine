from dataclasses import dataclass
from typing import List, Dict, Literal, TypedDict
from datetime import datetime

# Define explicit type-safe literals matching your Day 6 TypeScript contracts
MarketOperator = Literal["ERCOT", "PJM", "MISO"]
TimeOfUseBlock = Literal["ON_PEAK", "OFF_PEAK"]

class NodeTickDict(TypedDict):
    tick_id: str
    executed_at: str
    market_operator: MarketOperator
    node_id: str
    congestion_component: float
    loss_component: float
    energy_component: float
    final_lmp: float

@dataclass(frozen=True)
class HistoricalNodeVector:
    """
    Immutable domain vector tracking historical time-series pricing points.
    Frozen state guarantees absolute thread-safety across concurrent OS processes.
    """
    node_id: str
    market_operator: MarketOperator
    time_of_use_block: TimeOfUseBlock
    price_signals: List[float] # Ingests clean float arrays for vectorized operations
    timestamps: List[datetime]

@dataclass(frozen=True)
class ComputeGridResult:
    """Encapsulates the final calculated quantitative risk metrics."""
    node_id: str
    rolling_volatility: float
    max_price_spike: float
    mean_price: float
    processed_by_pid: int # Tracks which unique OS Process ID bypassed the GIL
