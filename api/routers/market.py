"""
Market Data Router
Handles price, candles, and options chain endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from services.alpaca import AlpacaService
from services.cache import get_cached_candles, store_candles

router = APIRouter()
alpaca = AlpacaService()


class PriceResponse(BaseModel):
    ticker: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: str


class CandleData(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class OptionsData(BaseModel):
    symbol: str
    strike: float
    type: str
    expiration: str
    bid: float
    ask: float
    iv: float
    delta: float
    gamma: float
    theta: float
    vega: float


@router.get("/price/{ticker}", response_model=PriceResponse)
async def get_current_price(ticker: str):
    """Get current stock price"""
    price_data = await alpaca.get_current_price(ticker)
    if not price_data:
        raise HTTPException(status_code=404, detail=f"Could not fetch price for {ticker}")
    return price_data


@router.get("/candles/{ticker}", response_model=List[CandleData])
async def get_candles(
    ticker: str,
    timeframe: str = Query("1Day", description="1Min, 5Min, 15Min, 1Hour, 1Day"),
    limit: int = Query(100, ge=1, le=1000),
    fresh: bool = Query(False, description="Force fresh data from API")
):
    """Get historical candle data with caching"""
    # Check cache first (unless fresh=True)
    if not fresh:
        cached = await get_cached_candles(ticker, timeframe, limit)
        if cached:
            return cached
    
    # Fetch from Alpaca
    candles = await alpaca.get_historical_bars(ticker, timeframe, limit)
    
    # Store in cache
    if candles:
        await store_candles(ticker, timeframe, candles)
    
    return candles


@router.get("/options/{ticker}")
async def get_options_chain(
    ticker: str,
    expiration: Optional[str] = None
):
    """Get options chain for a ticker"""
    chain = await alpaca.get_options_chain(ticker, expiration)
    return chain


@router.get("/expirations/{ticker}")
async def get_expirations(ticker: str):
    """Get available expiration dates"""
    return await alpaca.get_available_expirations(ticker)


@router.get("/iv/{ticker}")
async def get_implied_volatility(ticker: str):
    """Get implied volatility for ATM options"""
    price_data = await alpaca.get_current_price(ticker)
    if not price_data:
        raise HTTPException(status_code=404, detail="Could not fetch price")
    
    iv = await alpaca.get_implied_volatility(ticker, price_data["price"])
    return {"ticker": ticker, "iv": iv}


@router.get("/oi/{ticker}")
async def get_open_interest(ticker: str):
    """Get Open Interest profile for gamma pin analysis"""
    from services.open_interest import get_open_interest_profile
    
    price_data = await alpaca.get_current_price(ticker)
    if not price_data:
        raise HTTPException(status_code=404, detail="Could not fetch price")
    
    return await get_open_interest_profile(ticker, price_data["price"])


@router.get("/gex/{ticker}")
async def get_gamma_exposure(ticker: str):
    """Get Gamma Exposure (GEX) profile"""
    from services.open_interest import get_gex_profile
    
    price_data = await alpaca.get_current_price(ticker)
    if not price_data:
        raise HTTPException(status_code=404, detail="Could not fetch price")
    
    return await get_gex_profile(ticker, price_data["price"])


@router.get("/pricing/local-vol/{ticker}")
async def price_with_local_volatility(
    ticker: str,
    strike: float,
    expiry_days: int = 30,
    option_type: str = "call"
):
    """Price an option using Local Volatility (Dupire) model"""
    from services.local_vol import price_with_local_vol
    
    price_data = await alpaca.get_current_price(ticker)
    if not price_data:
        raise HTTPException(status_code=404, detail="Could not fetch price")
    
    spot = price_data["price"]
    iv = await alpaca.get_implied_volatility(ticker, spot)
    
    return await price_with_local_vol(
        spot=spot,
        strike=strike,
        expiry_years=expiry_days / 365,
        option_type=option_type,
        base_iv=iv
    )


@router.get("/pricing/jump-diffusion/{ticker}")
async def price_with_jump_model(
    ticker: str,
    strike: float,
    expiry_days: int = 30,
    option_type: str = "call",
    jump_intensity: float = 1.0,
    jump_mean: float = -0.05,
    jump_vol: float = 0.10
):
    """Price an option using Merton Jump-Diffusion model"""
    from services.jump_diffusion import price_with_jump_diffusion
    
    price_data = await alpaca.get_current_price(ticker)
    if not price_data:
        raise HTTPException(status_code=404, detail="Could not fetch price")
    
    spot = price_data["price"]
    iv = await alpaca.get_implied_volatility(ticker, spot)
    
    return await price_with_jump_diffusion(
        spot=spot,
        strike=strike,
        expiry_years=expiry_days / 365,
        option_type=option_type,
        sigma=iv,
        jump_intensity=jump_intensity,
        jump_mean=jump_mean,
        jump_vol=jump_vol
    )


@router.get("/pricing/compare/{ticker}")
async def compare_pricing_models(
    ticker: str,
    strike: float,
    expiry_days: int = 30
):
    """Compare all pricing models for a given option"""
    from services.local_vol import price_with_local_vol
    from services.jump_diffusion import price_with_jump_diffusion
    
    price_data = await alpaca.get_current_price(ticker)
    if not price_data:
        raise HTTPException(status_code=404, detail="Could not fetch price")
    
    spot = price_data["price"]
    iv = await alpaca.get_implied_volatility(ticker, spot)
    expiry_years = expiry_days / 365
    
    results = {}
    
    for opt_type in ['call', 'put']:
        local_vol_result = await price_with_local_vol(
            spot=spot, strike=strike, expiry_years=expiry_years,
            option_type=opt_type, base_iv=iv
        )
        
        jump_result = await price_with_jump_diffusion(
            spot=spot, strike=strike, expiry_years=expiry_years,
            option_type=opt_type, sigma=iv
        )
        
        results[opt_type] = {
            'spot': spot,
            'strike': strike,
            'expiry_days': expiry_days,
            'iv': iv,
            'black_scholes': local_vol_result['bs_price'],
            'local_vol': local_vol_result['local_vol_price'],
            'jump_diffusion': jump_result['jump_price'],
            'local_vol_diff': local_vol_result['price_diff'],
            'jump_premium': jump_result['jump_premium']
        }
    
    return results


