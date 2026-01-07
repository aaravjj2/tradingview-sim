"""
Skew-Adjusted Probability Sampler
Samples from IV surface instead of normal distribution for fat-tail simulation
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats


class SkewSampler:
    """
    Generate price paths that account for volatility skew (fat tails)
    Uses put/call IV ratio to adjust distribution shape
    """
    
    def __init__(self):
        self.skew_cache: Dict[str, float] = {}
    
    def calculate_skew_index(
        self, 
        atm_iv: float, 
        put_25d_iv: float, 
        call_25d_iv: float
    ) -> float:
        """
        Calculate skew index from option IVs
        Positive = puts expensive (bearish skew)
        Negative = calls expensive (bullish skew)
        """
        if atm_iv == 0:
            return 0.0
        
        # Normalized skew: (25D Put IV - 25D Call IV) / ATM IV
        skew = (put_25d_iv - call_25d_iv) / atm_iv
        return skew
    
    def skewed_distribution(
        self, 
        skew_index: float,
        n_samples: int = 10000
    ) -> np.ndarray:
        """
        Generate samples from a skewed distribution
        Uses skew-normal distribution when skew detected
        """
        if abs(skew_index) < 0.05:
            # Low skew: use normal distribution
            return np.random.standard_normal(n_samples)
        
        # Map skew index to distribution parameters
        # Positive skew_index -> left skew (more downside)
        # Negative skew_index -> right skew (more upside)
        alpha = -skew_index * 10  # Scale to skewnorm alpha
        alpha = np.clip(alpha, -10, 10)
        
        # Generate skew-normal samples
        samples = stats.skewnorm.rvs(alpha, size=n_samples)
        
        # Standardize
        samples = (samples - np.mean(samples)) / np.std(samples)
        
        return samples
    
    def fat_tail_samples(
        self,
        iv: float,
        skew_index: float,
        n_samples: int = 10000,
        tail_weight: float = 0.1
    ) -> np.ndarray:
        """
        Generate samples with fat tails using mixture distribution
        Combines normal core with Student's t-distribution tails
        """
        # Degrees of freedom: lower = fatter tails
        # Scale based on skew magnitude
        df = max(3, 8 - abs(skew_index) * 10)
        
        # Generate core (normal) and tail (t-distribution) samples
        core = self.skewed_distribution(skew_index, int(n_samples * (1 - tail_weight)))
        tails = np.random.standard_t(df, int(n_samples * tail_weight))
        
        # Combine and shuffle
        combined = np.concatenate([core, tails])
        np.random.shuffle(combined)
        
        return combined[:n_samples]
    
    def generate_skewed_paths(
        self,
        current_price: float,
        volatility: float,
        days: int,
        skew_index: float,
        n_simulations: int = 1000,
        drift: float = 0.0
    ) -> np.ndarray:
        """
        Generate price paths using skew-adjusted random samples
        
        Args:
            current_price: Starting price
            volatility: Annualized volatility
            days: Number of days to simulate
            skew_index: Volatility skew (-1 to 1)
            n_simulations: Number of paths
            drift: Expected return (annualized)
        
        Returns:
            Array of shape (n_simulations, days+1) with price paths
        """
        dt = 1 / 252
        paths = np.zeros((n_simulations, days + 1))
        paths[:, 0] = current_price
        
        for t in range(1, days + 1):
            # Generate skew-adjusted samples
            z = self.fat_tail_samples(volatility, skew_index, n_simulations)
            
            # GBM with skewed innovations
            paths[:, t] = paths[:, t-1] * np.exp(
                (drift - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * z
            )
        
        return paths
    
    def estimate_skew_from_chain(
        self,
        option_chain: Dict,
        current_price: float
    ) -> Tuple[float, Dict]:
        """
        Estimate skew from option chain data
        
        Args:
            option_chain: Dict with 'calls' and 'puts' lists
            current_price: Current underlying price
        
        Returns:
            Tuple of (skew_index, skew_details)
        """
        calls = option_chain.get('calls', [])
        puts = option_chain.get('puts', [])
        
        if not calls or not puts:
            return 0.0, {'atm_iv': 0.25, 'put_25d_iv': 0.25, 'call_25d_iv': 0.25}
        
        # Find ATM options (closest to current price)
        def find_nearest(options, target_price):
            if not options:
                return None
            return min(options, key=lambda x: abs(x.get('strike', 0) - target_price))
        
        atm_call = find_nearest(calls, current_price)
        atm_put = find_nearest(puts, current_price)
        
        atm_iv = 0.25
        if atm_call and atm_put:
            atm_iv = (atm_call.get('iv', 0.25) + atm_put.get('iv', 0.25)) / 2
        
        # Find 25-delta options (roughly 10-15% OTM)
        otm_distance = current_price * 0.10
        
        put_25d = find_nearest(puts, current_price - otm_distance)
        call_25d = find_nearest(calls, current_price + otm_distance)
        
        put_25d_iv = put_25d.get('iv', atm_iv) if put_25d else atm_iv
        call_25d_iv = call_25d.get('iv', atm_iv) if call_25d else atm_iv
        
        skew_index = self.calculate_skew_index(atm_iv, put_25d_iv, call_25d_iv)
        
        return skew_index, {
            'atm_iv': atm_iv,
            'put_25d_iv': put_25d_iv,
            'call_25d_iv': call_25d_iv,
            'skew_index': skew_index,
            'skew_type': 'bearish' if skew_index > 0.05 else 'bullish' if skew_index < -0.05 else 'neutral'
        }
