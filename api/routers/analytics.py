"""
Advanced Analytics Router
Endpoints for all Phase 8-13 features
"""

from fastapi import APIRouter, Query
from typing import List, Optional
import asyncio

# Import services
from services.ensemble_forecaster import EnsembleForecaster
from services.skew_sampler import SkewSampler
from services.macro_factors import MacroFactors
from services.whale_tracker import WhaleTracker
from services.nlp_strategy import NLPStrategyParser
from services.margin_simulator import MarginSimulator, Position
from services.vega_arb import VegaArbScanner
from services.roll_manager import RollManager

router = APIRouter(prefix="/api", tags=["Advanced Analytics"])

# Service instances
forecaster = EnsembleForecaster()
skew_sampler = SkewSampler()
macro_factors = MacroFactors()
whale_tracker = WhaleTracker()
nlp_parser = NLPStrategyParser()
margin_sim = MarginSimulator()


@router.get("/forecast/ensemble/{ticker}")
async def get_ensemble_forecast(
    ticker: str,
    days: int = Query(30, ge=1, le=90),
    current_price: float = Query(500.0),
    iv: float = Query(0.25, ge=0.05, le=2.0)
):
    """
    Get hybrid ensemble forecast (Monte Carlo + GARCH + Trend)
    """
    # Generate mock historical prices for demo
    import numpy as np
    historical = [current_price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(60)]
    historical.append(current_price)
    
    result = forecaster.forecast(
        current_price=current_price,
        historical_prices=historical,
        days=days,
        base_iv=iv
    )
    
    return result


@router.get("/forecast/probability/{ticker}")
async def get_probability_above(
    ticker: str,
    target_price: float,
    current_price: float = Query(500.0),
    days: int = Query(30)
):
    """Calculate probability of price exceeding target"""
    import numpy as np
    historical = [current_price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(60)]
    
    prob = forecaster.probability_above(
        current_price=current_price,
        target_price=target_price,
        historical_prices=historical,
        days=days
    )
    
    return {
        "ticker": ticker,
        "current_price": current_price,
        "target_price": target_price,
        "days": days,
        "probability": prob
    }


@router.get("/skew/{ticker}")
async def get_skew_analysis(
    ticker: str,
    current_price: float = Query(500.0)
):
    """Analyze volatility skew from options chain"""
    # Mock option chain for demo
    mock_chain = {
        "calls": [
            {"strike": current_price * 0.9, "iv": 0.28},
            {"strike": current_price, "iv": 0.25},
            {"strike": current_price * 1.1, "iv": 0.23},
        ],
        "puts": [
            {"strike": current_price * 0.9, "iv": 0.30},
            {"strike": current_price, "iv": 0.25},
            {"strike": current_price * 1.1, "iv": 0.22},
        ]
    }
    
    skew_index, details = skew_sampler.estimate_skew_from_chain(mock_chain, current_price)
    
    return {
        "ticker": ticker,
        **details
    }


@router.get("/macro/factors")
async def get_macro_factors():
    """Get current macro factor values"""
    factors = macro_factors.get_current_factors()
    yield_curve = macro_factors.get_yield_curve_signal()
    
    return {
        "factors": factors,
        "yield_curve": yield_curve
    }


@router.get("/macro/drift/{ticker}")
async def get_drift_adjustment(
    ticker: str,
    sector: str = Query("default")
):
    """Get drift adjustment based on macro correlations"""
    adjustment, impacts = macro_factors.calculate_drift_adjustment(ticker, sector)
    
    return {
        "ticker": ticker,
        "sector": sector,
        "drift_adjustment": adjustment,
        "factor_impacts": impacts
    }


@router.get("/whale/alerts")
async def get_whale_alerts(
    tickers: str = Query("SPY,QQQ,AAPL")
):
    """Get whale alerts for specified tickers"""
    ticker_list = [t.strip() for t in tickers.split(",")]
    alerts = await whale_tracker.get_top_alerts(ticker_list)
    return alerts


@router.post("/strategy/parse")
async def parse_strategy(
    command: str,
    current_price: float = Query(500.0)
):
    """Parse natural language strategy command"""
    result = nlp_parser.parse(command, current_price)
    
    if result:
        return {
            "success": True,
            "strategy_name": result.strategy_name,
            "ticker": result.ticker,
            "legs": result.legs,
            "confidence": result.confidence,
            "description": nlp_parser.describe_strategy(result)
        }
    
    return {
        "success": False,
        "error": "Could not parse strategy",
        "suggestions": nlp_parser.get_suggestions(command)
    }


@router.get("/strategy/suggestions")
async def get_strategy_suggestions(
    partial: str = Query("")
):
    """Get strategy autocomplete suggestions"""
    suggestions = nlp_parser.get_suggestions(partial)
    return {"suggestions": suggestions}


@router.get("/margin/simulate")
async def simulate_margin(
    strategy_type: str = Query("iron_condor"),
    current_price: float = Query(500.0),
    quantity: int = Query(1)
):
    """Compare Reg-T vs Portfolio Margin for a strategy"""
    result = margin_sim.calculate_for_strategy(strategy_type, current_price, quantity)
    return result


@router.post("/margin/custom")
async def custom_margin_calculation(
    positions: List[dict]
):
    """Calculate margin for custom positions"""
    pos_list = [
        Position(
            symbol=p.get("symbol", "SPY"),
            position_type=p.get("type", "call"),
            quantity=p.get("quantity", 1),
            current_price=p.get("current_price", 500),
            strike=p.get("strike"),
            expiration_days=p.get("dte"),
            is_long=p.get("is_long", True)
        )
        for p in positions
    ]
    
    result = margin_sim.compare_margins(pos_list)
    return result


@router.get("/scanner/vega")
async def scan_vega_opportunities():
    """Scan for calendar spread opportunities"""
    scanner = VegaArbScanner(None)  # No alpaca service for mock
    # Return mock opportunities
    opportunities = [
        {
            "ticker": "SPY",
            "iv_rank": 5.2,
            "front_month_iv": 0.18,
            "back_month_iv": 0.22,
            "term_structure": "contango",
            "strike": 580,
            "net_debit": 2.50,
            "score": 85
        },
        {
            "ticker": "QQQ",
            "iv_rank": 8.1,
            "front_month_iv": 0.20,
            "back_month_iv": 0.24,
            "term_structure": "contango",
            "strike": 500,
            "net_debit": 3.20,
            "score": 72
        }
    ]
    return {"opportunities": opportunities}
