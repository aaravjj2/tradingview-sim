"""
Protective Puts Overlay

Implements protective put options as an overlay to reduce tail risk.

Features:
- Buy 30-delta puts (DTE 30-45) during Risk-Off or as scheduled hedge
- Put spreads as lower-cost alternative
- Paper-only simulation with assignment risk and wide spreads
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random
import math

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class OptionType(Enum):
    PUT = "put"
    CALL = "call"


@dataclass
class OptionContract:
    """Represents an option contract."""
    symbol: str
    option_type: OptionType
    strike: float
    expiration: date
    delta: float
    premium: float  # Per share
    contracts: int = 1  # Each contract = 100 shares
    
    @property
    def notional_protection(self) -> float:
        """Dollar value of protection provided (puts only)."""
        if self.option_type == OptionType.PUT:
            return self.strike * self.contracts * 100
        return 0.0
    
    @property
    def total_cost(self) -> float:
        """Total premium paid."""
        return self.premium * self.contracts * 100


@dataclass
class PutSpread:
    """Represents a put spread (long put + short put)."""
    symbol: str
    long_put: OptionContract
    short_put: OptionContract
    
    @property
    def net_premium(self) -> float:
        """Net cost of spread."""
        return self.long_put.total_cost - self.short_put.total_cost
    
    @property
    def max_protection(self) -> float:
        """Maximum dollar protection from spread."""
        return (self.long_put.strike - self.short_put.strike) * self.long_put.contracts * 100


@dataclass
class ProtectionConfig:
    """Configuration for protective options."""
    target_delta: float = 0.30  # 30-delta puts
    min_dte: int = 30
    max_dte: int = 45
    notional_protection_pct: float = 0.50  # Protect 50% of portfolio
    annual_cost_budget_pct: float = 0.02  # Max 2% annual premium spend
    use_spreads: bool = True  # Use put spreads to reduce cost
    spread_width_pct: float = 0.10  # 10% spread width
    roll_days_before_expiry: int = 7
    enable_scheduled_hedge: bool = True
    hedge_schedule_days: List[int] = field(default_factory=lambda: [1, 15])  # 1st and 15th


class OptionsSimulator:
    """
    Simulates options pricing and execution.
    
    Uses simplified Black-Scholes approximations for paper trading.
    No real broker connection - paper only.
    """
    
    def __init__(self, risk_free_rate: float = 0.05, volatility: float = 0.20):
        self.risk_free_rate = risk_free_rate
        self.volatility = volatility
    
    def _norm_cdf(self, x: float) -> float:
        """Approximate standard normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _estimate_put_price(self, spot: float, strike: float, 
                           dte: int, volatility: float) -> float:
        """Estimate put price using Black-Scholes approximation."""
        if dte <= 0:
            return max(0, strike - spot)
        
        T = dte / 365.0
        d1 = (math.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility**2) * T) / (volatility * math.sqrt(T))
        d2 = d1 - volatility * math.sqrt(T)
        
        put_price = strike * math.exp(-self.risk_free_rate * T) * self._norm_cdf(-d2) - spot * self._norm_cdf(-d1)
        
        # Add bid-ask spread simulation (wider for OTM options)
        moneyness = strike / spot
        if moneyness < 0.9:  # OTM put
            spread_pct = 0.15  # 15% bid-ask spread
        else:
            spread_pct = 0.05
        
        # Return mid price with some randomness
        return put_price * (1 + random.uniform(-spread_pct/2, spread_pct/2))
    
    def _estimate_delta(self, spot: float, strike: float, 
                        dte: int, volatility: float) -> float:
        """Estimate put delta."""
        if dte <= 0:
            return -1.0 if strike > spot else 0.0
        
        T = dte / 365.0
        d1 = (math.log(spot / strike) + (self.risk_free_rate + 0.5 * volatility**2) * T) / (volatility * math.sqrt(T))
        
        return self._norm_cdf(d1) - 1  # Put delta is negative
    
    def find_target_delta_put(self, symbol: str, spot: float, 
                              target_delta: float, dte: int,
                              volatility: float = None) -> OptionContract:
        """Find a put with approximately the target delta."""
        vol = volatility or self.volatility
        
        # Binary search for strike that gives target delta
        low_strike = spot * 0.70
        high_strike = spot * 1.00
        
        for _ in range(20):
            mid_strike = (low_strike + high_strike) / 2
            delta = self._estimate_delta(spot, mid_strike, dte, vol)
            
            if abs(delta) < target_delta:
                low_strike = mid_strike
            else:
                high_strike = mid_strike
        
        strike = round(mid_strike, 2)
        premium = self._estimate_put_price(spot, strike, dte, vol)
        delta = self._estimate_delta(spot, strike, dte, vol)
        
        expiration = date.today() + timedelta(days=dte)
        
        return OptionContract(
            symbol=symbol,
            option_type=OptionType.PUT,
            strike=strike,
            expiration=expiration,
            delta=delta,
            premium=premium,
        )
    
    def create_put_spread(self, symbol: str, spot: float,
                          target_delta: float, dte: int,
                          spread_width_pct: float = 0.10,
                          volatility: float = None) -> PutSpread:
        """Create a put spread with the given parameters."""
        vol = volatility or self.volatility
        
        # Long put at target delta
        long_put = self.find_target_delta_put(symbol, spot, target_delta, dte, vol)
        
        # Short put at lower strike
        short_strike = long_put.strike * (1 - spread_width_pct)
        short_premium = self._estimate_put_price(spot, short_strike, dte, vol)
        short_delta = self._estimate_delta(spot, short_strike, dte, vol)
        
        short_put = OptionContract(
            symbol=symbol,
            option_type=OptionType.PUT,
            strike=round(short_strike, 2),
            expiration=long_put.expiration,
            delta=short_delta,
            premium=short_premium,
        )
        
        return PutSpread(symbol=symbol, long_put=long_put, short_put=short_put)
    
    def simulate_expiration_pnl(self, contract: OptionContract, 
                                 final_price: float) -> float:
        """Simulate P&L at expiration."""
        if contract.option_type == OptionType.PUT:
            intrinsic = max(0, contract.strike - final_price)
            return (intrinsic - contract.premium) * contract.contracts * 100
        else:
            intrinsic = max(0, final_price - contract.strike)
            return (intrinsic - contract.premium) * contract.contracts * 100


