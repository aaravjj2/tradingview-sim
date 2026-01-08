"""
Test Timestamp Causality

Validates that the model adapter enforces time causality:
- All data in snapshot must be <= decision_time
- Future data must raise ValueError
"""

import os
import sys
import pytest
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workspace.volgate.model_adapter import load_model, predict, _validate_time_causality


class TestTimestampCausality:
    """Test suite for timestamp causality validation."""
    
    def test_valid_snapshot_passes(self):
        """Snapshot with all bars <= decision_time should pass."""
        decision_time = datetime(2026, 1, 7, 16, 0, 0)
        
        snapshot = {
            "symbol": "SPY",
            "decision_time": decision_time.isoformat(),
            "ohlcv": [
                {"time": "2026-01-03T16:00:00", "open": 585, "high": 588, "low": 584, "close": 587, "volume": 45000000},
                {"time": "2026-01-06T16:00:00", "open": 587, "high": 590, "low": 586, "close": 589, "volume": 42000000},
                {"time": "2026-01-07T16:00:00", "open": 589, "high": 592, "low": 588, "close": 591, "volume": 38000000},
            ],
            "indicators": {
                "vol_5d": 0.12,
                "vol_30d": 0.15,
                "adx": 22.5,
                "atr": 4.25,
                "vix_proxy": 14.5,
                "adv_20d": 41000000
            },
            "market_context": {
                "spy_return_5d": 0.0085,
                "spy_vol_30d": 0.15
            },
            "meta": {
                "data_source_timestamps": {},
                "snapshot_hash": "test_hash"
            }
        }
        
        # Should not raise
        _validate_time_causality(snapshot, decision_time)
        
        # Full prediction should also pass
        model = load_model()
        result = predict(model, snapshot)
        
        assert result is not None
        assert "signal" in result
        assert "snapshot_hash" in result
    
    def test_future_bar_raises_error(self):
        """Snapshot with a bar after decision_time should raise ValueError."""
        decision_time = datetime(2026, 1, 7, 16, 0, 0)
        
        # Include a bar from the future
        snapshot = {
            "symbol": "SPY",
            "decision_time": decision_time.isoformat(),
            "ohlcv": [
                {"time": "2026-01-07T16:00:00", "open": 589, "high": 592, "low": 588, "close": 591, "volume": 38000000},
                {"time": "2026-01-08T16:00:00", "open": 591, "high": 595, "low": 590, "close": 594, "volume": 40000000},  # FUTURE!
            ],
            "indicators": {
                "vol_5d": 0.12,
                "vol_30d": 0.15,
                "adx": 22.5,
                "atr": 4.25,
                "vix_proxy": 14.5,
                "adv_20d": 41000000
            },
            "market_context": {},
            "meta": {}
        }
        
        with pytest.raises(ValueError) as exc_info:
            _validate_time_causality(snapshot, decision_time)
        
        assert "Time causality violation" in str(exc_info.value)
    
    def test_future_bar_in_predict_raises_error(self):
        """Full predict() should also raise on future data."""
        decision_time = datetime(2026, 1, 7, 16, 0, 0)
        
        snapshot = {
            "symbol": "SPY",
            "decision_time": decision_time.isoformat(),
            "ohlcv": [
                {"time": "2026-01-08T09:30:00", "open": 592, "high": 593, "low": 591, "close": 592.5, "volume": 5000000},  # FUTURE!
            ],
            "indicators": {
                "vol_5d": 0.12,
                "vol_30d": 0.15,
                "adx": 22.5,
                "atr": 4.25,
                "vix_proxy": 14.5,
                "adv_20d": 41000000
            },
            "market_context": {},
            "meta": {}
        }
        
        model = load_model()
        
        with pytest.raises(ValueError) as exc_info:
            predict(model, snapshot)
        
        assert "Time causality violation" in str(exc_info.value)
    
    def test_exactly_at_decision_time_passes(self):
        """Bar exactly at decision_time should pass."""
        decision_time = datetime(2026, 1, 7, 16, 0, 0)
        
        snapshot = {
            "symbol": "SPY",
            "decision_time": decision_time.isoformat(),
            "ohlcv": [
                {"time": "2026-01-07T16:00:00", "open": 589, "high": 592, "low": 588, "close": 591, "volume": 38000000},
            ],
            "indicators": {
                "vol_5d": 0.12,
                "vol_30d": 0.15,
                "adx": 22.5,
                "atr": 4.25,
                "vix_proxy": 14.5,
                "adv_20d": 41000000
            },
            "market_context": {},
            "meta": {}
        }
        
        # Should not raise
        _validate_time_causality(snapshot, decision_time)
    
    def test_one_second_future_raises_error(self):
        """Even 1 second in the future should raise."""
        decision_time = datetime(2026, 1, 7, 16, 0, 0)
        one_second_future = (decision_time + timedelta(seconds=1)).isoformat()
        
        snapshot = {
            "symbol": "SPY",
            "decision_time": decision_time.isoformat(),
            "ohlcv": [
                {"time": one_second_future, "open": 589, "high": 592, "low": 588, "close": 591, "volume": 38000000},
            ],
            "indicators": {
                "vol_5d": 0.12,
                "vol_30d": 0.15,
                "adx": 22.5,
                "atr": 4.25,
                "vix_proxy": 14.5,
                "adv_20d": 41000000
            },
            "market_context": {},
            "meta": {}
        }
        
        with pytest.raises(ValueError) as exc_info:
            _validate_time_causality(snapshot, decision_time)
        
        assert "Time causality violation" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
