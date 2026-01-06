"""
Strategy Module for Options Supergraph Dashboard
Decoupled Strategy class for algo-readiness and bot compatibility
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np
import json
from enum import Enum


class OptionType(Enum):
    CALL = "call"
    PUT = "put"
    STOCK = "stock"


class PositionType(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class OptionLeg:
    """Represents a single option leg in a strategy"""
    option_type: str  # 'call', 'put', or 'stock'
    position: str  # 'long' or 'short'
    strike: float
    premium: float
    quantity: int
    expiration_days: int
    iv: float = 0.30
    symbol: str = ""
    
    @property
    def sign(self) -> int:
        """Returns +1 for long positions, -1 for short positions"""
        return 1 if self.position == "long" else -1
    
    def to_dict(self) -> Dict:
        """Serialize leg to dictionary"""
        return {
            "option_type": self.option_type,
            "position": self.position,
            "strike": self.strike,
            "premium": self.premium,
            "quantity": self.quantity,
            "expiration_days": self.expiration_days,
            "iv": self.iv,
            "symbol": self.symbol
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OptionLeg":
        """Deserialize leg from dictionary"""
        return cls(
            option_type=data["option_type"],
            position=data["position"],
            strike=data["strike"],
            premium=data["premium"],
            quantity=data["quantity"],
            expiration_days=data["expiration_days"],
            iv=data.get("iv", 0.30),
            symbol=data.get("symbol", "")
        )


@dataclass
class Strategy:
    """
    Represents a complete options strategy.
    Designed for serialization and use by trading bots.
    """
    name: str
    ticker: str
    legs: List[OptionLeg] = field(default_factory=list)
    max_risk: float = 0.0  # Maximum loss
    profit_target: float = 0.0  # Target profit
    stop_loss: float = 0.0  # Stop loss level
    created_at: str = ""
    notes: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()
        
        # Calculate max risk if not set
        if self.max_risk == 0 and self.legs:
            self._calculate_risk_metrics()
    
    def _calculate_risk_metrics(self):
        """Calculate max loss and profit from legs"""
        # This will be calculated by the payoff functions
        pass
    
    @property
    def is_defined_risk(self) -> bool:
        """Check if this is a defined-risk strategy (e.g., spreads, iron condor)"""
        # A strategy is defined risk if it has both long and short positions
        # in the same option type
        has_long_call = any(l for l in self.legs if l.option_type == "call" and l.sign > 0)
        has_short_call = any(l for l in self.legs if l.option_type == "call" and l.sign < 0)
        has_long_put = any(l for l in self.legs if l.option_type == "put" and l.sign > 0)
        has_short_put = any(l for l in self.legs if l.option_type == "put" and l.sign < 0)
        
        return (has_long_call and has_short_call) or (has_long_put and has_short_put)
    
    @property
    def net_premium(self) -> float:
        """Calculate net premium paid (positive) or received (negative)"""
        return sum(leg.premium * leg.quantity * 100 * leg.sign for leg in self.legs 
                   if leg.option_type != "stock")
    
    @property
    def total_contracts(self) -> int:
        """Total number of option contracts"""
        return sum(leg.quantity for leg in self.legs if leg.option_type != "stock")
    
    def add_leg(self, leg: OptionLeg):
        """Add a leg to the strategy"""
        self.legs.append(leg)
        self._calculate_risk_metrics()
    
    def remove_leg(self, index: int):
        """Remove a leg by index"""
        if 0 <= index < len(self.legs):
            self.legs.pop(index)
            self._calculate_risk_metrics()
    
    def calculate_payoff_at_expiry(self, price_range: np.ndarray) -> np.ndarray:
        """
        Calculate P/L at expiration for the strategy
        
        Args:
            price_range: Array of stock prices
            
        Returns:
            Array of P/L values
        """
        payoff = np.zeros_like(price_range, dtype=float)
        
        for leg in self.legs:
            if leg.option_type == "stock":
                leg_payoff = (price_range - leg.strike) * leg.quantity * leg.sign
            elif leg.option_type == "call":
                intrinsic = np.maximum(0, price_range - leg.strike)
                leg_payoff = (intrinsic - leg.premium) * 100 * leg.quantity * leg.sign
            else:  # put
                intrinsic = np.maximum(0, leg.strike - price_range)
                leg_payoff = (intrinsic - leg.premium) * 100 * leg.quantity * leg.sign
            
            payoff += leg_payoff
        
        return payoff
    
    def to_dict(self) -> Dict:
        """Serialize strategy to dictionary"""
        return {
            "name": self.name,
            "ticker": self.ticker,
            "legs": [leg.to_dict() for leg in self.legs],
            "max_risk": self.max_risk,
            "profit_target": self.profit_target,
            "stop_loss": self.stop_loss,
            "created_at": self.created_at,
            "notes": self.notes
        }
    
    def to_json(self) -> str:
        """Serialize strategy to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Strategy":
        """Deserialize strategy from dictionary"""
        legs = [OptionLeg.from_dict(leg) for leg in data.get("legs", [])]
        return cls(
            name=data["name"],
            ticker=data["ticker"],
            legs=legs,
            max_risk=data.get("max_risk", 0.0),
            profit_target=data.get("profit_target", 0.0),
            stop_loss=data.get("stop_loss", 0.0),
            created_at=data.get("created_at", ""),
            notes=data.get("notes", "")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Strategy":
        """Deserialize strategy from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def clone(self) -> "Strategy":
        """Create a deep copy of the strategy"""
        return Strategy.from_dict(self.to_dict())


class StrategyBuilder:
    """Factory class for creating common strategies"""
    
    @staticmethod
    def long_call(ticker: str, strike: float, premium: float, 
                  expiration_days: int, iv: float = 0.30) -> Strategy:
        """Create a long call strategy"""
        strategy = Strategy(name="Long Call", ticker=ticker)
        strategy.add_leg(OptionLeg(
            option_type="call",
            position="long",
            strike=strike,
            premium=premium,
            quantity=1,
            expiration_days=expiration_days,
            iv=iv
        ))
        return strategy
    
    @staticmethod
    def long_put(ticker: str, strike: float, premium: float,
                 expiration_days: int, iv: float = 0.30) -> Strategy:
        """Create a long put strategy"""
        strategy = Strategy(name="Long Put", ticker=ticker)
        strategy.add_leg(OptionLeg(
            option_type="put",
            position="long",
            strike=strike,
            premium=premium,
            quantity=1,
            expiration_days=expiration_days,
            iv=iv
        ))
        return strategy
    
    @staticmethod
    def bull_call_spread(ticker: str, long_strike: float, short_strike: float,
                         long_premium: float, short_premium: float,
                         expiration_days: int, iv: float = 0.30) -> Strategy:
        """Create a bull call spread"""
        strategy = Strategy(name="Bull Call Spread", ticker=ticker)
        strategy.add_leg(OptionLeg(
            option_type="call",
            position="long",
            strike=long_strike,
            premium=long_premium,
            quantity=1,
            expiration_days=expiration_days,
            iv=iv
        ))
        strategy.add_leg(OptionLeg(
            option_type="call",
            position="short",
            strike=short_strike,
            premium=short_premium,
            quantity=1,
            expiration_days=expiration_days,
            iv=iv
        ))
        return strategy
    
    @staticmethod
    def iron_condor(ticker: str, put_long: float, put_short: float,
                    call_short: float, call_long: float,
                    premiums: Dict[str, float], expiration_days: int,
                    iv: float = 0.30) -> Strategy:
        """
        Create an iron condor
        
        Args:
            put_long: Lower put strike (protection)
            put_short: Upper put strike (sold)
            call_short: Lower call strike (sold)
            call_long: Upper call strike (protection)
            premiums: Dict with keys 'put_long', 'put_short', 'call_short', 'call_long'
        """
        strategy = Strategy(name="Iron Condor", ticker=ticker)
        
        # Long put (lower wing protection)
        strategy.add_leg(OptionLeg(
            option_type="put", position="long",
            strike=put_long, premium=premiums.get("put_long", 0),
            quantity=1, expiration_days=expiration_days, iv=iv
        ))
        
        # Short put (credit)
        strategy.add_leg(OptionLeg(
            option_type="put", position="short",
            strike=put_short, premium=premiums.get("put_short", 0),
            quantity=1, expiration_days=expiration_days, iv=iv
        ))
        
        # Short call (credit)
        strategy.add_leg(OptionLeg(
            option_type="call", position="short",
            strike=call_short, premium=premiums.get("call_short", 0),
            quantity=1, expiration_days=expiration_days, iv=iv
        ))
        
        # Long call (upper wing protection)
        strategy.add_leg(OptionLeg(
            option_type="call", position="long",
            strike=call_long, premium=premiums.get("call_long", 0),
            quantity=1, expiration_days=expiration_days, iv=iv
        ))
        
        return strategy
    
    @staticmethod
    def straddle(ticker: str, strike: float, call_premium: float,
                 put_premium: float, expiration_days: int,
                 position: str = "long", iv: float = 0.30) -> Strategy:
        """Create a straddle (long or short)"""
        name = f"{'Long' if position == 'long' else 'Short'} Straddle"
        strategy = Strategy(name=name, ticker=ticker)
        
        strategy.add_leg(OptionLeg(
            option_type="call", position=position,
            strike=strike, premium=call_premium,
            quantity=1, expiration_days=expiration_days, iv=iv
        ))
        strategy.add_leg(OptionLeg(
            option_type="put", position=position,
            strike=strike, premium=put_premium,
            quantity=1, expiration_days=expiration_days, iv=iv
        ))
        
        return strategy
    
    @staticmethod
    def covered_call(ticker: str, stock_price: float, call_strike: float,
                     call_premium: float, expiration_days: int,
                     iv: float = 0.30) -> Strategy:
        """Create a covered call (100 shares + short call)"""
        strategy = Strategy(name="Covered Call", ticker=ticker)
        
        # Long stock
        strategy.add_leg(OptionLeg(
            option_type="stock", position="long",
            strike=stock_price, premium=0,
            quantity=100, expiration_days=expiration_days
        ))
        
        # Short call
        strategy.add_leg(OptionLeg(
            option_type="call", position="short",
            strike=call_strike, premium=call_premium,
            quantity=1, expiration_days=expiration_days, iv=iv
        ))
        
        return strategy
