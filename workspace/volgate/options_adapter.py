"""
Options Adapter

Fetches options chains and calculates Greeks.
Uses yfinance as fallback data source.

Paper-only - no real trading.
"""

import os
import sys
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


@dataclass
class OptionsQuote:
    """Options quote data."""
    symbol: str
    expiration: date
    strike: float
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float


class OptionsAdapter:
    """
    Adapter for fetching options data.
    
    Uses yfinance as primary source, with synthetic fallback.
    Paper-only simulation.
    """
    
    def __init__(self, use_synthetic: bool = True):
        """
        Initialize options adapter.
        
        Args:
            use_synthetic: If True, use synthetic data (default for paper)
        """
        self.use_synthetic = use_synthetic
        self._risk_free_rate = 0.05
        
    def _norm_cdf(self, x: float) -> float:
        """Standard normal CDF approximation."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _norm_pdf(self, x: float) -> float:
        """Standard normal PDF."""
        return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)
    
    def _calculate_d1_d2(self, spot: float, strike: float, 
                         T: float, r: float, sigma: float) -> Tuple[float, float]:
        """Calculate d1 and d2 for Black-Scholes."""
        if T <= 0 or sigma <= 0:
            return (0.0, 0.0)
        
        d1 = (math.log(spot / strike) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return (d1, d2)
    
    def calculate_greeks(self, spot: float, strike: float, 
                         dte: int, sigma: float, option_type: str = 'put',
                         r: float = None) -> Dict[str, float]:
        """
        Calculate option Greeks using Black-Scholes.
        
        Returns:
            Dict with delta, gamma, theta, vega
        """
        r = r or self._risk_free_rate
        T = dte / 365.0
        
        if T <= 0:
            # At expiration
            if option_type == 'put':
                delta = -1.0 if strike > spot else 0.0
            else:
                delta = 1.0 if spot > strike else 0.0
            return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
        
        d1, d2 = self._calculate_d1_d2(spot, strike, T, r, sigma)
        
        # Delta
        if option_type == 'put':
            delta = self._norm_cdf(d1) - 1
        else:
            delta = self._norm_cdf(d1)
        
        # Gamma (same for puts and calls)
        gamma = self._norm_pdf(d1) / (spot * sigma * math.sqrt(T))
        
        # Theta
        term1 = -spot * self._norm_pdf(d1) * sigma / (2 * math.sqrt(T))
        if option_type == 'put':
            term2 = r * strike * math.exp(-r * T) * self._norm_cdf(-d2)
            theta = (term1 + term2) / 365  # Per day
        else:
            term2 = r * strike * math.exp(-r * T) * self._norm_cdf(d2)
            theta = (term1 - term2) / 365  # Per day
        
        # Vega
        vega = spot * math.sqrt(T) * self._norm_pdf(d1) / 100  # Per 1% move in vol
        
        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
        }
    
    def calculate_option_price(self, spot: float, strike: float,
                               dte: int, sigma: float, 
                               option_type: str = 'put',
                               r: float = None) -> float:
        """Calculate option price using Black-Scholes."""
        r = r or self._risk_free_rate
        T = dte / 365.0
        
        if T <= 0:
            if option_type == 'put':
                return max(0, strike - spot)
            else:
                return max(0, spot - strike)
        
        d1, d2 = self._calculate_d1_d2(spot, strike, T, r, sigma)
        
        if option_type == 'put':
            price = strike * math.exp(-r * T) * self._norm_cdf(-d2) - spot * self._norm_cdf(-d1)
        else:
            price = spot * self._norm_cdf(d1) - strike * math.exp(-r * T) * self._norm_cdf(d2)
        
        return max(0, price)
    
    def generate_synthetic_chain(self, symbol: str, spot: float,
                                  expiration_dte: int = 30,
                                  sigma: float = 0.20,
                                  num_strikes: int = 10) -> List[OptionsQuote]:
        """
        Generate synthetic options chain for paper trading.
        
        Args:
            symbol: Underlying symbol
            spot: Current spot price
            expiration_dte: Days to expiration
            sigma: Implied volatility
            num_strikes: Number of strikes to generate
        """
        chain = []
        expiration = date.today() + timedelta(days=expiration_dte)
        
        # Generate strikes around ATM
        strike_step = round(spot * 0.025, 0)  # 2.5% steps
        atm_strike = round(spot / strike_step) * strike_step
        
        for i in range(-num_strikes // 2, num_strikes // 2 + 1):
            strike = atm_strike + i * strike_step
            if strike <= 0:
                continue
            
            for opt_type in ['put', 'call']:
                price = self.calculate_option_price(spot, strike, expiration_dte, sigma, opt_type)
                greeks = self.calculate_greeks(spot, strike, expiration_dte, sigma, opt_type)
                
                # Add bid-ask spread
                spread_pct = 0.05 + 0.10 * abs(strike - spot) / spot  # Wider for OTM
                bid = price * (1 - spread_pct / 2)
                ask = price * (1 + spread_pct / 2)
                
                quote = OptionsQuote(
                    symbol=symbol,
                    expiration=expiration,
                    strike=strike,
                    option_type=opt_type,
                    bid=round(bid, 2),
                    ask=round(ask, 2),
                    last=round(price, 2),
                    volume=int(1000 + 5000 * abs(strike - spot) / spot),
                    open_interest=int(5000 + 20000 * abs(strike - spot) / spot),
                    implied_volatility=sigma,
                    **greeks,
                )
                chain.append(quote)
        
        return chain
    
    def get_options_chain(self, symbol: str, expiration_dte: int = 30,
                          spot: float = None) -> List[OptionsQuote]:
        """
        Get options chain for a symbol.
        
        Args:
            symbol: Underlying symbol
            expiration_dte: Target days to expiration
            spot: Current spot price (required for synthetic)
        """
        if self.use_synthetic:
            if spot is None:
                # Default spot prices
                default_spots = {"SPY": 590.0, "GLD": 185.0, "TLT": 95.0, "QQQ": 500.0}
                spot = default_spots.get(symbol, 100.0)
            
            return self.generate_synthetic_chain(symbol, spot, expiration_dte)
        
        # Try yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            
            # Get available expirations
            expirations = ticker.options
            if not expirations:
                return self.generate_synthetic_chain(symbol, spot or 100.0, expiration_dte)
            
            # Find closest expiration to target DTE
            target_date = date.today() + timedelta(days=expiration_dte)
            closest_exp = min(expirations, 
                              key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d").date() - target_date).days))
            
            # Get chain
            opt_chain = ticker.option_chain(closest_exp)
            
            chain = []
            exp_date = datetime.strptime(closest_exp, "%Y-%m-%d").date()
            dte = (exp_date - date.today()).days
            
            # Process puts
            for _, row in opt_chain.puts.iterrows():
                greeks = self.calculate_greeks(spot or 590, row['strike'], dte, 
                                                row.get('impliedVolatility', 0.2), 'put')
                chain.append(OptionsQuote(
                    symbol=symbol,
                    expiration=exp_date,
                    strike=row['strike'],
                    option_type='put',
                    bid=row.get('bid', 0),
                    ask=row.get('ask', 0),
                    last=row.get('lastPrice', 0),
                    volume=int(row.get('volume', 0) or 0),
                    open_interest=int(row.get('openInterest', 0) or 0),
                    implied_volatility=row.get('impliedVolatility', 0.2),
                    **greeks,
                ))
            
            # Process calls
            for _, row in opt_chain.calls.iterrows():
                greeks = self.calculate_greeks(spot or 590, row['strike'], dte,
                                                row.get('impliedVolatility', 0.2), 'call')
                chain.append(OptionsQuote(
                    symbol=symbol,
                    expiration=exp_date,
                    strike=row['strike'],
                    option_type='call',
                    bid=row.get('bid', 0),
                    ask=row.get('ask', 0),
                    last=row.get('lastPrice', 0),
                    volume=int(row.get('volume', 0) or 0),
                    open_interest=int(row.get('openInterest', 0) or 0),
                    implied_volatility=row.get('impliedVolatility', 0.2),
                    **greeks,
                ))
            
            return chain
            
        except Exception as e:
            # Fallback to synthetic
            return self.generate_synthetic_chain(symbol, spot or 100.0, expiration_dte)
    
    def find_by_delta(self, chain: List[OptionsQuote], 
                      target_delta: float, option_type: str = 'put') -> Optional[OptionsQuote]:
        """Find option closest to target delta."""
        filtered = [q for q in chain if q.option_type == option_type]
        if not filtered:
            return None
        
        return min(filtered, key=lambda q: abs(abs(q.delta) - abs(target_delta)))


if __name__ == "__main__":
    adapter = OptionsAdapter(use_synthetic=True)
    
    print("Options Adapter Test")
    print("=" * 50)
    
    # Generate chain
    chain = adapter.get_options_chain("SPY", expiration_dte=30, spot=590.0)
    
    puts = [q for q in chain if q.option_type == 'put']
    print(f"Generated {len(puts)} put options")
    
    # Find 30-delta put
    target_put = adapter.find_by_delta(chain, 0.30, 'put')
    if target_put:
        print(f"\n30-Delta Put:")
        print(f"  Strike: ${target_put.strike}")
        print(f"  Delta: {target_put.delta}")
        print(f"  Bid/Ask: ${target_put.bid:.2f} / ${target_put.ask:.2f}")
        print(f"  IV: {target_put.implied_volatility*100:.1f}%")
    
    # Test Greeks
    print(f"\nGreeks Calculation Test:")
    greeks = adapter.calculate_greeks(590, 570, 30, 0.20, 'put')
    print(f"  $590 spot, $570 strike, 30 DTE:")
    print(f"  Delta: {greeks['delta']}")
    print(f"  Gamma: {greeks['gamma']}")
    print(f"  Theta: {greeks['theta']}")
    print(f"  Vega: {greeks['vega']}")
