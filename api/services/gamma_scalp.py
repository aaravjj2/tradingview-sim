"""
Gamma Scalping Algorithm
Automatically delta-hedge long gamma positions to harvest volatility
"""

import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime
import math


class GammaScalper:
    """
    Gamma Scalping Bot
    
    For long gamma positions (long options), the strategy:
    1. When delta becomes too positive (price moved up): Sell shares to neutralize
    2. When delta becomes too negative (price moved down): Buy shares to neutralize
    
    This "scalps" the gamma by buying low and selling high, capturing volatility.
    """
    
    def __init__(
        self,
        ticker: str,
        position_delta: float,  # Current option delta exposure
        position_gamma: float,  # Current option gamma
        hedge_threshold: float = 0.10,  # Rebalance when delta drifts by this amount
        max_hedge_size: int = 100,  # Maximum shares per hedge
        min_hedge_interval: int = 60,  # Minimum seconds between hedges
        paper_mode: bool = True
    ):
        self.ticker = ticker
        self.position_delta = position_delta
        self.position_gamma = position_gamma
        self.hedge_threshold = hedge_threshold
        self.max_hedge_size = max_hedge_size
        self.min_hedge_interval = min_hedge_interval
        self.paper_mode = paper_mode
        
        self.is_running = False
        self.current_stock_position = 0  # Net shares held for hedging
        self.last_hedge_time: Optional[datetime] = None
        self.hedge_history: List[Dict] = []
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        # Reference price for P&L calculation
        self.reference_price: Optional[float] = None
    
    def calculate_current_delta(self, current_price: float) -> float:
        """
        Calculate current delta exposure including stock hedge
        
        Delta changes as price moves due to gamma:
        new_delta ≈ old_delta + gamma * (price_change)
        """
        if self.reference_price is None:
            self.reference_price = current_price
            return self.position_delta + self.current_stock_position
        
        price_change = current_price - self.reference_price
        option_delta = self.position_delta + self.position_gamma * price_change
        
        # Total delta = option delta + stock position (1 delta per share)
        total_delta = option_delta + self.current_stock_position
        
        return total_delta
    
    def calculate_hedge_size(self, current_price: float) -> int:
        """
        Determine how many shares to buy/sell to neutralize delta
        
        Returns positive for buy, negative for sell
        """
        current_delta = self.calculate_current_delta(current_price)
        
        # Don't hedge if within threshold
        if abs(current_delta) < self.hedge_threshold:
            return 0
        
        # Calculate shares needed to neutralize
        # If delta is +0.5, need to sell 0.5 * 100 = 50 shares
        shares_needed = -int(current_delta * 100)
        
        # Cap at max hedge size
        shares_needed = max(-self.max_hedge_size, min(self.max_hedge_size, shares_needed))
        
        return shares_needed
    
    def execute_hedge(self, current_price: float, shares: int) -> Dict:
        """
        Execute a hedge trade (paper or live)
        
        Returns trade details
        """
        if shares == 0:
            return {"action": "none", "reason": "No hedge needed"}
        
        now = datetime.now()
        
        # Check minimum interval
        if self.last_hedge_time:
            elapsed = (now - self.last_hedge_time).total_seconds()
            if elapsed < self.min_hedge_interval:
                return {"action": "skipped", "reason": f"Min interval not met ({elapsed:.0f}s < {self.min_hedge_interval}s)"}
        
        action = "buy" if shares > 0 else "sell"
        abs_shares = abs(shares)
        
        # Calculate P&L for this hedge
        if action == "buy":
            cost = abs_shares * current_price
            self.realized_pnl -= cost  # Buying costs money
        else:
            proceeds = abs_shares * current_price
            self.realized_pnl += proceeds  # Selling generates money
        
        # Update position
        self.current_stock_position += shares
        self.last_hedge_time = now
        
        # Update reference price
        self.reference_price = current_price
        
        trade = {
            "timestamp": now.isoformat(),
            "action": action,
            "shares": abs_shares,
            "price": current_price,
            "cost_basis": abs_shares * current_price,
            "stock_position": self.current_stock_position,
            "delta_after": self.calculate_current_delta(current_price),
            "realized_pnl": self.realized_pnl,
            "paper_mode": self.paper_mode
        }
        
        self.hedge_history.append(trade)
        
        return trade
    
    def get_status(self, current_price: float) -> Dict:
        """Get current scalper status"""
        current_delta = self.calculate_current_delta(current_price)
        
        # Calculate unrealized P&L from stock position
        if self.reference_price:
            price_change = current_price - self.reference_price
            self.unrealized_pnl = self.current_stock_position * price_change
        
        return {
            "ticker": self.ticker,
            "current_price": current_price,
            "is_running": self.is_running,
            "paper_mode": self.paper_mode,
            "position": {
                "option_delta": self.position_delta,
                "option_gamma": self.position_gamma,
                "stock_shares": self.current_stock_position,
                "net_delta": round(current_delta, 4),
                "delta_dollars": round(current_delta * 100 * current_price, 2)
            },
            "pnl": {
                "realized": round(self.realized_pnl, 2),
                "unrealized": round(self.unrealized_pnl, 2),
                "total": round(self.realized_pnl + self.unrealized_pnl, 2)
            },
            "settings": {
                "hedge_threshold": self.hedge_threshold,
                "max_hedge_size": self.max_hedge_size,
                "min_hedge_interval": self.min_hedge_interval
            },
            "stats": {
                "total_hedges": len(self.hedge_history),
                "last_hedge": self.hedge_history[-1] if self.hedge_history else None
            }
        }
    
    async def tick(self, current_price: float) -> Optional[Dict]:
        """
        Process one tick of the scalper
        Returns trade if one was executed, None otherwise
        """
        if not self.is_running:
            return None
        
        hedge_size = self.calculate_hedge_size(current_price)
        
        if hedge_size != 0:
            return self.execute_hedge(current_price, hedge_size)
        
        return None
    
    def start(self):
        """Start the scalper"""
        self.is_running = True
    
    def stop(self):
        """Stop the scalper"""
        self.is_running = False


# Singleton instance for API
_active_scalpers: Dict[str, GammaScalper] = {}


async def create_gamma_scalper(
    ticker: str,
    position_delta: float,
    position_gamma: float,
    hedge_threshold: float = 0.10,
    paper_mode: bool = True
) -> Dict:
    """Create and start a gamma scalper"""
    scalper = GammaScalper(
        ticker=ticker,
        position_delta=position_delta,
        position_gamma=position_gamma,
        hedge_threshold=hedge_threshold,
        paper_mode=paper_mode
    )
    scalper.start()
    _active_scalpers[ticker] = scalper
    
    return {"status": "created", "ticker": ticker}


async def get_scalper_status(ticker: str, current_price: float) -> Optional[Dict]:
    """Get status of an active scalper"""
    scalper = _active_scalpers.get(ticker)
    if scalper:
        return scalper.get_status(current_price)
    return None


async def scalper_tick(ticker: str, current_price: float) -> Optional[Dict]:
    """Process one tick for a scalper"""
    scalper = _active_scalpers.get(ticker)
    if scalper:
        return await scalper.tick(current_price)
    return None


async def stop_scalper(ticker: str) -> Dict:
    """Stop a scalper"""
    scalper = _active_scalpers.get(ticker)
    if scalper:
        scalper.stop()
        return scalper.get_status(0)
    return {"status": "not_found", "ticker": ticker}
