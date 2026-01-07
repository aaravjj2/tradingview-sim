"""
Advanced Greeks Calculator
Second-order Greeks: Vanna, Charm, Vomma, Speed
"""

import math
from typing import Dict


def normal_cdf(x: float) -> float:
    """Standard Normal CDF approximation"""
    t = 1 / (1 + 0.2316419 * abs(x))
    d = 0.39894228 * math.exp(-x * x / 2)
    prob = d * t * (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    return 1 - prob if x > 0 else prob


def normal_pdf(x: float) -> float:
    """Standard Normal PDF"""
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def calculate_all_greeks(
    option_type: str,
    S: float,  # Spot price
    K: float,  # Strike
    T: float,  # Time to expiry (years)
    r: float,  # Risk-free rate
    sigma: float  # Implied volatility
) -> Dict:
    """
    Calculate all greeks including second-order
    
    First Order: Delta, Gamma, Theta, Vega, Rho
    Second Order: Vanna, Charm, Vomma, Speed
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {
            "delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0,
            "vanna": 0, "charm": 0, "vomma": 0, "speed": 0
        }
    
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    
    # Standard normal values
    N_d1 = normal_cdf(d1)
    N_d2 = normal_cdf(d2)
    N_neg_d1 = normal_cdf(-d1)
    N_neg_d2 = normal_cdf(-d2)
    n_d1 = normal_pdf(d1)
    
    # First-order Greeks
    if option_type == "call":
        delta = N_d1
        theta = ((-S * n_d1 * sigma / (2 * sqrt_T)) - 
                 r * K * math.exp(-r * T) * N_d2) / 365
        rho = K * T * math.exp(-r * T) * N_d2 / 100
    else:  # put
        delta = N_d1 - 1
        theta = ((-S * n_d1 * sigma / (2 * sqrt_T)) + 
                 r * K * math.exp(-r * T) * N_neg_d2) / 365
        rho = -K * T * math.exp(-r * T) * N_neg_d2 / 100
    
    # Gamma (same for calls and puts)
    gamma = n_d1 / (S * sigma * sqrt_T)
    
    # Vega (same for calls and puts)
    vega = S * n_d1 * sqrt_T / 100
    
    # Second-order Greeks
    
    # Vanna: dDelta/dVol = dVega/dSpot
    vanna = -n_d1 * d2 / sigma
    
    # Charm: dDelta/dTime (Delta decay)
    charm = -n_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T)
    if option_type == "put":
        charm = charm + r * math.exp(-r * T) * N_neg_d1
    
    # Vomma: dVega/dVol (Vega convexity)
    vomma = vega * d1 * d2 / sigma
    
    # Speed: dGamma/dSpot
    speed = -gamma / S * (1 + d1 / (sigma * sqrt_T))
    
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
        "vanna": round(vanna, 6),
        "charm": round(charm, 6),
        "vomma": round(vomma, 4),
        "speed": round(speed, 8)
    }


def calculate_beta_weighted_delta(
    position_delta: float,
    position_price: float,
    spy_price: float,
    beta: float
) -> float:
    """
    Calculate Beta-Weighted Delta (normalized to SPY)
    
    Beta-Weighted Delta = Position Delta * (Stock Price / SPY Price) * Beta
    """
    if spy_price <= 0:
        return position_delta
    
    return round(position_delta * (position_price / spy_price) * beta, 4)


def calculate_portfolio_greeks(positions: list, spy_price: float = 500) -> Dict:
    """
    Aggregate greeks across multiple positions
    Returns net exposure and beta-weighted values
    """
    totals = {
        "delta": 0,
        "gamma": 0,
        "theta": 0,
        "vega": 0,
        "vanna": 0,
        "charm": 0,
        "beta_weighted_delta": 0
    }
    
    for pos in positions:
        qty = pos.get("quantity", 1)
        multiplier = 100  # Options contract size
        
        totals["delta"] += pos.get("delta", 0) * qty * multiplier
        totals["gamma"] += pos.get("gamma", 0) * qty * multiplier
        totals["theta"] += pos.get("theta", 0) * qty * multiplier
        totals["vega"] += pos.get("vega", 0) * qty * multiplier
        totals["vanna"] += pos.get("vanna", 0) * qty * multiplier
        totals["charm"] += pos.get("charm", 0) * qty * multiplier
        
        # Beta-weighted
        price = pos.get("underlying_price", 100)
        beta = pos.get("beta", 1.0)
        bwd = calculate_beta_weighted_delta(
            pos.get("delta", 0) * qty * multiplier,
            price,
            spy_price,
            beta
        )
        totals["beta_weighted_delta"] += bwd
    
    return {k: round(v, 4) for k, v in totals.items()}
