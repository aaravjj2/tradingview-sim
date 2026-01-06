"""
Pydantic Schemas
Data models for API requests and responses
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OptionLeg(BaseModel):
    option_type: str  # "call", "put", "stock"
    position: str  # "long", "short"
    strike: Optional[float] = None
    strike_offset: Optional[int] = None
    premium: Optional[float] = None
    quantity: int = 1
    expiration_days: Optional[int] = None
    iv: Optional[float] = None


class StrategyCreate(BaseModel):
    name: str
    ticker: str
    legs: List[OptionLeg]
    notes: Optional[str] = None


class StrategyResponse(BaseModel):
    id: str
    name: str
    ticker: str
    legs: List[OptionLeg]
    created_at: str


class GreeksData(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float


class PositionMetrics(BaseModel):
    max_profit: float
    max_loss: float
    breakevens: List[float]
    probability_of_profit: float
    greeks: GreeksData


class JournalEntry(BaseModel):
    trade_id: str
    ticker: str
    notes: str
    tags: Optional[str] = ""
    strategy: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    quantity: Optional[int] = None
    side: Optional[str] = None
    pnl: Optional[float] = None


class HeartbeatResponse(BaseModel):
    ticker: str
    price: float
    timestamp: str
    change: float
    change_percent: float
