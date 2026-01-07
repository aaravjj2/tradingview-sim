"""
Merton Jump-Diffusion Model
Better pricing for OTM options and tail risk
"""

import math
from typing import Dict
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


def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes call price"""
    if T <= 0:
        return max(0, S - K)
    
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)


def black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes put price"""
    if T <= 0:
        return max(0, K - S)
    
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


class MertonJumpDiffusion:
    """
    Merton's Jump-Diffusion Model (1976)
    
    dS/S = (μ - λk)dt + σdW + (Y-1)dN
    
    Where:
    - μ: drift
    - σ: diffusion volatility  
    - λ: jump intensity (expected number of jumps per year)
    - Y: jump size (lognormal: ln(Y) ~ N(μ_J, σ_J²))
    - k = E[Y-1] = exp(μ_J + σ_J²/2) - 1
    
    The model is useful for pricing OTM options where Black-Scholes underprices
    due to fat tails in the actual return distribution.
    """
    
    def __init__(
        self,
        spot: float,
        rate: float = 0.05,
        sigma: float = 0.20,      # Diffusion volatility
        lam: float = 1.0,         # Jump intensity (jumps per year)
        mu_j: float = -0.05,      # Mean jump size (log)
        sigma_j: float = 0.10     # Jump size volatility
    ):
        self.spot = spot
        self.rate = rate
        self.sigma = sigma
        self.lam = lam
        self.mu_j = mu_j
        self.sigma_j = sigma_j
        
        # Expected relative jump size
        self.k = math.exp(mu_j + sigma_j * sigma_j / 2) - 1
    
    def price_call(self, K: float, T: float, n_terms: int = 50) -> float:
        """
        Price a call option using the series expansion
        
        C = Σ (exp(-λ'T) * (λ'T)^n / n!) * C_BS(S_n, K, T, r_n, σ_n)
        
        Where:
        - λ' = λ(1+k)
        - S_n = S * exp(-λkT) * (1+k)^n
        - σ_n² = σ² + n*σ_J²/T
        - r_n = r - λk + n*ln(1+k)/T
        """
        lam_prime = self.lam * (1 + self.k)
        
        total_price = 0.0
        
        for n in range(n_terms):
            # Poisson probability weight
            poisson_weight = math.exp(-lam_prime * T) * (lam_prime * T) ** n / math.factorial(n)
            
            if poisson_weight < 1e-12:
                break
            
            # Adjusted parameters for n jumps
            sigma_n_sq = self.sigma ** 2 + n * self.sigma_j ** 2 / T if T > 0 else self.sigma ** 2
            sigma_n = math.sqrt(sigma_n_sq)
            
            r_n = self.rate - self.lam * self.k + n * math.log(1 + self.k) / T if T > 0 else self.rate
            
            S_n = self.spot * math.exp(-self.lam * self.k * T) * ((1 + self.k) ** n)
            
            # Black-Scholes price for this component
            bs_price = black_scholes_call(S_n, K, T, r_n, sigma_n)
            
            total_price += poisson_weight * bs_price
        
        return total_price
    
    def price_put(self, K: float, T: float, n_terms: int = 50) -> float:
        """Price a put option using put-call parity"""
        call_price = self.price_call(K, T, n_terms)
        # Put-call parity: P = C - S + K*exp(-rT)
        return call_price - self.spot + K * math.exp(-self.rate * T)
    
    def price_option(self, K: float, T: float, option_type: str = 'call') -> Dict:
        """
        Price an option and compare to Black-Scholes
        
        Returns:
        - jump_price: Merton jump-diffusion price
        - bs_price: Black-Scholes price
        - jump_premium: Extra value from accounting for jumps
        """
        if option_type == 'call':
            jump_price = self.price_call(K, T)
            bs_price = black_scholes_call(self.spot, K, T, self.rate, self.sigma)
        else:
            jump_price = self.price_put(K, T)
            bs_price = black_scholes_put(self.spot, K, T, self.rate, self.sigma)
        
        # Moneyness
        moneyness = self.spot / K
        
        return {
            'strike': K,
            'expiry': T,
            'option_type': option_type,
            'spot': self.spot,
            'moneyness': round(moneyness, 4),
            'jump_price': round(jump_price, 4),
            'bs_price': round(bs_price, 4),
            'jump_premium': round(jump_price - bs_price, 4),
            'jump_premium_pct': round((jump_price / bs_price - 1) * 100 if bs_price > 0 else 0, 2),
            'params': {
                'sigma': self.sigma,
                'lambda': self.lam,
                'mu_j': self.mu_j,
                'sigma_j': self.sigma_j
            }
        }
    
    def implied_jump_vol(self, K: float, T: float) -> float:
        """
        Calculate the "effective" volatility that would make BS price match jump price
        This shows how much extra vol is needed to account for jumps
        """
        jump_price = self.price_call(K, T)
        
        # Binary search for implied vol
        vol_low, vol_high = 0.01, 2.0
        
        for _ in range(100):
            vol_mid = (vol_low + vol_high) / 2
            bs_price = black_scholes_call(self.spot, K, T, self.rate, vol_mid)
            
            if abs(bs_price - jump_price) < 0.0001:
                return vol_mid
            elif bs_price < jump_price:
                vol_low = vol_mid
            else:
                vol_high = vol_mid
        
        return (vol_low + vol_high) / 2


# API endpoint helper
async def price_with_jump_diffusion(
    spot: float,
    strike: float,
    expiry_years: float,
    option_type: str = 'call',
    rate: float = 0.05,
    sigma: float = 0.20,
    jump_intensity: float = 1.0,
    jump_mean: float = -0.05,
    jump_vol: float = 0.10
) -> Dict:
    """Quick pricing using jump-diffusion model"""
    model = MertonJumpDiffusion(
        spot=spot,
        rate=rate,
        sigma=sigma,
        lam=jump_intensity,
        mu_j=jump_mean,
        sigma_j=jump_vol
    )
    
    result = model.price_option(strike, expiry_years, option_type)
    result['implied_jump_vol'] = round(model.implied_jump_vol(strike, expiry_years), 4)
    
    return result


def analyze_tail_risk(
    spot: float,
    strikes: list,
    expiry_years: float,
    sigma: float = 0.20,
    jump_intensity: float = 1.0
) -> list:
    """
    Analyze how jump-diffusion affects pricing across strikes
    Useful for understanding tail risk pricing
    """
    model = MertonJumpDiffusion(spot=spot, sigma=sigma, lam=jump_intensity)
    
    results = []
    for K in strikes:
        for opt_type in ['call', 'put']:
            result = model.price_option(K, expiry_years, opt_type)
            results.append(result)
    
    return results