class ProtectivePutsOverlay:
    """
    Manages protective put overlay for a portfolio.
    
    Paper-only simulation with realistic costs and risks.
    """
    
    def __init__(self, config: Optional[ProtectionConfig] = None):
        self.config = config or ProtectionConfig()
        self.simulator = OptionsSimulator()
        self.active_positions: List[OptionContract] = []
        self.active_spreads: List[PutSpread] = []
        self.total_premium_spent: float = 0.0
        self.protection_log: List[Dict] = []
    
    def should_hedge(self, current_date: date, regime: str, 
                     is_in_position: bool) -> bool:
        """Determine if hedging is warranted."""
        # Always hedge if in Risk-Off regime and have position
        if regime.lower() in ["risk_off", "risk-off", "defensive"] and is_in_position:
            return True
        
        # Scheduled hedging on specific days
        if self.config.enable_scheduled_hedge:
            if current_date.day in self.config.hedge_schedule_days and is_in_position:
                return True
        
        return False
    
    def calculate_contracts_needed(self, portfolio_value: float, 
                                   spot_price: float) -> int:
        """Calculate number of contracts needed for target protection."""
        protection_value = portfolio_value * self.config.notional_protection_pct
        shares_to_protect = protection_value / spot_price
        contracts = int(shares_to_protect / 100)
        return max(1, contracts)
    
    def add_protection(self, symbol: str, spot_price: float,
                       portfolio_value: float, current_date: date,
                       volatility: float = 0.20) -> Dict:
        """Add protective put or spread overlay."""
        # Check annual budget
        annual_budget = portfolio_value * self.config.annual_cost_budget_pct
        if self.total_premium_spent >= annual_budget:
            return {"status": "budget_exceeded", "action": None}
        
        contracts_needed = self.calculate_contracts_needed(portfolio_value, spot_price)
        dte = random.randint(self.config.min_dte, self.config.max_dte)
        
        result = {}
        
        if self.config.use_spreads:
            # Create put spread
            spread = self.simulator.create_put_spread(
                symbol, spot_price, self.config.target_delta,
                dte, self.config.spread_width_pct, volatility
            )
            spread.long_put.contracts = contracts_needed
            spread.short_put.contracts = contracts_needed
            
            cost = spread.net_premium
            self.active_spreads.append(spread)
            
            result = {
                "status": "added_spread",
                "long_strike": spread.long_put.strike,
                "short_strike": spread.short_put.strike,
                "expiration": spread.long_put.expiration,
                "contracts": contracts_needed,
                "net_premium": cost,
                "max_protection": spread.max_protection,
            }
        else:
            # Create naked put
            put = self.simulator.find_target_delta_put(
                symbol, spot_price, self.config.target_delta, dte, volatility
            )
            put.contracts = contracts_needed
            
            cost = put.total_cost
            self.active_positions.append(put)
            
            result = {
                "status": "added_put",
                "strike": put.strike,
                "delta": put.delta,
                "expiration": put.expiration,
                "contracts": contracts_needed,
                "premium": cost,
                "notional_protection": put.notional_protection,
            }
        
        self.total_premium_spent += cost
        self.protection_log.append({
            "date": current_date.isoformat(),
            "action": result["status"],
            "cost": cost,
            **result,
        })
        
        return result
    
    def roll_expiring_positions(self, current_date: date, spot_price: float,
                                  portfolio_value: float, volatility: float = 0.20) -> List[Dict]:
        """Roll positions that are near expiration."""
        results = []
        
        # Check and roll expiring puts
        for position in self.active_positions[:]:
            days_to_expiry = (position.expiration - current_date).days
            if days_to_expiry <= self.config.roll_days_before_expiry:
                self.active_positions.remove(position)
                result = self.add_protection(
                    position.symbol, spot_price, portfolio_value,
                    current_date, volatility
                )
                result["rolled_from"] = position.expiration.isoformat()
                results.append(result)
        
        # Check and roll expiring spreads
        for spread in self.active_spreads[:]:
            days_to_expiry = (spread.long_put.expiration - current_date).days
            if days_to_expiry <= self.config.roll_days_before_expiry:
                self.active_spreads.remove(spread)
                result = self.add_protection(
                    spread.symbol, spot_price, portfolio_value,
                    current_date, volatility
                )
                result["rolled_from"] = spread.long_put.expiration.isoformat()
                results.append(result)
        
        return results
    
    def calculate_protection_pnl(self, final_price: float) -> float:
        """Calculate P&L from all protection positions."""
        total_pnl = 0.0
        
        for put in self.active_positions:
            total_pnl += self.simulator.simulate_expiration_pnl(put, final_price)
        
        for spread in self.active_spreads:
            long_pnl = self.simulator.simulate_expiration_pnl(spread.long_put, final_price)
            short_pnl = -self.simulator.simulate_expiration_pnl(spread.short_put, final_price)
            total_pnl += long_pnl + short_pnl
        
        return total_pnl
    
    def get_summary(self) -> Dict:
        """Get summary of protective overlay."""
        return {
            "active_puts": len(self.active_positions),
            "active_spreads": len(self.active_spreads),
            "total_premium_spent": self.total_premium_spent,
            "protection_entries": len(self.protection_log),
        }
    
    def reset(self):
        """Reset all positions and tracking."""
        self.active_positions.clear()
        self.active_spreads.clear()
        self.total_premium_spent = 0.0
        self.protection_log.clear()


