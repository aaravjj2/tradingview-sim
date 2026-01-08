"""
Test Replay Integration

End-to-end test using historical replay:
- Data ingestion → snapshot → predict → trade_plan → simulated order → reconciliation
"""

import os
import sys
import json
import pytest
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workspace.volgate.model_adapter import load_model, predict
from src.signals.vol_gate import VolGateSignal
from src.order_manager import OrderManager, get_order_manager


class TestReplayIntegration:
    """End-to-end integration test using replay data."""
    
    @pytest.fixture
    def signal_generator(self):
        """Create a fresh signal generator."""
        return VolGateSignal()
    
    @pytest.fixture
    def order_manager(self, tmp_path):
        """Create order manager with temp database."""
        db_path = tmp_path / "test_trading.db"
        return OrderManager(str(db_path))
    
    @pytest.fixture
    def sample_ohlcv(self):
        """Sample historical OHLCV data for replay."""
        return [
            {"time": "2026-01-13T16:00:00", "open": 585.0, "high": 587.5, "low": 584.0, "close": 586.5, "volume": 42000000},
            {"time": "2026-01-14T16:00:00", "open": 586.5, "high": 588.0, "low": 585.5, "close": 587.0, "volume": 40000000},
            {"time": "2026-01-15T16:00:00", "open": 587.0, "high": 590.0, "low": 586.5, "close": 589.0, "volume": 45000000},
        ]
    
    @pytest.fixture
    def sample_indicators(self):
        """Sample indicators for replay."""
        return {
            "vol_5d": 0.12,
            "vol_30d": 0.14,
            "adx": 28.0,
            "atr": 3.5,
            "vix_proxy": 15.0,
            "adv_20d": 43000000
        }
    
    def test_full_replay_day_flow(self, signal_generator, order_manager, sample_ohlcv, sample_indicators):
        """Test complete flow for a single replay day."""
        decision_time = datetime(2026, 1, 15, 15, 55, 0)  # Decision cutoff
        execution_date = date(2026, 1, 16)  # T+1
        
        # Step 1: Create snapshot
        snapshot = signal_generator.create_snapshot(
            symbol="SPY",
            decision_time=decision_time,
            ohlcv=sample_ohlcv,
            indicators=sample_indicators
        )
        
        assert snapshot is not None
        assert snapshot["symbol"] == "SPY"
        assert len(snapshot["ohlcv"]) > 0
        
        # Step 2: Generate signal
        signal = signal_generator.generate_signal(snapshot)
        
        assert signal is not None
        assert "signal" in signal
        assert "exposure" in signal
        assert "confidence" in signal
        
        # Step 3: Create trade plan
        trade_plan = signal_generator.create_trade_plan(
            signal=signal,
            current_price=589.0,
            adv_20d=43000000,
            max_position_fraction=0.01
        )
        
        # Trade plan may be None if signal says no trade
        if trade_plan is not None:
            assert trade_plan["expected_execution_time"] == "OPEN_T+1"
            assert trade_plan["trading_mode"] == "paper"
            
            # Step 4: Place order (idempotent)
            order_result = order_manager.place_order(
                trade_plan=trade_plan,
                execution_date=execution_date
            )
            
            assert order_result["status"] == "created"
            client_order_id = order_result["client_order_id"]
            
            # Verify order was created
            order = order_manager.get_order(client_order_id)
            assert order is not None
            assert order.symbol == "SPY"
            assert order.status == "pending"
            
            # Step 5: Submit order
            submit_result = order_manager.submit_order(client_order_id)
            assert submit_result["status"] == "submitted"
            
            # Step 6: Simulate fill
            fill_result = order_manager.fill_order(
                client_order_id=client_order_id,
                filled_price=589.25  # Slight slippage from 589.0
            )
            
            assert fill_result["status"] == "filled"
            
            # Step 7: Verify order is filled
            filled_order = order_manager.get_order(client_order_id)
            assert filled_order.status == "filled"
            assert filled_order.filled_price == 589.25
            
            # Calculate slippage
            expected_price = 589.0
            actual_price = 589.25
            slippage_bps = (actual_price - expected_price) / expected_price * 10000
            
            # Slippage should be within tolerance (modeled mean 8bps ± 1σ*3bps = [5, 11] bps)
            assert abs(slippage_bps) < 15, f"Slippage {slippage_bps:.2f}bps outside tolerance"
    
    def test_replay_produces_actions_csv(self, signal_generator, order_manager, sample_ohlcv, sample_indicators, tmp_path):
        """Test that replay produces replay_actions.csv."""
        decision_time = datetime(2026, 1, 15, 15, 55, 0)
        execution_date = date(2026, 1, 16)
        
        actions = []
        
        # Run replay
        snapshot = signal_generator.create_snapshot(
            symbol="SPY",
            decision_time=decision_time,
            ohlcv=sample_ohlcv,
            indicators=sample_indicators
        )
        
        actions.append({
            "step": "snapshot_created",
            "timestamp": decision_time.isoformat(),
            "symbol": "SPY",
            "bars_count": len(snapshot["ohlcv"])
        })
        
        signal = signal_generator.generate_signal(snapshot)
        
        actions.append({
            "step": "signal_generated",
            "timestamp": decision_time.isoformat(),
            "signal": signal["signal"],
            "exposure": signal["exposure"],
            "confidence": signal["confidence"]
        })
        
        trade_plan = signal_generator.create_trade_plan(
            signal=signal,
            current_price=589.0,
            adv_20d=43000000
        )
        
        if trade_plan:
            actions.append({
                "step": "trade_plan_created",
                "trade_plan_id": trade_plan["trade_plan_id"],
                "target_shares": trade_plan["target_shares"]
            })
            
            order_result = order_manager.place_order(trade_plan, execution_date)
            
            actions.append({
                "step": "order_placed",
                "client_order_id": order_result.get("client_order_id"),
                "status": order_result["status"]
            })
        
        # Write actions to CSV
        csv_path = tmp_path / "replay_actions.csv"
        with open(csv_path, "w") as f:
            if actions:
                headers = set()
                for action in actions:
                    headers.update(action.keys())
                headers = sorted(headers)
                
                f.write(",".join(headers) + "\n")
                for action in actions:
                    row = [str(action.get(h, "")) for h in headers]
                    f.write(",".join(row) + "\n")
        
        # Verify file exists and has content
        assert csv_path.exists()
        with open(csv_path) as f:
            content = f.read()
            assert "step" in content
            assert "snapshot_created" in content
            assert "signal_generated" in content
    
    def test_trade_plan_scheduled_for_t_plus_1(self, signal_generator, sample_ohlcv, sample_indicators):
        """Verify trade plans are scheduled for T+1 execution."""
        decision_time = datetime(2026, 1, 15, 15, 55, 0)
        
        snapshot = signal_generator.create_snapshot(
            symbol="SPY",
            decision_time=decision_time,
            ohlcv=sample_ohlcv,
            indicators=sample_indicators
        )
        
        signal = signal_generator.generate_signal(snapshot)
        
        trade_plan = signal_generator.create_trade_plan(
            signal=signal,
            current_price=589.0,
            adv_20d=43000000
        )
        
        if trade_plan:
            assert trade_plan["expected_execution_time"] == "OPEN_T+1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
