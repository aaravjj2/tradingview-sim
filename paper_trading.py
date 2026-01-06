"""
Paper Trading Module for Options Supergraph Dashboard
Mock trading ledger for testing strategies without real money
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
import json

from database import get_connection
from strategy import Strategy, OptionLeg


@dataclass
class Position:
    """Represents an open position"""
    id: int
    ticker: str
    position_type: str  # 'stock' or 'option'
    quantity: int
    entry_price: float
    strike: Optional[float] = None
    expiration: Optional[str] = None
    option_type: Optional[str] = None  # 'call' or 'put'
    opened_at: str = ""
    current_value: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class Trade:
    """Represents an executed trade"""
    id: int
    ticker: str
    action: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    total_value: float
    strategy_name: Optional[str] = None
    executed_at: str = ""


class PaperAccount:
    """
    Mock trading account for paper trading.
    Tracks balance, positions, and trade history.
    """
    
    def __init__(self):
        self._ensure_account_exists()
    
    def _ensure_account_exists(self):
        """Ensure account record exists in database"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO paper_account (id, balance, initial_balance)
                VALUES (1, 100000.0, 100000.0)
            """)
            conn.commit()
    
    @property
    def balance(self) -> float:
        """Get current account balance"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM paper_account WHERE id = 1")
            row = cursor.fetchone()
            return row["balance"] if row else 100000.0
    
    @balance.setter
    def balance(self, value: float):
        """Set account balance"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE paper_account 
                SET balance = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (value,))
            conn.commit()
    
    @property
    def initial_balance(self) -> float:
        """Get initial account balance"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT initial_balance FROM paper_account WHERE id = 1")
            row = cursor.fetchone()
            return row["initial_balance"] if row else 100000.0
    
    @property
    def total_pnl(self) -> float:
        """Calculate total P/L from initial balance"""
        return self.balance - self.initial_balance
    
    @property
    def pnl_percent(self) -> float:
        """Calculate P/L as percentage"""
        return (self.total_pnl / self.initial_balance) * 100
    
    def reset_account(self, initial_balance: float = 100000.0):
        """Reset account to initial state"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Reset balance
            cursor.execute("""
                UPDATE paper_account 
                SET balance = ?, initial_balance = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (initial_balance, initial_balance))
            
            # Clear positions
            cursor.execute("DELETE FROM paper_positions")
            
            # Clear trade history
            cursor.execute("DELETE FROM trade_history")
            
            conn.commit()
    
    def get_positions(self) -> List[Position]:
        """Get all open positions"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM paper_positions WHERE closed_at IS NULL
            """)
            
            positions = []
            for row in cursor.fetchall():
                positions.append(Position(
                    id=row["id"],
                    ticker=row["ticker"],
                    position_type=row["position_type"],
                    quantity=row["quantity"],
                    entry_price=row["entry_price"],
                    strike=row["strike"],
                    expiration=row["expiration"],
                    option_type=row["option_type"],
                    opened_at=row["opened_at"]
                ))
            
            return positions
    
    def get_position_by_id(self, position_id: int) -> Optional[Position]:
        """Get a specific position by ID"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM paper_positions WHERE id = ?
            """, (position_id,))
            
            row = cursor.fetchone()
            if row:
                return Position(
                    id=row["id"],
                    ticker=row["ticker"],
                    position_type=row["position_type"],
                    quantity=row["quantity"],
                    entry_price=row["entry_price"],
                    strike=row["strike"],
                    expiration=row["expiration"],
                    option_type=row["option_type"],
                    opened_at=row["opened_at"]
                )
            return None
    
    def execute_strategy(self, strategy: Strategy, current_prices: Dict[str, float]) -> bool:
        """
        Execute a complete strategy (open all legs)
        
        Args:
            strategy: Strategy object to execute
            current_prices: Dict mapping leg index to current market price
        
        Returns:
            True if successful, False otherwise
        """
        total_cost = 0.0
        
        # Calculate total cost/credit
        for i, leg in enumerate(strategy.legs):
            # Use provided price or leg premium
            price = current_prices.get(str(i), leg.premium)
            
            if leg.option_type == "stock":
                total_cost += price * leg.quantity * leg.sign
            else:
                # Options: premium * 100 shares per contract * quantity * direction
                total_cost += price * 100 * leg.quantity * leg.sign
        
        # Check if we have enough balance (for debit strategies)
        if total_cost > 0 and total_cost > self.balance:
            print(f"Insufficient funds. Need ${total_cost:.2f}, have ${self.balance:.2f}")
            return False
        
        # Execute each leg
        with get_connection() as conn:
            cursor = conn.cursor()
            
            for i, leg in enumerate(strategy.legs):
                price = current_prices.get(str(i), leg.premium)
                
                # Insert position
                cursor.execute("""
                    INSERT INTO paper_positions 
                    (ticker, position_type, quantity, entry_price, strike, expiration, option_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy.ticker,
                    leg.option_type,
                    leg.quantity * leg.sign,  # Negative for short positions
                    price,
                    leg.strike if leg.option_type != "stock" else None,
                    str(leg.expiration_days) if leg.option_type != "stock" else None,
                    leg.option_type if leg.option_type in ["call", "put"] else None
                ))
                
                # Record trade
                action = "BUY" if leg.sign > 0 else "SELL"
                trade_value = price * (100 if leg.option_type != "stock" else 1) * leg.quantity
                
                cursor.execute("""
                    INSERT INTO trade_history 
                    (ticker, action, quantity, price, total_value, strategy_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    strategy.ticker,
                    action,
                    leg.quantity,
                    price,
                    trade_value,
                    strategy.name
                ))
            
            conn.commit()
        
        # Update balance
        self.balance = self.balance - total_cost
        
        return True
    
    def close_position(self, position_id: int, close_price: float) -> Optional[float]:
        """
        Close a specific position
        
        Args:
            position_id: ID of position to close
            close_price: Current market price
            
        Returns:
            Realized P/L or None if position not found
        """
        position = self.get_position_by_id(position_id)
        if not position:
            return None
        
        # Calculate P/L
        if position.position_type == "stock":
            pnl = (close_price - position.entry_price) * position.quantity
        else:
            # For options: (exit - entry) * 100 * quantity
            # Note: quantity is already negative for short positions
            pnl = (close_price - position.entry_price) * 100 * position.quantity
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Update position as closed
            cursor.execute("""
                UPDATE paper_positions 
                SET closed_at = CURRENT_TIMESTAMP, close_price = ?, pnl = ?
                WHERE id = ?
            """, (close_price, pnl, position_id))
            
            # Record closing trade
            action = "SELL" if position.quantity > 0 else "BUY"
            cursor.execute("""
                INSERT INTO trade_history 
                (ticker, action, quantity, price, total_value, strategy_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                position.ticker,
                action,
                abs(position.quantity),
                close_price,
                abs(close_price * (100 if position.position_type != "stock" else 1) * position.quantity),
                "Close Position"
            ))
            
            conn.commit()
        
        # Update balance with P/L
        self.balance = self.balance + pnl
        
        return pnl
    
    def get_trade_history(self, limit: int = 50) -> List[Trade]:
        """Get recent trade history"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trade_history 
                ORDER BY executed_at DESC LIMIT ?
            """, (limit,))
            
            trades = []
            for row in cursor.fetchall():
                trades.append(Trade(
                    id=row["id"],
                    ticker=row["ticker"],
                    action=row["action"],
                    quantity=row["quantity"],
                    price=row["price"],
                    total_value=row["total_value"],
                    strategy_name=row["strategy_name"],
                    executed_at=row["executed_at"]
                ))
            
            return trades
    
    def get_net_delta(self, current_price: float, 
                      calculate_delta_fn: callable = None) -> float:
        """
        Calculate net delta of all open positions
        
        Args:
            current_price: Current stock price
            calculate_delta_fn: Optional function to calculate option delta
            
        Returns:
            Net delta exposure
        """
        positions = self.get_positions()
        net_delta = 0.0
        
        for pos in positions:
            if pos.position_type == "stock":
                # Stock delta is 1 per share
                net_delta += pos.quantity
            elif calculate_delta_fn and pos.strike:
                # Calculate option delta using provided function
                delta = calculate_delta_fn(
                    current_price, 
                    pos.strike, 
                    pos.option_type
                )
                net_delta += delta * 100 * pos.quantity
        
        return net_delta
    
    def get_summary(self) -> Dict[str, Any]:
        """Get account summary"""
        positions = self.get_positions()
        
        return {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "total_pnl": self.total_pnl,
            "pnl_percent": self.pnl_percent,
            "open_positions": len(positions),
            "positions": [
                {
                    "id": p.id,
                    "ticker": p.ticker,
                    "type": f"{p.option_type or p.position_type}",
                    "quantity": p.quantity,
                    "entry": p.entry_price,
                    "strike": p.strike
                }
                for p in positions
            ]
        }


# Singleton instance
paper_account = PaperAccount()
