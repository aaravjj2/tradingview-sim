"""
Max Pain Calculator
Calculates the strike price where option writers lose the least money
"""

from typing import List, Dict


def calculate_max_pain(options_chain: Dict, current_price: float) -> Dict:
    """
    Calculate Max Pain price for options expiration
    
    Max Pain = Strike where total $ value of ITM options is minimized
    (i.e., where option writers pay out the least)
    """
    calls = options_chain.get("calls", [])
    puts = options_chain.get("puts", [])
    
    # Get unique strikes
    strikes = set()
    for opt in calls + puts:
        strikes.add(opt.get("strike", 0))
    
    strikes = sorted(list(strikes))
    
    if not strikes:
        return {"max_pain": current_price, "pain_by_strike": []}
    
    pain_by_strike = []
    min_pain = float("inf")
    max_pain_strike = current_price
    
    for test_strike in strikes:
        total_pain = 0
        
        # Calculate call pain (calls ITM below test_strike)
        for call in calls:
            strike = call.get("strike", 0)
            oi = call.get("open_interest", 100)  # Default OI if not available
            
            if test_strike > strike:
                # Call is ITM, writers pay out
                pain = (test_strike - strike) * oi * 100
                total_pain += pain
        
        # Calculate put pain (puts ITM above test_strike)
        for put in puts:
            strike = put.get("strike", 0)
            oi = put.get("open_interest", 100)
            
            if test_strike < strike:
                # Put is ITM, writers pay out
                pain = (strike - test_strike) * oi * 100
                total_pain += pain
        
        pain_by_strike.append({
            "strike": test_strike,
            "pain": total_pain
        })
        
        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike
    
    return {
        "max_pain": max_pain_strike,
        "min_total_pain": min_pain,
        "pain_by_strike": pain_by_strike
    }


def calculate_gamma_exposure(options_chain: Dict, current_price: float) -> Dict:
    """
    Calculate Gamma Exposure (GEX) by strike
    Helps identify price levels with significant options activity
    """
    calls = options_chain.get("calls", [])
    puts = options_chain.get("puts", [])
    
    gex_by_strike = {}
    
    # Process calls (positive gamma for dealers if short calls)
    for call in calls:
        strike = call.get("strike", 0)
        oi = call.get("open_interest", 100)
        gamma = call.get("gamma", 0.05)
        
        # GEX = Gamma * OI * 100 (contract size) * Spot^2 * 0.01
        gex = gamma * oi * 100 * (current_price ** 2) * 0.01
        
        if strike not in gex_by_strike:
            gex_by_strike[strike] = 0
        gex_by_strike[strike] += gex  # Calls add positive gamma
    
    # Process puts (negative gamma for dealers if short puts)
    for put in puts:
        strike = put.get("strike", 0)
        oi = put.get("open_interest", 100)
        gamma = put.get("gamma", 0.05)
        
        gex = gamma * oi * 100 * (current_price ** 2) * 0.01
        
        if strike not in gex_by_strike:
            gex_by_strike[strike] = 0
        gex_by_strike[strike] -= gex  # Puts subtract gamma
    
    # Convert to list and sort
    gex_list = [{"strike": k, "gex": v} for k, v in gex_by_strike.items()]
    gex_list.sort(key=lambda x: x["strike"])
    
    # Find flip point (where GEX crosses zero)
    flip_point = current_price
    for i in range(1, len(gex_list)):
        if gex_list[i-1]["gex"] * gex_list[i]["gex"] < 0:
            flip_point = gex_list[i]["strike"]
            break
    
    return {
        "gex_by_strike": gex_list,
        "flip_point": flip_point,
        "total_gex": sum(g["gex"] for g in gex_list)
    }
