"""
Open Interest Service
Fetches and processes Open Interest data for gamma pin analysis
"""

from typing import Dict, List, Optional
from services.alpaca import AlpacaService

alpaca = AlpacaService()


async def get_open_interest_profile(ticker: str, current_price: float) -> Dict:
    """
    Get Open Interest profile for a ticker.
    Returns OI at each strike with gamma exposure estimates.
    """
    try:
        # Fetch options chain
        chain = await alpaca.get_options_chain(ticker)
        
        calls = chain.get("calls", [])
        puts = chain.get("puts", [])
        
        # Aggregate OI by strike
        oi_by_strike: Dict[float, Dict] = {}
        
        for opt in calls:
            strike = opt.get("strike", 0)
            # Alpaca doesn't provide OI directly, estimate from volume
            # In production, use a data provider with OI data
            oi_estimate = opt.get("volume", 0) * 10  # Rough estimate
            gamma = opt.get("gamma", 0)
            
            if strike not in oi_by_strike:
                oi_by_strike[strike] = {"call_oi": 0, "put_oi": 0, "call_gamma": 0, "put_gamma": 0}
            
            oi_by_strike[strike]["call_oi"] += oi_estimate
            oi_by_strike[strike]["call_gamma"] += gamma * oi_estimate * 100
        
        for opt in puts:
            strike = opt.get("strike", 0)
            oi_estimate = opt.get("volume", 0) * 10
            gamma = opt.get("gamma", 0)
            
            if strike not in oi_by_strike:
                oi_by_strike[strike] = {"call_oi": 0, "put_oi": 0, "call_gamma": 0, "put_gamma": 0}
            
            oi_by_strike[strike]["put_oi"] += oi_estimate
            oi_by_strike[strike]["put_gamma"] += gamma * oi_estimate * 100
        
        # Convert to sorted list
        strikes = sorted(oi_by_strike.keys())
        profile = []
        
        for strike in strikes:
            data = oi_by_strike[strike]
            net_gamma = data["call_gamma"] - data["put_gamma"]
            total_oi = data["call_oi"] + data["put_oi"]
            
            profile.append({
                "strike": strike,
                "call_oi": data["call_oi"],
                "put_oi": data["put_oi"],
                "total_oi": total_oi,
                "net_gamma": net_gamma,
                "call_gamma": data["call_gamma"],
                "put_gamma": data["put_gamma"]
            })
        
        # Find significant levels
        max_oi_strike = max(profile, key=lambda x: x["total_oi"])["strike"] if profile else current_price
        zero_gamma_strikes = [p["strike"] for p in profile if abs(p["net_gamma"]) < 1000]
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "profile": profile,
            "max_oi_strike": max_oi_strike,
            "zero_gamma_strikes": zero_gamma_strikes,
            "support_levels": [p["strike"] for p in profile if p["put_oi"] > p["call_oi"] * 1.5 and p["strike"] < current_price][:3],
            "resistance_levels": [p["strike"] for p in profile if p["call_oi"] > p["put_oi"] * 1.5 and p["strike"] > current_price][:3]
        }
        
    except Exception as e:
        print(f"Error fetching OI profile: {e}")
        return {
            "ticker": ticker,
            "current_price": current_price,
            "profile": [],
            "max_oi_strike": current_price,
            "zero_gamma_strikes": [],
            "support_levels": [],
            "resistance_levels": []
        }


async def get_gex_profile(ticker: str, current_price: float) -> Dict:
    """
    Calculate Gamma Exposure (GEX) profile.
    GEX = Gamma * Open Interest * 100 * Spot Price^2 * 0.01
    
    Positive GEX = Market makers are long gamma (stabilizing)
    Negative GEX = Market makers are short gamma (amplifying moves)
    """
    try:
        chain = await alpaca.get_options_chain(ticker)
        
        calls = chain.get("calls", [])
        puts = chain.get("puts", [])
        
        gex_by_strike: Dict[float, float] = {}
        
        # Call GEX (positive contribution)
        for opt in calls:
            strike = opt.get("strike", 0)
            gamma = opt.get("gamma", 0)
            oi_estimate = opt.get("volume", 0) * 10
            
            # GEX formula simplified
            gex = gamma * oi_estimate * 100 * (current_price ** 2) * 0.01
            
            if strike in gex_by_strike:
                gex_by_strike[strike] += gex
            else:
                gex_by_strike[strike] = gex
        
        # Put GEX (negative contribution - dealers are short puts)
        for opt in puts:
            strike = opt.get("strike", 0)
            gamma = opt.get("gamma", 0)
            oi_estimate = opt.get("volume", 0) * 10
            
            gex = -gamma * oi_estimate * 100 * (current_price ** 2) * 0.01
            
            if strike in gex_by_strike:
                gex_by_strike[strike] += gex
            else:
                gex_by_strike[strike] = gex
        
        # Convert to sorted list
        strikes = sorted(gex_by_strike.keys())
        profile = [{"strike": s, "gex": gex_by_strike[s]} for s in strikes]
        
        # Find zero gamma level (flip point)
        total_gex = sum(p["gex"] for p in profile)
        cumulative_gex = 0
        zero_gamma_level = current_price
        
        for p in profile:
            cumulative_gex += p["gex"]
            if cumulative_gex >= total_gex / 2:
                zero_gamma_level = p["strike"]
                break
        
        # Determine regime
        regime = "positive" if total_gex > 0 else "negative"
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "profile": profile,
            "total_gex": total_gex,
            "zero_gamma_level": zero_gamma_level,
            "regime": regime,
            "regime_description": "Low volatility expected" if regime == "positive" else "High volatility expected"
        }
        
    except Exception as e:
        print(f"Error calculating GEX: {e}")
        return {
            "ticker": ticker,
            "current_price": current_price,
            "profile": [],
            "total_gex": 0,
            "zero_gamma_level": current_price,
            "regime": "unknown",
            "regime_description": "Unable to determine"
        }
