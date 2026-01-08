"""
Trade Journal Router
API endpoints for accessing trade journal data.
"""

from fastapi import APIRouter, Query
from typing import Optional
from services.trade_journal import get_trade_journal

router = APIRouter(prefix="/api/journal", tags=["Trade Journal"])


@router.get("/stats")
async def get_journal_stats():
    """Get trade journal statistics."""
    journal = get_trade_journal()
    return journal.get_stats()


@router.get("/recent")
async def get_recent_trades(limit: int = Query(20, ge=1, le=100)):
    """Get recent trades."""
    journal = get_trade_journal()
    return {"trades": journal.get_recent(limit)}


@router.get("/by-strategy/{strategy}")
async def get_trades_by_strategy(strategy: str):
    """Get all trades for a specific strategy."""
    journal = get_trade_journal()
    trades = journal.filter_by_strategy(strategy)
    return {"trades": [t.to_dict() for t in trades]}


@router.post("/record")
async def record_trade(
    ticker: str,
    strategy: str,
    direction: str,
    entry_price: float,
    quantity: int,
    council_decision: dict,
    market_context: Optional[dict] = None,
    llm_explanation: Optional[str] = None
):
    """Manually record a trade."""
    journal = get_trade_journal()
    entry = journal.record_trade(
        ticker=ticker,
        strategy=strategy,
        direction=direction,
        entry_price=entry_price,
        quantity=quantity,
        council_decision=council_decision,
        market_context=market_context,
        llm_explanation=llm_explanation
    )
    return entry.to_dict()


@router.post("/close/{trade_id}")
async def close_trade(trade_id: str, exit_price: float):
    """Close a trade."""
    journal = get_trade_journal()
    entry = journal.close_trade(trade_id, exit_price)
    if entry:
        return entry.to_dict()
    return {"error": "Trade not found"}
