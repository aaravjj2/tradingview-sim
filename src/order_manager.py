"""
Order Manager with Idempotent Order Placement

Handles order submission with deterministic client_order_id generation
to ensure idempotent order placement.

PAPER-ONLY: This module enforces paper trading mode.
"""

import os
import json
import hashlib
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import sqlite3

# Safety enforcement
TRADING_MODE = os.environ.get("TRADING_MODE", "paper")

if TRADING_MODE == "live":
    raise RuntimeError(
        "TRADING_MODE=live is not allowed. "
        "This system is paper-only. Set TRADING_MODE=paper."
    )


@dataclass
class Order:
    """Represents an order in the system."""
    client_order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    qty: int
    order_type: str  # "market", "limit"
    limit_price: Optional[float]
    status: str  # "pending", "submitted", "filled", "cancelled", "rejected"
    trade_plan_id: str
    created_at: str
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    filled_price: Optional[float] = None
    filled_qty: Optional[int] = None
    broker_order_id: Optional[str] = None
    error_message: Optional[str] = None


class OrderManager:
    """
    Manages order lifecycle with idempotent placement.
    
    Uses deterministic client_order_id based on trade plan hash + date
    to ensure the same trade plan only results in one order.
    """
    
    def __init__(self, db_path: str = "trading_data.db"):
        self.db_path = db_path
        self.orders: Dict[str, Order] = {}
        self._ensure_tables()
        self._load_orders()
    
    def _ensure_tables(self):
        """Create order tracking tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    client_order_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    order_type TEXT NOT NULL,
                    limit_price REAL,
                    status TEXT NOT NULL,
                    trade_plan_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    submitted_at TEXT,
                    filled_at TEXT,
                    filled_price REAL,
                    filled_qty INTEGER,
                    broker_order_id TEXT,
                    error_message TEXT
                )
            """)
            conn.commit()
    
    def _load_orders(self):
        """Load existing orders from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM orders").fetchall()
            
            for row in rows:
                order = Order(
                    client_order_id=row["client_order_id"],
                    symbol=row["symbol"],
                    side=row["side"],
                    qty=row["qty"],
                    order_type=row["order_type"],
                    limit_price=row["limit_price"],
                    status=row["status"],
                    trade_plan_id=row["trade_plan_id"],
                    created_at=row["created_at"],
                    submitted_at=row["submitted_at"],
                    filled_at=row["filled_at"],
                    filled_price=row["filled_price"],
                    filled_qty=row["filled_qty"],
                    broker_order_id=row["broker_order_id"],
                    error_message=row["error_message"]
                )
                self.orders[order.client_order_id] = order
    
    def _save_order(self, order: Order):
        """Save order to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO orders (
                    client_order_id, symbol, side, qty, order_type, limit_price,
                    status, trade_plan_id, created_at, submitted_at, filled_at,
                    filled_price, filled_qty, broker_order_id, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.client_order_id, order.symbol, order.side, order.qty,
                order.order_type, order.limit_price, order.status,
                order.trade_plan_id, order.created_at, order.submitted_at,
                order.filled_at, order.filled_price, order.filled_qty,
                order.broker_order_id, order.error_message
            ))
            conn.commit()
    
    def generate_client_order_id(self, trade_plan: Dict[str, Any], execution_date: date) -> str:
        """
        Generate a deterministic client_order_id.
        
        The ID is derived from:
        - SHA256 hash of the trade plan
        - Execution date
        
        This ensures the same trade plan on the same day always produces
        the same client_order_id, enabling idempotent order placement.
        
        Args:
            trade_plan: Trade plan dictionary
            execution_date: Date of execution
            
        Returns:
            Deterministic client order ID
        """
        # Create deterministic hash of trade plan
        plan_content = {
            "trade_plan_id": trade_plan.get("trade_plan_id"),
            "symbol": trade_plan.get("symbol"),
            "target_shares": trade_plan.get("target_shares"),
            "snapshot_hash": trade_plan.get("snapshot_hash")
        }
        plan_str = json.dumps(plan_content, sort_keys=True)
        plan_hash = hashlib.sha256(plan_str.encode()).hexdigest()[:16]
        
        # Combine with date for uniqueness per day
        date_str = execution_date.strftime("%Y%m%d")
        
        return f"VG-{date_str}-{plan_hash}"
    
    def place_order(
        self,
        trade_plan: Dict[str, Any],
        execution_date: date,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        adv_fraction_cap: float = 0.01
    ) -> Dict[str, Any]:
        """
        Place an order with idempotent handling.
        
        If an order with the same client_order_id already exists,
        returns the existing order without placing a duplicate.
        
        Args:
            trade_plan: Trade plan from signal generator
            execution_date: Date for order execution
            order_type: "market" or "limit"
            limit_price: Required if order_type is "limit"
            adv_fraction_cap: Max fraction of ADV per order
            
        Returns:
            Order status dict
        """
        # Generate deterministic client order ID
        client_order_id = self.generate_client_order_id(trade_plan, execution_date)
        
        # Check for existing order (idempotency)
        if client_order_id in self.orders:
            existing = self.orders[client_order_id]
            return {
                "status": "already_exists",
                "client_order_id": client_order_id,
                "order_status": existing.status,
                "message": "Order already exists - idempotent skip"
            }
        
        # Validate ADV constraint
        target_shares = trade_plan.get("target_shares", 0)
        # Note: In production, would fetch real ADV and validate
        # For now, trust the trade plan's calculation
        
        # Create order
        order = Order(
            client_order_id=client_order_id,
            symbol=trade_plan.get("symbol", "SPY"),
            side=trade_plan.get("action", "buy"),
            qty=target_shares,
            order_type=order_type,
            limit_price=limit_price,
            status="pending",
            trade_plan_id=trade_plan.get("trade_plan_id", ""),
            created_at=datetime.now().isoformat()
        )
        
        # Store order
        self.orders[client_order_id] = order
        self._save_order(order)
        
        return {
            "status": "created",
            "client_order_id": client_order_id,
            "order": asdict(order)
        }
    
    def submit_order(self, client_order_id: str) -> Dict[str, Any]:
        """
        Submit a pending order for execution.
        
        In paper mode, this simulates order submission.
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            Submission status
        """
        if client_order_id not in self.orders:
            return {"status": "error", "message": "Order not found"}
        
        order = self.orders[client_order_id]
        
        if order.status != "pending":
            return {
                "status": "already_processed",
                "order_status": order.status
            }
        
        # Update order status
        order.status = "submitted"
        order.submitted_at = datetime.now().isoformat()
        
        # In paper mode, simulate immediate fill
        if TRADING_MODE == "paper":
            order.broker_order_id = f"PAPER-{client_order_id}"
            # Note: In real implementation, would get actual fill price
            # For now, mark as pending fill
        
        self._save_order(order)
        
        return {
            "status": "submitted",
            "client_order_id": client_order_id,
            "broker_order_id": order.broker_order_id
        }
    
    def fill_order(
        self,
        client_order_id: str,
        filled_price: float,
        filled_qty: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Record an order fill.
        
        Args:
            client_order_id: Client order ID
            filled_price: Execution price
            filled_qty: Filled quantity (defaults to order qty)
            
        Returns:
            Fill status
        """
        if client_order_id not in self.orders:
            return {"status": "error", "message": "Order not found"}
        
        order = self.orders[client_order_id]
        
        order.status = "filled"
        order.filled_at = datetime.now().isoformat()
        order.filled_price = filled_price
        order.filled_qty = filled_qty or order.qty
        
        self._save_order(order)
        
        return {
            "status": "filled",
            "client_order_id": client_order_id,
            "filled_price": filled_price,
            "filled_qty": order.filled_qty
        }
    
    def get_order(self, client_order_id: str) -> Optional[Order]:
        """Get order by client order ID."""
        return self.orders.get(client_order_id)
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders."""
        return [o for o in self.orders.values() if o.status == "pending"]
    
    def get_orders_by_date(self, target_date: date) -> List[Order]:
        """Get all orders for a specific date."""
        date_str = target_date.strftime("%Y%m%d")
        return [o for o in self.orders.values() if f"-{date_str}-" in o.client_order_id]


# Singleton instance
_order_manager: Optional[OrderManager] = None


def get_order_manager(db_path: str = "trading_data.db") -> OrderManager:
    """Get or create the singleton OrderManager instance."""
    global _order_manager
    if _order_manager is None:
        _order_manager = OrderManager(db_path)
    return _order_manager
