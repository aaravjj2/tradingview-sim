"""
Test Model Adapter Predict Function

Tests the model adapter's predict() function with example snapshots.
Verifies output schema and deterministic behavior.
"""

import os
import sys
import json
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workspace.volgate.model_adapter import load_model, predict


class TestAdapterPredict:
    """Test suite for model adapter predict function."""
    
    @pytest.fixture
    def example_snapshot(self):
        """Load the example snapshot from workspace."""
        example_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "workspace/volgate/example_snapshot.json"
        )
        with open(example_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def model(self):
        """Load the placeholder model."""
        return load_model()
    
    def test_predict_returns_required_fields(self, model, example_snapshot):
        """Prediction must contain all required output fields."""
        result = predict(model, example_snapshot)
        
        required_fields = [
            "timestamp",
            "symbol",
            "model_version",
            "signal",
            "exposure",
            "confidence",
            "reason",
            "snapshot_hash"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
    
    def test_predict_signal_is_valid(self, model, example_snapshot):
        """Signal must be 0 or 1."""
        result = predict(model, example_snapshot)
        
        assert result["signal"] in [0, 1], "Signal must be 0 or 1"
    
    def test_predict_exposure_in_range(self, model, example_snapshot):
        """Exposure must be between 0 and 1."""
        result = predict(model, example_snapshot)
        
        assert 0 <= result["exposure"] <= 1, "Exposure must be in [0, 1]"
    
    def test_predict_confidence_in_range(self, model, example_snapshot):
        """Confidence must be between 0 and 1."""
        result = predict(model, example_snapshot)
        
        assert 0 <= result["confidence"] <= 1, "Confidence must be in [0, 1]"
    
    def test_predict_is_deterministic(self, model, example_snapshot):
        """Same snapshot should produce same output."""
        result1 = predict(model, example_snapshot)
        result2 = predict(model, example_snapshot)
        
        # Core prediction fields should be identical
        assert result1["signal"] == result2["signal"]
        assert result1["exposure"] == result2["exposure"]
        assert result1["confidence"] == result2["confidence"]
        assert result1["snapshot_hash"] == result2["snapshot_hash"]
    
    def test_predict_symbol_matches_input(self, model, example_snapshot):
        """Output symbol should match input symbol."""
        result = predict(model, example_snapshot)
        
        assert result["symbol"] == example_snapshot["symbol"]
    
    def test_predict_timestamp_matches_input(self, model, example_snapshot):
        """Output timestamp should match decision_time."""
        result = predict(model, example_snapshot)
        
        # Compare date portions
        assert example_snapshot["decision_time"][:10] in result["timestamp"]
    
    def test_predict_generates_snapshot_hash(self, model, example_snapshot):
        """Snapshot hash should be a valid hex string."""
        result = predict(model, example_snapshot)
        
        snapshot_hash = result["snapshot_hash"]
        
        # Should be a hex string
        assert all(c in "0123456789abcdef" for c in snapshot_hash.lower())
        
        # SHA256 should be 64 characters
        assert len(snapshot_hash) == 64
    
    def test_high_volatility_reduces_exposure(self, model):
        """High volatility should result in low/zero exposure."""
        high_vol_snapshot = {
            "symbol": "SPY",
            "decision_time": "2026-01-07T16:00:00",
            "ohlcv": [
                {"time": "2026-01-07T16:00:00", "open": 589, "high": 592, "low": 588, "close": 591, "volume": 38000000},
            ],
            "indicators": {
                "vol_5d": 0.35,  # Very high volatility
                "vol_30d": 0.30,
                "adx": 22.5,
                "atr": 4.25,
                "vix_proxy": 35.0,  # High VIX
                "adv_20d": 41000000
            },
            "market_context": {},
            "meta": {}
        }
        
        result = predict(model, high_vol_snapshot)
        
        # High volatility should lead to reduced exposure
        assert result["exposure"] <= 0.3
    
    def test_low_volatility_strong_trend_increases_exposure(self, model):
        """Low volatility with strong trend should increase exposure."""
        low_vol_snapshot = {
            "symbol": "SPY",
            "decision_time": "2026-01-07T16:00:00",
            "ohlcv": [
                {"time": "2026-01-07T16:00:00", "open": 589, "high": 592, "low": 588, "close": 591, "volume": 38000000},
            ],
            "indicators": {
                "vol_5d": 0.08,  # Low volatility
                "vol_30d": 0.09,
                "adx": 35.0,  # Strong trend
                "atr": 2.0,
                "vix_proxy": 12.0,  # Low VIX
                "adv_20d": 41000000
            },
            "market_context": {},
            "meta": {}
        }
        
        result = predict(model, low_vol_snapshot)
        
        # Low volatility + strong trend should lead to increased exposure
        assert result["signal"] == 1
        assert result["exposure"] >= 0.5
    
    def test_missing_decision_time_raises_error(self, model):
        """Missing decision_time should raise ValueError."""
        bad_snapshot = {
            "symbol": "SPY",
            # No decision_time
            "ohlcv": [],
            "indicators": {},
            "market_context": {},
            "meta": {}
        }
        
        with pytest.raises(ValueError) as exc_info:
            predict(model, bad_snapshot)
        
        assert "decision_time" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
