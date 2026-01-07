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


@router.post("/close-all")
async def close_all_positions():
    """Emergency close all open positions"""
    try:
        # Get all positions
        positions = await alpaca.get_positions()
        
        if not positions or len(positions) == 0:
            return {"closed_count": 0, "message": "No open positions"}
        
        closed = []
        errors = []
        
        for pos in positions:
            symbol = pos.get("symbol", "")
            qty = abs(int(float(pos.get("qty", 0))))
            side = "sell" if float(pos.get("qty", 0)) > 0 else "buy"
            
            try:
                order = await alpaca.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    order_type="market",
                    time_in_force="day"
                )
                
                if "error" not in order:
                    closed.append(symbol)
                else:
                    errors.append(f"{symbol}: {order['error']}")
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
        
        return {
            "closed_count": len(closed),
            "closed_symbols": closed,
            "errors": errors,
            "message": f"Closed {len(closed)} positions"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================
# AI & Advanced Analytics
# =========================

@router.get("/recommend/{ticker}")
async def get_ai_recommendation(
    ticker: str,
    current_price: float = 500.0,
    iv_rank: float = 50.0,
    days_to_expiry: int = 30,
    risk_tolerance: str = "moderate"
):
    """Get AI strategy recommendation"""
    from services.strategy_recommender import get_strategy_recommendation
    
    return await get_strategy_recommendation(
        ticker=ticker,
        current_price=current_price,
        iv_rank=iv_rank,
        days_to_expiry=days_to_expiry,
        risk_tolerance=risk_tolerance
    )


@router.get("/forecast/{ticker}")
async def forecast_price(
    ticker: str,
    current_price: float = 500.0,
    targets: str = "480,490,510,520",
    days: int = 30,
    volatility: float = 0.25
):
    """Forecast price with target probabilities"""
    from services.price_forecast import forecast_price as forecast
    
    target_list = [float(t.strip()) for t in targets.split(",")]
    return await forecast(ticker, current_price, target_list, days, volatility)


@router.get("/correlation")
async def analyze_correlations(
    tickers: str = "SPY,QQQ,IWM,GLD,TLT",
    lookback: int = 60
):
    """Get correlation matrix"""
    from services.correlation_matrix import analyze_correlations as analyze
    
    ticker_list = [t.strip() for t in tickers.split(",")]
    return await analyze(ticker_list, lookback)


@router.get("/drawdown")
async def analyze_drawdown(
    annual_return: float = 0.15,
    annual_volatility: float = 0.20,
    days: int = 252,
    simulations: int = 10000
):
    """Monte Carlo drawdown analysis"""
    from services.drawdown_analysis import run_drawdown_analysis
    
    return await run_drawdown_analysis(
        annual_return=annual_return,
        annual_volatility=annual_volatility,
        days=days,
        num_simulations=simulations
    )


@router.get("/dispersion/{index}")
async def scan_dispersion(index: str = "SPY"):
    """Scan for dispersion trading opportunities"""
    from services.dispersion_scanner import scan_dispersion
    
    return await scan_dispersion(index)
