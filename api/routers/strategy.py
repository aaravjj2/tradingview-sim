"""
Strategy Router
Handles strategy CRUD and execution
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from services.alpaca import AlpacaService
from models.schemas import StrategyCreate, StrategyResponse, OptionLeg

router = APIRouter()
alpaca = AlpacaService()


@router.post("/create", response_model=StrategyResponse)
async def create_strategy(strategy: StrategyCreate):
    """Create a new strategy"""
    return StrategyResponse(
        id=datetime.now().strftime("%Y%m%d%H%M%S"),
        name=strategy.name,
        ticker=strategy.ticker,
        legs=strategy.legs,
        created_at=datetime.now().isoformat()
    )


class StrategyExecution(BaseModel):
    strategy_id: str
    ticker: str
    action: str  # BUY or SELL
    quantity: int
    paper_mode: bool = True
    password: Optional[str] = None


@router.post("/execute")
async def execute_strategy(
    execution: StrategyExecution
):
    """Execute a strategy via Alpaca"""
    # For live mode, require password
    if not execution.paper_mode:
        if execution.password != "LIVE_TRADE_2024":
            raise HTTPException(status_code=403, detail="Invalid password for live trading")
    
    # Execute actual trade
    try:
        side = "buy" if execution.action.upper() == "BUY" else "sell"
        order = await alpaca.submit_order(
            symbol=execution.ticker,
            qty=execution.quantity,
            side=side,
            order_type="market",
            time_in_force="day"
        )
        
        if "error" in order:
             raise HTTPException(status_code=400, detail=f"Alpaca Error: {order['error']}")

        return {
            "status": "filled" if order.get("status") == "filled" else "submitted",
            "order_id": order.get("id"),
            "strategy_id": execution.strategy_id,
            "mode": "paper" if execution.paper_mode else "live",
            "timestamp": datetime.now().isoformat(),
            "details": order
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates")
async def get_strategy_templates():
    """Get predefined strategy templates"""
    return {
        "Long Call": [{"option_type": "call", "position": "long", "strike_offset": 0}],
        "Long Put": [{"option_type": "put", "position": "long", "strike_offset": 0}],
        "Bull Call Spread": [
            {"option_type": "call", "position": "long", "strike_offset": 0},
            {"option_type": "call", "position": "short", "strike_offset": 1}
        ],
        "Bear Put Spread": [
            {"option_type": "put", "position": "long", "strike_offset": 0},
            {"option_type": "put", "position": "short", "strike_offset": -1}
        ],
        "Iron Condor": [
            {"option_type": "put", "position": "short", "strike_offset": -1},
            {"option_type": "put", "position": "long", "strike_offset": -2},
            {"option_type": "call", "position": "short", "strike_offset": 1},
            {"option_type": "call", "position": "long", "strike_offset": 2}
        ],
        "Covered Call": [
            {"option_type": "stock", "position": "long", "quantity": 100},
            {"option_type": "call", "position": "short", "strike_offset": 1}
        ]
    }


@router.post("/calculate")
async def calculate_strategy(strategy: StrategyCreate):
    """Calculate strategy metrics (max profit, max loss, breakevens)"""
    # Placeholder for calculation logic
    return {
        "max_profit": 1000.00,
        "max_loss": -500.00,
        "breakevens": [100.00],
        "probability_of_profit": 55.0,
        "greeks": {
            "delta": 0.50,
            "gamma": 0.05,
            "theta": -10.00,
            "vega": 15.00
        }
    }
