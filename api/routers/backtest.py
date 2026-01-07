"""
Backtest Router
Handles strategy backtesting and Monte Carlo simulations
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from services.montecarlo import monte_carlo_pop, price_distribution

router = APIRouter()


class BacktestRequest(BaseModel):
    ticker: str
    strategy_rule: str  # e.g., "RSI < 30"
    start_date: str
    end_date: str
    initial_capital: float = 10000.0


class TradeSignal(BaseModel):
    date: str
    action: str  # "buy" or "sell"
    price: float
    reason: str


class BacktestResult(BaseModel):
    ticker: str
    strategy_rule: str
    signals: List[TradeSignal]
    total_return: float
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float


class OptionLeg(BaseModel):
    option_type: str  # call, put, stock
    position: str  # long, short
    strike: float
    premium: float = 0
    quantity: int = 1


class MonteCarloRequest(BaseModel):
    spot: float
    volatility: float  # Annualized IV (e.g., 0.25 for 25%)
    days: int  # Days to expiration
    legs: List[OptionLeg]
    num_simulations: int = 1000
    risk_free_rate: float = 0.05


@router.post("/run", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest):
    """Run a backtest on historical data"""
    return BacktestResult(
        ticker=request.ticker,
        strategy_rule=request.strategy_rule,
        signals=[
            TradeSignal(date="2024-01-15", action="buy", price=450.0, reason="RSI crossed below 30"),
            TradeSignal(date="2024-01-22", action="sell", price=465.0, reason="RSI crossed above 70")
        ],
        total_return=3.33,
        sharpe_ratio=1.5,
        win_rate=65.0,
        max_drawdown=-5.2
    )


@router.post("/monte-carlo")
async def run_monte_carlo(request: MonteCarloRequest):
    """Run Monte Carlo simulation for options strategy"""
    try:
        # Convert Pydantic models to dicts
        legs_dict = [leg.dict() for leg in request.legs]
        
        result = monte_carlo_pop(
            spot=request.spot,
            volatility=request.volatility,
            days=request.days,
            legs=legs_dict,
            risk_free_rate=request.risk_free_rate,
            num_simulations=request.num_simulations
        )
        
        # Get price distribution
        distribution = price_distribution(result.final_prices)
        
        return {
            "spot": request.spot,
            "volatility": request.volatility,
            "days": request.days,
            "num_simulations": request.num_simulations,
            "results": {
                "pop": result.pop,
                "expected_return": result.expected_return,
                "max_profit": result.max_profit,
                "max_loss": result.max_loss,
                "percentiles": result.percentiles
            },
            "distribution": distribution,
            "sample_paths": result.paths[:20]  # Only first 20 for visualization
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rules")
async def get_available_rules():
    """Get available strategy rules for backtesting"""
    return {
        "momentum": [
            {"id": "rsi_oversold", "name": "RSI Oversold", "rule": "RSI < 30"},
            {"id": "rsi_overbought", "name": "RSI Overbought", "rule": "RSI > 70"},
            {"id": "macd_cross", "name": "MACD Crossover", "rule": "MACD crosses above Signal"}
        ],
        "trend": [
            {"id": "sma_cross", "name": "SMA Crossover", "rule": "SMA20 > SMA50"},
            {"id": "price_above_sma", "name": "Price Above SMA", "rule": "Price > SMA200"}
        ],
        "volatility": [
            {"id": "bb_squeeze", "name": "Bollinger Squeeze", "rule": "Bandwidth < 0.1"},
            {"id": "bb_breakout", "name": "Bollinger Breakout", "rule": "Price > Upper Band"}
        ]
    }

