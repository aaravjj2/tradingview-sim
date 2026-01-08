"""
Auto-Hedge Service
Automatically hedges portfolio delta exposure with SPY options.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from services.alpaca import AlpacaService


class HedgeAction(Enum):
    BUY_SPY_PUTS = "buy_spy_puts"
    BUY_SPY_CALLS = "buy_spy_calls"
    CLOSE_HEDGE = "close_hedge"
    NO_ACTION = "no_action"


@dataclass
class HedgePosition:
    """Active hedge position."""
    hedge_id: str
    option_type: str  # "put" or "call"
    strike: float
    quantity: int
    entry_price: float
    current_price: float = 0.0
    delta_hedged: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "hedge_id": self.hedge_id,
            "option_type": self.option_type,
            "strike": self.strike,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "delta_hedged": self.delta_hedged,
            "pnl": (self.current_price - self.entry_price) * self.quantity * 100,
            "opened_at": self.opened_at.isoformat()
        }


@dataclass
class HedgeRecommendation:
    """Recommended hedge action."""
    action: HedgeAction
    reason: str
    current_delta: float
    target_delta: float
    contracts_needed: int
    option_type: str
    estimated_cost: float
    urgency: str  # "low", "medium", "high"


class AutoHedger:
    """
    Automatic Delta Hedger
    
    Monitors portfolio delta and hedges with SPY options when exposure
    exceeds configured thresholds.
    
    Rules:
    - If Delta > +500: Buy SPY Puts
    - If Delta < -500: Buy SPY Calls
    - Target: Keep Delta between -100 and +100
    """
    
    def __init__(self, alpaca_service: Optional[AlpacaService] = None):
        self.alpaca = alpaca_service or AlpacaService()
        self.active_hedges: Dict[str, HedgePosition] = {}
        self.hedge_history: List[HedgePosition] = []
        
        # Configuration
        self.delta_upper_threshold = 500
        self.delta_lower_threshold = -500
        self.target_delta_upper = 100
        self.target_delta_lower = -100
        self.spy_delta_per_contract = 50  # Approximate delta for ATM SPY option
        
        # State
        self.current_portfolio_delta = 0.0
        self.auto_hedge_enabled = True
        self.last_check = None
    
    def analyze(self, portfolio_delta: float) -> HedgeRecommendation:
        """
        Analyze portfolio delta and recommend hedge action.
        
        Args:
            portfolio_delta: Current portfolio delta exposure
            
        Returns:
            HedgeRecommendation with action and details
        """
        self.current_portfolio_delta = portfolio_delta
        
        # Check if within acceptable range
        if self.target_delta_lower <= portfolio_delta <= self.target_delta_upper:
            return HedgeRecommendation(
                action=HedgeAction.NO_ACTION,
                reason="Portfolio delta within acceptable range",
                current_delta=portfolio_delta,
                target_delta=0,
                contracts_needed=0,
                option_type="none",
                estimated_cost=0,
                urgency="low"
            )
        
        # Calculate hedge needed
        if portfolio_delta > self.delta_upper_threshold:
            # Too long - need puts
            delta_to_hedge = portfolio_delta - self.target_delta_upper
            contracts = int(abs(delta_to_hedge) / self.spy_delta_per_contract) + 1
            
            urgency = "high" if portfolio_delta > 800 else "medium"
            
            return HedgeRecommendation(
                action=HedgeAction.BUY_SPY_PUTS,
                reason=f"Portfolio too long (+{portfolio_delta:.0f} delta), buying puts to neutralize",
                current_delta=portfolio_delta,
                target_delta=self.target_delta_upper,
                contracts_needed=contracts,
                option_type="put",
                estimated_cost=contracts * 2.50 * 100,  # Estimate $2.50 per contract
                urgency=urgency
            )
        
        elif portfolio_delta < self.delta_lower_threshold:
            # Too short - need calls
            delta_to_hedge = abs(portfolio_delta) - abs(self.target_delta_lower)
            contracts = int(delta_to_hedge / self.spy_delta_per_contract) + 1
            
            urgency = "high" if portfolio_delta < -800 else "medium"
            
            return HedgeRecommendation(
                action=HedgeAction.BUY_SPY_CALLS,
                reason=f"Portfolio too short ({portfolio_delta:.0f} delta), buying calls to neutralize",
                current_delta=portfolio_delta,
                target_delta=self.target_delta_lower,
                contracts_needed=contracts,
                option_type="call",
                estimated_cost=contracts * 2.50 * 100,
                urgency=urgency
            )
        
        # Between thresholds but outside target
        return HedgeRecommendation(
            action=HedgeAction.NO_ACTION,
            reason="Delta elevated but within threshold",
            current_delta=portfolio_delta,
            target_delta=0,
            contracts_needed=0,
            option_type="none",
            estimated_cost=0,
            urgency="low"
        )
    
    async def execute_hedge(
        self, 
        recommendation: HedgeRecommendation,
        paper_mode: bool = True
    ) -> Optional[HedgePosition]:
        """Execute the recommended hedge."""
        if recommendation.action == HedgeAction.NO_ACTION:
            return None
        
        try:
            # Get current SPY price
            spy_data = await self.alpaca.get_current_price("SPY")
            spy_price = spy_data["price"] if spy_data else 580
            
            # Calculate strike (ATM)
            strike = round(spy_price / 5) * 5  # Round to nearest $5
            
            hedge_id = f"HEDGE_{datetime.now().strftime('%H%M%S')}"
            
            if paper_mode:
                # Simulate execution
                entry_price = 2.50  # Mock price
                
                hedge = HedgePosition(
                    hedge_id=hedge_id,
                    option_type=recommendation.option_type,
                    strike=strike,
                    quantity=recommendation.contracts_needed,
                    entry_price=entry_price,
                    current_price=entry_price,
                    delta_hedged=recommendation.contracts_needed * self.spy_delta_per_contract
                )
                
                self.active_hedges[hedge_id] = hedge
                
                print(f"[AutoHedge] [PAPER] Opened hedge: {hedge.quantity}x SPY {strike} {hedge.option_type}")
                
                return hedge
            else:
                # Real execution would go here
                pass
                
        except Exception as e:
            print(f"[AutoHedge] Error executing hedge: {e}")
            return None
    
    async def check_and_hedge(self, portfolio_delta: float, paper_mode: bool = True) -> Optional[HedgePosition]:
        """Full cycle: analyze and execute if needed."""
        if not self.auto_hedge_enabled:
            return None
        
        recommendation = self.analyze(portfolio_delta)
        self.last_check = datetime.now()
        
        if recommendation.action != HedgeAction.NO_ACTION:
            return await self.execute_hedge(recommendation, paper_mode)
        
        return None
    
    async def close_hedge(self, hedge_id: str, paper_mode: bool = True) -> bool:
        """Close an active hedge position."""
        if hedge_id not in self.active_hedges:
            return False
        
        hedge = self.active_hedges[hedge_id]
        
        if paper_mode:
            print(f"[AutoHedge] [PAPER] Closed hedge: {hedge.quantity}x SPY {hedge.strike} {hedge.option_type}")
        
        self.hedge_history.append(hedge)
        del self.active_hedges[hedge_id]
        
        return True
    
    def get_status(self) -> Dict:
        """Get current hedger status."""
        total_delta_hedged = sum(h.delta_hedged for h in self.active_hedges.values())
        
        return {
            "enabled": self.auto_hedge_enabled,
            "current_portfolio_delta": self.current_portfolio_delta,
            "total_delta_hedged": total_delta_hedged,
            "net_delta": self.current_portfolio_delta - total_delta_hedged,
            "active_hedges": len(self.active_hedges),
            "hedges": [h.to_dict() for h in self.active_hedges.values()],
            "last_check": self.last_check.isoformat() if self.last_check else None
        }


# Singleton
_auto_hedger: Optional[AutoHedger] = None

def get_auto_hedger() -> AutoHedger:
    global _auto_hedger
    if _auto_hedger is None:
        _auto_hedger = AutoHedger()
    return _auto_hedger
