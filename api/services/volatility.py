"""
Volatility Analysis Service
Handles IV Surface, HV calculations, and volatility metrics
"""

import math
from typing import List, Dict
from datetime import datetime, timedelta


def calculate_iv_surface(options_data: List[Dict], expirations: List[str]) -> Dict:
    """
    Build 3D Implied Volatility Surface
    Returns: {strikes: [], expirations: [], iv_matrix: [[...]]}
    """
    # Extract unique strikes across all expirations
    all_strikes = set()
    for opt in options_data:
        all_strikes.add(opt.get("strike", 0))
    
    strikes = sorted(list(all_strikes))
    
    # Build IV matrix: rows = expirations, cols = strikes
    iv_matrix = []
    
    for exp in expirations:
        row = []
        for strike in strikes:
            # Find option matching this expiration and strike
            iv = 0.25  # Default IV
            for opt in options_data:
                if opt.get("expiration") == exp and opt.get("strike") == strike:
                    iv = opt.get("iv", 0.25)
                    break
            row.append(iv * 100)  # Convert to percentage
        iv_matrix.append(row)
    
    return {
        "strikes": strikes,
        "expirations": expirations,
        "iv_matrix": iv_matrix
    }


def calculate_historical_volatility(candles: List[Dict], period: int = 20) -> float:
    """
    Calculate Historical Volatility using close prices
    Uses log returns and annualized standard deviation
    """
    if len(candles) < period + 1:
        return 0.20  # Default 20%
    
    # Get last N+1 closes for N returns
    closes = [c.get("close", 0) for c in candles[-(period + 1):]]
    
    # Calculate log returns
    log_returns = []
    for i in range(1, len(closes)):
        if closes[i-1] > 0:
            log_returns.append(math.log(closes[i] / closes[i-1]))
    
    if not log_returns:
        return 0.20
    
    # Calculate standard deviation
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / len(log_returns)
    std_dev = math.sqrt(variance)
    
    # Annualize (assuming daily data, 252 trading days)
    annualized_vol = std_dev * math.sqrt(252)
    
    return round(annualized_vol, 4)


def calculate_probability_cone(current_price: float, iv: float, days: int = 30) -> Dict:
    """
    Calculate price probability cone based on IV
    Returns 1σ and 2σ bounds for given time horizon
    """
    # Time factor (fraction of year)
    t = days / 365
    
    # Expected move = Price * IV * sqrt(T)
    expected_move_1sigma = current_price * iv * math.sqrt(t)
    expected_move_2sigma = expected_move_1sigma * 2
    
    return {
        "current_price": current_price,
        "days": days,
        "iv": iv,
        "upper_1sigma": round(current_price + expected_move_1sigma, 2),
        "lower_1sigma": round(current_price - expected_move_1sigma, 2),
        "upper_2sigma": round(current_price + expected_move_2sigma, 2),
        "lower_2sigma": round(current_price - expected_move_2sigma, 2),
        "expected_move_pct": round(expected_move_1sigma / current_price * 100, 2)
    }


def calculate_iv_smile(options_data: List[Dict], expiration: str) -> Dict:
    """
    Extract IV Smile/Skew for a specific expiration
    Returns puts and calls IV by strike
    """
    calls = []
    puts = []
    
    for opt in options_data:
        if opt.get("expiration") != expiration:
            continue
        
        strike = opt.get("strike", 0)
        iv = opt.get("iv", 0) * 100  # Convert to percentage
        opt_type = opt.get("type", "")
        
        if opt_type == "call":
            calls.append({"strike": strike, "iv": iv})
        elif opt_type == "put":
            puts.append({"strike": strike, "iv": iv})
    
    # Sort by strike
    calls.sort(key=lambda x: x["strike"])
    puts.sort(key=lambda x: x["strike"])
    
    # Determine skew direction
    skew = "neutral"
    if puts and calls:
        avg_put_iv = sum(p["iv"] for p in puts) / len(puts) if puts else 0
        avg_call_iv = sum(c["iv"] for c in calls) / len(calls) if calls else 0
        
        if avg_put_iv > avg_call_iv * 1.1:
            skew = "bearish"  # Put skew
        elif avg_call_iv > avg_put_iv * 1.1:
            skew = "bullish"  # Call skew
    
    return {
        "expiration": expiration,
        "calls": calls,
        "puts": puts,
        "skew": skew
    }