def run_protection_backtest(prices: List[float], portfolio_value: float = 100000,
                            crash_scenario: bool = False) -> Dict:
    """
    Run backtest of protective overlay.
    
    Args:
        prices: Price series
        portfolio_value: Initial portfolio value
        crash_scenario: Simulate 2008/2020 style crash
    """
    overlay = ProtectivePutsOverlay()
    spot = prices[0]
    
    if crash_scenario:
        # Inject a crash - price drops 30% over 20 days
        crash_start = len(prices) // 2
        for i in range(crash_start, min(crash_start + 20, len(prices))):
            prices[i] = prices[crash_start - 1] * (1 - 0.015 * (i - crash_start + 1))
    
    # Add initial protection
    initial_protection = overlay.add_protection(
        "SPY", spot, portfolio_value, date(2026, 1, 1), volatility=0.20
    )
    
    # Track unprotected and protected portfolios
    unprotected_dd = 0.0
    protected_dd = 0.0
    peak = portfolio_value
    
    for i, price in enumerate(prices[30:]):
        current_value = portfolio_value * (price / spot)
        peak = max(peak, current_value)
        unprotected_dd = max(unprotected_dd, (peak - current_value) / peak)
        
        # Calculate protected value
        protection_pnl = overlay.calculate_protection_pnl(price)
        protected_value = current_value + protection_pnl
        protected_dd = max(protected_dd, (peak - protected_value) / peak)
    
    return {
        "unprotected_max_dd": unprotected_dd * 100,
        "protected_max_dd": protected_dd * 100,
        "dd_reduction_pct": (unprotected_dd - protected_dd) / unprotected_dd * 100 if unprotected_dd > 0 else 0,
        "total_premium_cost": overlay.total_premium_spent,
        "premium_cost_pct": overlay.total_premium_spent / portfolio_value * 100,
        "summary": overlay.get_summary(),
    }


if __name__ == "__main__":
    # Simple test
    import numpy as np
    np.random.seed(42)
    
    # Generate synthetic prices
    prices = [590.0]
    for _ in range(252):
        prices.append(prices[-1] * (1 + np.random.normal(0.0003, 0.012)))
    
    print("Testing Protective Puts Overlay")
    print("=" * 50)
    
    # Normal market
    result = run_protection_backtest(prices.copy())
    print(f"Normal Market:")
    print(f"  Unprotected Max DD: {result['unprotected_max_dd']:.1f}%")
    print(f"  Protected Max DD: {result['protected_max_dd']:.1f}%")
    print(f"  Premium Cost: {result['premium_cost_pct']:.2f}%")
    
    # Crash scenario
    result_crash = run_protection_backtest(prices.copy(), crash_scenario=True)
    print(f"\nCrash Scenario:")
    print(f"  Unprotected Max DD: {result_crash['unprotected_max_dd']:.1f}%")
    print(f"  Protected Max DD: {result_crash['protected_max_dd']:.1f}%")
    print(f"  DD Reduction: {result_crash['dd_reduction_pct']:.1f}%")
