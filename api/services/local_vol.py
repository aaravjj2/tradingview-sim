"""
Local Volatility Model (Dupire)
More accurate option pricing during skew events
"""

import math
from typing import Dict, Optional
from functools import lru_cache


def norm_cdf(x: float) -> float:
    """Standard normal CDF approximation"""
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2)
    
    return 0.5 * (1.0 + sign * y)


def norm_pdf(x: float) -> float:
    """Standard normal PDF"""
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def black_scholes_price(
    S: float,  # Spot price
    K: float,  # Strike
    T: float,  # Time to expiry (years)
    r: float,  # Risk-free rate
    sigma: float,  # Volatility
    option_type: str = 'call'
) -> float:
    """Standard Black-Scholes price"""
    if T <= 0:
        if option_type == 'call':
            return max(0, S - K)
        return max(0, K - S)
    
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    
    if option_type == 'call':
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def implied_vol_from_price(
    option_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = 'call',
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> float:
    """Newton-Raphson method to find implied volatility from option price"""
    sigma = 0.3  # Initial guess
    
    for _ in range(max_iterations):
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        diff = option_price - price
        
        if abs(diff) < tolerance:
            return sigma
        
        # Vega (sensitivity to volatility)
        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * sqrt_T)
        vega = S * sqrt_T * norm_pdf(d1)
        
        if vega < 1e-10:
            break
            
        sigma = sigma + diff / vega
        sigma = max(0.01, min(sigma, 5.0))  # Bound between 1% and 500%
    
    return sigma


class LocalVolatilityModel:
    """
    Dupire Local Volatility Model
    
    The local volatility function σ(K, T) is derived from the implied volatility surface
    such that it reproduces all market option prices.
    
    Dupire's formula:
    σ²_loc(K, T) = [∂C/∂T + rK·∂C/∂K] / [½K²·∂²C/∂K²]
    """
    
    def __init__(self, spot: float, rate: float = 0.05):
        self.spot = spot
        self.rate = rate
        self.vol_surface: Dict[tuple, float] = {}  # (K, T) -> implied_vol
    
    def calibrate_from_chain(self, options: list):
        """
        Calibrate the local vol surface from an options chain
        
        Args:
            options: List of dicts with keys: strike, expiry_years, price, option_type
        """
        for opt in options:
            K = opt['strike']
            T = opt['expiry_years']
            price = opt['price']
            opt_type = opt.get('option_type', 'call')
            
            iv = implied_vol_from_price(price, self.spot, K, T, self.rate, opt_type)
            self.vol_surface[(K, T)] = iv
    
    def get_implied_vol(self, K: float, T: float) -> float:
        """Get implied volatility at strike K and expiry T (with interpolation)"""
        if (K, T) in self.vol_surface:
            return self.vol_surface[(K, T)]
        
        # Simple bilinear interpolation
        strikes = sorted(set(k for k, t in self.vol_surface.keys()))
        expiries = sorted(set(t for k, t in self.vol_surface.keys()))
        
        if not strikes or not expiries:
            return 0.25  # Default
        
        # Find surrounding points
        k_lower = max([s for s in strikes if s <= K], default=strikes[0])
        k_upper = min([s for s in strikes if s >= K], default=strikes[-1])
        t_lower = max([e for e in expiries if e <= T], default=expiries[0])
        t_upper = min([e for e in expiries if e >= T], default=expiries[-1])
        
        # Get corner values
        v11 = self.vol_surface.get((k_lower, t_lower), 0.25)
        v12 = self.vol_surface.get((k_lower, t_upper), 0.25)
        v21 = self.vol_surface.get((k_upper, t_lower), 0.25)
        v22 = self.vol_surface.get((k_upper, t_upper), 0.25)
        
        # Interpolate
        if k_upper == k_lower:
            k_weight = 0.5
        else:
            k_weight = (K - k_lower) / (k_upper - k_lower)
        
        if t_upper == t_lower:
            t_weight = 0.5
        else:
            t_weight = (T - t_lower) / (t_upper - t_lower)
        
        v1 = v11 * (1 - k_weight) + v21 * k_weight
        v2 = v12 * (1 - k_weight) + v22 * k_weight
        
        return v1 * (1 - t_weight) + v2 * t_weight
    
    def local_vol(self, K: float, T: float, dK: float = 0.5, dT: float = 0.01) -> float:
        """
        Calculate local volatility using numerical differentiation of Dupire's formula
        """
        if T <= dT:
            return self.get_implied_vol(K, dT)
        
        sigma = self.get_implied_vol(K, T)
        
        # Numerical derivatives
        C = black_scholes_price(self.spot, K, T, self.rate, sigma, 'call')
        C_T_up = black_scholes_price(self.spot, K, T + dT, self.rate, 
                                     self.get_implied_vol(K, T + dT), 'call')
        C_K_up = black_scholes_price(self.spot, K + dK, T, self.rate,
                                     self.get_implied_vol(K + dK, T), 'call')
        C_K_down = black_scholes_price(self.spot, K - dK, T, self.rate,
                                       self.get_implied_vol(K - dK, T), 'call')
        
        dC_dT = (C_T_up - C) / dT
        dC_dK = (C_K_up - C_K_down) / (2 * dK)
        d2C_dK2 = (C_K_up - 2 * C + C_K_down) / (dK * dK)
        
        if d2C_dK2 <= 0:
            return sigma  # Fall back to implied vol
        
        numerator = dC_dT + self.rate * K * dC_dK
        denominator = 0.5 * K * K * d2C_dK2
        
        if denominator <= 0:
            return sigma
        
        local_var = numerator / denominator
        if local_var <= 0:
            return sigma
        
        return math.sqrt(local_var)
    
    def price_option(
        self,
        K: float,
        T: float,
        option_type: str = 'call'
    ) -> Dict:
        """
        Price an option using local volatility
        
        Returns dict with:
        - local_vol_price: Price using local vol
        - bs_price: Standard BS price
        - local_vol: The local volatility used
        - implied_vol: The implied volatility
        """
        implied_vol = self.get_implied_vol(K, T)
        local_v = self.local_vol(K, T)
        
        bs_price = black_scholes_price(self.spot, K, T, self.rate, implied_vol, option_type)
        local_vol_price = black_scholes_price(self.spot, K, T, self.rate, local_v, option_type)
        
        return {
            'strike': K,
            'expiry': T,
            'option_type': option_type,
            'local_vol_price': round(local_vol_price, 4),
            'bs_price': round(bs_price, 4),
            'local_vol': round(local_v, 4),
            'implied_vol': round(implied_vol, 4),
            'price_diff': round(local_vol_price - bs_price, 4),
            'vol_diff': round(local_v - implied_vol, 4)
        }


# API endpoint helper
async def price_with_local_vol(
    spot: float,
    strike: float,
    expiry_years: float,
    option_type: str = 'call',
    rate: float = 0.05,
    base_iv: float = 0.25
) -> Dict:
    """Quick pricing using local vol approximation"""
    model = LocalVolatilityModel(spot, rate)
    
    # Create synthetic vol surface with skew
    for k_mult in [0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15]:
        for t in [0.083, 0.25, 0.5, 1.0]:
            K = spot * k_mult
            # Add skew: OTM puts have higher IV
            skew = 0.1 * (1 - k_mult) if k_mult < 1 else 0.05 * (k_mult - 1)
            iv = base_iv + skew
            model.vol_surface[(K, t)] = iv
    
    return model.price_option(strike, expiry_years, option_type)
