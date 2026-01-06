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
    limit: int = Query(100, ge=1, le=1000)
):
    """Get historical candle data with caching"""
    # Check cache first
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
