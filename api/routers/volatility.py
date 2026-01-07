"""
Volatility Router
API endpoints for volatility analysis
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from services.alpaca import AlpacaService
from services.volatility import (
    calculate_iv_surface,
    calculate_historical_volatility,
    calculate_probability_cone,
    calculate_iv_smile
)
from services.maxpain import calculate_max_pain, calculate_gamma_exposure
from services.greeks import calculate_all_greeks, calculate_portfolio_greeks

router = APIRouter()
alpaca = AlpacaService()


class GreeksRequest(BaseModel):
    option_type: str
    spot: float
    strike: float
    time_to_expiry: float  # in years
    risk_free_rate: float = 0.05
    volatility: float


@router.get("/surface/{ticker}")
async def get_iv_surface(ticker: str):
    """Get 3D Implied Volatility Surface data"""
    try:
        options = await alpaca.get_options_chain(ticker)
        expirations = await alpaca.get_available_expirations(ticker)
        
        all_options = options.get("calls", []) + options.get("puts", [])
        
        surface = calculate_iv_surface(all_options, expirations[:6])  # First 6 expirations
        
        return {
            "ticker": ticker,
            "surface": surface
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/hv/{ticker}")
async def get_historical_volatility(ticker: str, period: int = 20):
    """Calculate Historical Volatility from price data"""
    try:
        bars = await alpaca.get_historical_bars(ticker, "1Day", period + 10)
        
        hv = calculate_historical_volatility(bars, period)
        
        # Also get current IV for comparison
        options = await alpaca.get_options_chain(ticker)
        all_opts = options.get("calls", []) + options.get("puts", [])
        
        # Average IV from ATM options
        current_price = await alpaca.get_current_price(ticker)
        price = current_price.get("price", 100) if current_price else 100
        
        # Find ATM options
        atm_opts = sorted(all_opts, key=lambda x: abs(x.get("strike", 0) - price))[:4]
        avg_iv = sum(o.get("iv", 0.25) for o in atm_opts) / len(atm_opts) if atm_opts else 0.25
        
        return {
            "ticker": ticker,
            "period": period,
            "historical_volatility": hv,
            "implied_volatility": round(avg_iv, 4),
            "iv_hv_ratio": round(avg_iv / hv, 2) if hv > 0 else 1.0,
            "signal": "expensive" if avg_iv > hv * 1.2 else ("cheap" if avg_iv < hv * 0.8 else "fair")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cone/{ticker}")
async def get_probability_cone(ticker: str, days: int = 30):
    """Calculate probability cone based on IV"""
    try:
        current = await alpaca.get_current_price(ticker)
        if not current:
            raise HTTPException(status_code=404, detail="Could not fetch price")
        
        price = current.get("price", 100)
        
        # Get IV from options
        options = await alpaca.get_options_chain(ticker)
        all_opts = options.get("calls", []) + options.get("puts", [])
        
        atm_opts = sorted(all_opts, key=lambda x: abs(x.get("strike", 0) - price))[:4]
        iv = sum(o.get("iv", 0.25) for o in atm_opts) / len(atm_opts) if atm_opts else 0.25
        
        cone = calculate_probability_cone(price, iv, days)
        
        return {
            "ticker": ticker,
            **cone
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/smile/{ticker}")
async def get_iv_smile(ticker: str, expiration: Optional[str] = None):
    """Get IV Smile/Skew for a specific expiration"""
    try:
        options = await alpaca.get_options_chain(ticker)
        all_opts = options.get("calls", []) + options.get("puts", [])
        
        if not expiration:
            expirations = await alpaca.get_available_expirations(ticker)
            expiration = expirations[0] if expirations else ""
        
        smile = calculate_iv_smile(all_opts, expiration)
        
        return {
            "ticker": ticker,
            **smile
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/maxpain/{ticker}")
async def get_max_pain(ticker: str):
    """Calculate Max Pain price"""
    try:
        options = await alpaca.get_options_chain(ticker)
        current = await alpaca.get_current_price(ticker)
        
        price = current.get("price", 100) if current else 100
        
        result = calculate_max_pain(options, price)
        
        return {
            "ticker": ticker,
            "current_price": price,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/gex/{ticker}")
async def get_gamma_exposure(ticker: str):
    """Calculate Gamma Exposure by strike"""
    try:
        options = await alpaca.get_options_chain(ticker)
        current = await alpaca.get_current_price(ticker)
        
        price = current.get("price", 100) if current else 100
        
        result = calculate_gamma_exposure(options, price)
        
        return {
            "ticker": ticker,
            "current_price": price,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/greeks")
async def calculate_greeks(request: GreeksRequest):
    """Calculate all Greeks including second-order"""
    try:
        result = calculate_all_greeks(
            option_type=request.option_type,
            S=request.spot,
            K=request.strike,
            T=request.time_to_expiry,
            r=request.risk_free_rate,
            sigma=request.volatility
        )
        
        return {
            "input": request.dict(),
            "greeks": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
