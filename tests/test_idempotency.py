"""
Test Idempotency

Verifies that order placement is idempotent:
- Same trade plan posted twice should only result in one order
"""

import os
import sys
import pytest
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.order_manager import OrderManager


class TestIdempotency:
    """Test suite for idempotent order placement."""
    
    @pytest.fixture
    def order_manager(self, tmp_path):
        """Create order manager with temp database."""
        db_path = tmp_path / "test_idempotency.db"
        return OrderManager(str(db_path))
    
    @pytest.fixture
    def sample_trade_plan(self):
        """Sample trade plan for testing."""
        return {
            "trade_plan_id": "TP-001",
            "symbol": "SPY",
            "decision_time": "2026-01-15T15:55:00",
            "action": "buy",
            "target_exposure": 0.7,
            "target_shares": 430,
            "current_price": 589.0,
            "expected_execution_time": "OPEN_T+1",
            "signal_confidence": 0.82,
            "snapshot_hash": "abc123def456",
            "model_version": "volgate-v1.0"
        }
    
    def test_same_plan_twice_creates_one_order(self, order_manager, sample_trade_plan):
        """Posting the same trade plan twice should only create one order."""
        execution_date = date(2026, 1, 16)
        
        # First placement
        result1 = order_manager.place_order(sample_trade_plan, execution_date)
        assert result1["status"] == "created"
        client_order_id = result1["client_order_id"]
        
        # Second placement (same plan, same date)
        result2 = order_manager.place_order(sample_trade_plan, execution_date)
        
        # Should detect as duplicate
        assert result2["status"] == "already_exists"
        assert result2["client_order_id"] == client_order_id
        assert "idempotent" in result2["message"].lower()
        
        # Verify only one order exists
        pending = order_manager.get_pending_orders()
        matching = [o for o in pending if o.trade_plan_id == sample_trade_plan["trade_plan_id"]]
        assert len(matching) == 1
    
    def test_client_order_id_is_deterministic(self, order_manager, sample_trade_plan):
        """Same trade plan should always generate same client_order_id."""
        execution_date = date(2026, 1, 16)
        
        id1 = order_manager.generate_client_order_id(sample_trade_plan, execution_date)
        id2 = order_manager.generate_client_order_id(sample_trade_plan, execution_date)
        
        assert id1 == id2
    
    def test_different_dates_create_different_orders(self, order_manager, sample_trade_plan):
        """Same trade plan on different dates should create different orders."""
        date1 = date(2026, 1, 16)
        date2 = date(2026, 1, 17)
        
        result1 = order_manager.place_order(sample_trade_plan, date1)
        result2 = order_manager.place_order(sample_trade_plan, date2)
        
        assert result1["status"] == "created"
        assert result2["status"] == "created"
        assert result1["client_order_id"] != result2["client_order_id"]
    
    def test_different_plans_create_different_orders(self, order_manager):
        """Different trade plans should create different orders."""
        execution_date = date(2026, 1, 16)
        
        plan1 = {
            "trade_plan_id": "TP-001",
            "symbol": "SPY",
            "target_shares": 100,
            "snapshot_hash": "hash1"
        }
        
        plan2 = {
            "trade_plan_id": "TP-002",
            "symbol": "SPY",
            "target_shares": 200,
            "snapshot_hash": "hash2"
        }
        
        result1 = order_manager.place_order(plan1, execution_date)
        result2 = order_manager.place_order(plan2, execution_date)
        
        assert result1["status"] == "created"
        assert result2["status"] == "created"
        assert result1["client_order_id"] != result2["client_order_id"]
    
    def test_idempotency_after_submission(self, order_manager, sample_trade_plan):
        """Duplicate placement after submission should still be idempotent."""
        execution_date = date(2026, 1, 16)
        
        # First placement and submission
        result1 = order_manager.place_order(sample_trade_plan, execution_date)
        client_order_id = result1["client_order_id"]
        
        order_manager.submit_order(client_order_id)
        
        # Try to place again
        result2 = order_manager.place_order(sample_trade_plan, execution_date)
        
        assert result2["status"] == "already_exists"
        assert result2["order_status"] == "submitted"
    
    def test_idempotency_after_fill(self, order_manager, sample_trade_plan):
        """Duplicate placement after fill should still be idempotent."""
        execution_date = date(2026, 1, 16)
        
        # First placement, submission, and fill
        result1 = order_manager.place_order(sample_trade_plan, execution_date)
        client_order_id = result1["client_order_id"]
        
        order_manager.submit_order(client_order_id)
        order_manager.fill_order(client_order_id, filled_price=589.25)
        
        # Try to place again
        result2 = order_manager.place_order(sample_trade_plan, execution_date)
        
        assert result2["status"] == "already_exists"
        assert result2["order_status"] == "filled"
    
    def test_client_order_id_format(self, order_manager, sample_trade_plan):
        """Client order ID should follow expected format."""
        execution_date = date(2026, 1, 16)
        
        client_order_id = order_manager.generate_client_order_id(sample_trade_plan, execution_date)
        
        # Should start with VG-
        assert client_order_id.startswith("VG-")
        
        # Should contain date
        assert "20260116" in client_order_id
        
        # Should have hash suffix
        parts = client_order_id.split("-")
        assert len(parts) == 3
        assert len(parts[2]) == 16  # 16-char hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
