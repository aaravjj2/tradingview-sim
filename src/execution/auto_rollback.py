"""
Auto-Rollback System

Implements automatic rollback when kill switches trigger.
Closes all positions and reverts to paper mode immediately.
"""

import os
import sys
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class RollbackReason(Enum):
    SLIPPAGE_BREACH = "slippage_breach"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    FILL_MISS_RATE = "fill_miss_rate"
    API_ERROR = "api_error"
    MANUAL = "manual"
    KILL_SWITCH = "kill_switch"


@dataclass
class RollbackEvent:
    """Records a rollback event."""
    timestamp: str
    reason: RollbackReason
    details: str
    positions_closed: List[Dict]
    orders_cancelled: List[Dict]
    final_pnl: float
    operator: str


class AutoRollback:
    """
    Automatic rollback system for live pilot mode.
    
    Monitors kill switch conditions and executes immediate
    rollback when triggered.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            "slippage_breach_bps": 50,
            "daily_loss_pct": 1.0,
            "fill_miss_rate_pct": 5.0,
            "max_consecutive_api_errors": 3,
        }
        
        self.api_error_count = 0
        self.daily_pnl = 0.0
        self.positions: List[Dict] = []
        self.pending_orders: List[Dict] = []
        self.rollback_log: List[RollbackEvent] = []
        self.is_rolled_back = False
    
    def check_slippage_breach(self, expected_price: float, 
                               actual_price: float) -> bool:
        """Check if slippage exceeds threshold."""
        slippage_bps = abs(actual_price - expected_price) / expected_price * 10000
        return slippage_bps > self.config["slippage_breach_bps"]
    
    def check_daily_loss_limit(self, current_pnl: float, 
                                capital: float) -> bool:
        """Check if daily loss exceeds limit."""
        loss_pct = abs(min(0, current_pnl)) / capital * 100
        return loss_pct > self.config["daily_loss_pct"]
    
    def check_fill_miss_rate(self, orders_sent: int, 
                              fills_received: int) -> bool:
        """Check if fill miss rate exceeds threshold."""
        if orders_sent == 0:
            return False
        miss_rate = (orders_sent - fills_received) / orders_sent * 100
        return miss_rate > self.config["fill_miss_rate_pct"]
    
    def record_api_error(self) -> bool:
        """Record an API error and check if threshold exceeded."""
        self.api_error_count += 1
        return self.api_error_count >= self.config["max_consecutive_api_errors"]
    
    def clear_api_errors(self):
        """Clear API error count on successful request."""
        self.api_error_count = 0
    
    def execute_rollback(self, reason: RollbackReason, 
                         details: str = "",
                         operator: str = "auto") -> RollbackEvent:
        """
        Execute immediate rollback.
        
        1. Cancel all pending orders
        2. Close all positions at market
        3. Revert to paper mode
        4. Log event
        """
        if self.is_rolled_back:
            print("Already rolled back - skipping")
            return None
        
        print("\n" + "!" * 60)
        print("!!! ROLLBACK INITIATED !!!")
        print("!" * 60)
        print(f"Reason: {reason.value}")
        print(f"Details: {details}")
        
        # Cancel pending orders
        cancelled_orders = []
        for order in self.pending_orders:
            cancelled_orders.append({
                "order_id": order.get("id", "unknown"),
                "symbol": order.get("symbol", "unknown"),
                "status": "cancelled",
            })
            print(f"  Cancelled order: {order.get('id', 'unknown')}")
        
        # Close positions at market
        closed_positions = []
        final_pnl = 0.0
        for position in self.positions:
            # Simulate market close
            close_result = {
                "symbol": position.get("symbol", "unknown"),
                "shares": position.get("shares", 0),
                "close_price": position.get("current_price", 0),
                "pnl": position.get("unrealized_pnl", 0),
            }
            closed_positions.append(close_result)
            final_pnl += close_result["pnl"]
            print(f"  Closed position: {position.get('symbol')} ({position.get('shares')} shares)")
        
        # Create event
        event = RollbackEvent(
            timestamp=datetime.now().isoformat(),
            reason=reason,
            details=details,
            positions_closed=closed_positions,
            orders_cancelled=cancelled_orders,
            final_pnl=final_pnl,
            operator=operator,
        )
        
        self.rollback_log.append(event)
        self.is_rolled_back = True
        
        # Clear state
        self.positions.clear()
        self.pending_orders.clear()
        
        # Set environment to paper (in real implementation)
        os.environ["TRADING_MODE"] = "paper"
        
        print("\n" + "=" * 60)
        print("ROLLBACK COMPLETE")
        print("=" * 60)
        print(f"Positions Closed: {len(closed_positions)}")
        print(f"Orders Cancelled: {len(cancelled_orders)}")
        print(f"Final P&L: ${final_pnl:.2f}")
        print(f"Mode: PAPER (reverted)")
        print("=" * 60)
        
        # Save rollback log
        self._save_rollback_log(event)
        
        return event
    
    def _save_rollback_log(self, event: RollbackEvent):
        """Save rollback event to file."""
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts", "rollback_logs"
        )
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(log_file, "w") as f:
            json.dump({
                "timestamp": event.timestamp,
                "reason": event.reason.value,
                "details": event.details,
                "positions_closed": event.positions_closed,
                "orders_cancelled": event.orders_cancelled,
                "final_pnl": event.final_pnl,
                "operator": event.operator,
            }, f, indent=2)
        
        print(f"Rollback log saved: {log_file}")
    
    def add_position(self, position: Dict):
        """Add a position to track."""
        self.positions.append(position)
    
    def add_pending_order(self, order: Dict):
        """Add a pending order to track."""
        self.pending_orders.append(order)
    
    def update_pnl(self, pnl: float):
        """Update daily P&L."""
        self.daily_pnl = pnl
    
    def get_status(self) -> Dict:
        """Get current rollback system status."""
        return {
            "is_rolled_back": self.is_rolled_back,
            "positions_count": len(self.positions),
            "pending_orders_count": len(self.pending_orders),
            "api_error_count": self.api_error_count,
            "daily_pnl": self.daily_pnl,
            "rollback_events": len(self.rollback_log),
        }


# Global rollback instance
_rollback_system: Optional[AutoRollback] = None


def get_rollback_system() -> AutoRollback:
    """Get or create the rollback system singleton."""
    global _rollback_system
    if _rollback_system is None:
        _rollback_system = AutoRollback()
    return _rollback_system


def trigger_emergency_rollback(reason: str, details: str = ""):
    """Trigger emergency rollback from anywhere."""
    system = get_rollback_system()
    system.execute_rollback(RollbackReason.MANUAL, f"{reason}: {details}", "manual")


if __name__ == "__main__":
    # Test rollback
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Rollback System")
    parser.add_argument("--reason", type=str, default="manual", help="Rollback reason")
    parser.add_argument("--test", action="store_true", help="Run test rollback")
    args = parser.parse_args()
    
    if args.test:
        system = AutoRollback()
        
        # Add test positions
        system.add_position({"symbol": "SPY", "shares": 10, "current_price": 590, "unrealized_pnl": -15})
        system.add_pending_order({"id": "TEST-001", "symbol": "SPY", "side": "buy"})
        
        # Execute rollback
        system.execute_rollback(RollbackReason.MANUAL, "Test rollback", "test_operator")
