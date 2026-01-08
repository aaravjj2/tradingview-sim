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
    print(f"[OI] DEBUG: Fetching for {ticker} at {current_price}")
    try:
        # Fetch options chain
        chain = await alpaca.get_options_chain(ticker)
        
        calls = chain.get("calls", [])
        puts = chain.get("puts", [])
        
        # Aggregate OI by strike
        oi_by_strike: Dict[float, Dict] = {}
        
        # Track total OI from Alpaca to check data quality
        total_alpaca_oi = 0
        
        for opt in calls:
            strike = opt.get("strike", 0)
            oi_estimate = opt.get("volume", 0) * 10  # Rough estimate
            gamma = opt.get("gamma", 0)
            
            total_alpaca_oi += oi_estimate
            
            if strike not in oi_by_strike:
                oi_by_strike[strike] = {"call_oi": 0, "put_oi": 0, "call_gamma": 0, "put_gamma": 0}
            
            oi_by_strike[strike]["call_oi"] += oi_estimate
            oi_by_strike[strike]["call_gamma"] += gamma * oi_estimate * 100
        
        for opt in puts:
            strike = opt.get("strike", 0)
            oi_estimate = opt.get("volume", 0) * 10
            gamma = opt.get("gamma", 0)
            
            total_alpaca_oi += oi_estimate
            
            if strike not in oi_by_strike:
                oi_by_strike[strike] = {"call_oi": 0, "put_oi": 0, "call_gamma": 0, "put_gamma": 0}
            
            oi_by_strike[strike]["put_oi"] += oi_estimate
            oi_by_strike[strike]["put_gamma"] += gamma * oi_estimate * 100
        
        print(f"[OI] DEBUG: Alpaca Total Estimated OI: {total_alpaca_oi}")
        
        # Fallback if Alpaca data is empty OR has very low volume (likely bad data)
        if total_alpaca_oi < 1000:
            print("[OI] DEBUG: Alpaca data insufficient. Starting YFinance fallback...")
            # Fallback to yfinance if Alpaca data is empty (common in paper/free tier)
            try:
                import yfinance as yf
                import asyncio
                
                # Define blocking YF logic in a separate function
                def fetch_yf_data(ticker_symbol):
                    print(f"[OI] YFinance thread started for {ticker_symbol}")
                    yf_ticker = yf.Ticker(ticker_symbol)
                    opts = yf_ticker.options
                    result_data = {}
                    
                    if opts:
                        # Fetch first 2 expirations
                        for expiry in opts[:2]:
                            try:
                                chain = yf_ticker.option_chain(expiry)
                                # Convert to dict records to avoid passing DataFrames across threads if possible, 
                                # but here we just process and return the needed stats or the full chain data.
                                # Actually, better to do the heavy dataframe processing in the thread too.
                                
                                calls_data = []
                                puts_data = []
                                
                                # Handle NaNs and iterate
                                calls_df = chain.calls.fillna(0)
                                for _, row in calls_df.iterrows():
                                    calls_data.append({
                                        'strike': float(row['strike']),
                                        'oi': float(row['openInterest']),
                                        'vol': float(row['volume'])
                                    })
                                    
                                puts_df = chain.puts.fillna(0)
                                for _, row in puts_df.iterrows():
                                    puts_data.append({
                                        'strike': float(row['strike']),
                                        'oi': float(row['openInterest']),
                                        'vol': float(row['volume'])
                                    })
                                
                                result_data[expiry] = {'calls': calls_data, 'puts': puts_data}
                            except Exception as ex:
                                print(f"[OI] Error fetching expiry {expiry}: {ex}")
                    return result_data

                # Run in thread pool
                print(f"[OI] Offloading YFinance fetch to thread...")
                yf_results = await asyncio.to_thread(fetch_yf_data, ticker)
                
                # Process results back in main loop (cpu bound but fast)
                for expiry, data in yf_results.items():
                    # Process calls
                    for row in data['calls']:
                        strike = row['strike']
                        oi = row['oi']
                        
                        moneyness = abs(strike - current_price) / current_price
                        gamma_proxy = 1.0 / (moneyness + 0.01) * 0.01
                        
                        if strike not in oi_by_strike:
                            oi_by_strike[strike] = {"call_oi": 0, "put_oi": 0, "call_gamma": 0, "put_gamma": 0}
                        
                        oi_by_strike[strike]["call_oi"] += oi
                        oi_by_strike[strike]["call_gamma"] += gamma_proxy * oi * 100

                    # Process puts
                    for row in data['puts']:
                        strike = row['strike']
                        oi = row['oi']
                        
                        moneyness = abs(strike - current_price) / current_price
                        gamma_proxy = 1.0 / (moneyness + 0.01) * 0.01
                        
                        if strike not in oi_by_strike:
                            oi_by_strike[strike] = {"call_oi": 0, "put_oi": 0, "call_gamma": 0, "put_gamma": 0}
                        
                        oi_by_strike[strike]["put_oi"] += oi
                        oi_by_strike[strike]["put_gamma"] += gamma_proxy * oi * 100
                            
            except Exception as e:
                print(f"[OI] YFinance fallback failed: {e}")

        # Convert to sorted list
        strikes = sorted(oi_by_strike.keys())
        profile = []
        
        for strike in strikes:
            data = oi_by_strike[strike]
            net_gamma = data["call_gamma"] - data["put_gamma"]
            total_oi = data["call_oi"] + data["put_oi"]
            
            # Filter low OI strikes to reduce noise
            if total_oi > 10:  # Lowered from 100
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
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "profile": profile,
            "max_oi_strike": max_oi_strike,
            "zero_gamma_strikes": [],
            "support_levels": [p["strike"] for p in profile if p["put_oi"] > p["call_oi"] * 1.5 and p["strike"] < current_price][-3:],
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
