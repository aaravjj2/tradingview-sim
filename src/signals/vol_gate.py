"""
Volatility-Gated Signal Generator

Calls the model adapter to generate trade plans based on market snapshots.

PAPER-ONLY: This module enforces paper trading mode.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from workspace.volgate.model_adapter import load_model, predict, ModelHandle


# ============================================================================
# SAFETY: Paper-Only Trading Mode Enforcement
# ============================================================================
TRADING_MODE = os.environ.get("TRADING_MODE", "paper")

if TRADING_MODE not in ("paper", "shadow"):
    raise RuntimeError(
        f"TRADING_MODE must be 'paper' or 'shadow', got '{TRADING_MODE}'. "
        "Live trading is not supported."
    )


class VolGateSignal:
    """
    Volatility-Gated Signal Generator.
    
    Orchestrates snapshot creation and model prediction to produce trade plans.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the signal generator.
        
        Args:
            model_path: Optional path to model artifact
        """
        self.model = load_model(model_path)
        self.last_signal: Optional[Dict] = None
        self.signal_history: List[Dict] = []
    
    def create_snapshot(
        self,
        symbol: str,
        decision_time: datetime,
        ohlcv: List[Dict],
        indicators: Dict[str, float],
        market_context: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Create a snapshot for model prediction.
        
        Args:
            symbol: Trading symbol (e.g., "SPY")
            decision_time: Timestamp of decision point
            ohlcv: List of OHLCV bars
            indicators: Dict with vol_5d, vol_30d, adx, atr, vix_proxy, adv_20d
            market_context: Optional dict with spy_return_5d, spy_vol_30d
            
        Returns:
            Snapshot dict matching schema
        """
        # Ensure all bars are before or at decision_time
        filtered_ohlcv = []
        for bar in ohlcv:
            bar_time_str = bar.get("time")
            if bar_time_str:
                try:
                    bar_time = datetime.fromisoformat(bar_time_str.replace('Z', '+00:00'))
                    if bar_time.tzinfo is None:
                        bar_time = bar_time.replace(tzinfo=decision_time.tzinfo)
                    if bar_time <= decision_time:
                        filtered_ohlcv.append(bar)
                except ValueError:
                    continue
        
        if not filtered_ohlcv:
            raise ValueError("No valid OHLCV bars at or before decision_time")
        
        # Compute snapshot hash
        snapshot_content = {
            "symbol": symbol,
            "decision_time": decision_time.isoformat(),
            "ohlcv": filtered_ohlcv,
            "indicators": indicators
        }
        snapshot_str = json.dumps(snapshot_content, sort_keys=True, default=str)
        snapshot_hash = hashlib.sha256(snapshot_str.encode()).hexdigest()
        
        return {
            "symbol": symbol,
            "decision_time": decision_time.isoformat(),
            "ohlcv": filtered_ohlcv,
            "indicators": indicators,
            "market_context": market_context or {
                "spy_return_5d": 0.0,
                "spy_vol_30d": 0.15
            },
            "meta": {
                "data_source_timestamps": {
                    "ohlcv": filtered_ohlcv[-1]["time"] if filtered_ohlcv else None,
                    "indicators": decision_time.isoformat()
                },
                "snapshot_hash": snapshot_hash
            }
        }
    
    def generate_signal(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a trading signal from a snapshot.
        
        Args:
            snapshot: Market snapshot matching schema
            
        Returns:
            Signal dict with trading recommendation
        """
        prediction = predict(self.model, snapshot)
        
        # Store in history
        self.last_signal = prediction
        self.signal_history.append(prediction)
        
        # Keep only last 100 signals
        if len(self.signal_history) > 100:
            self.signal_history = self.signal_history[-100:]
        
        return prediction
    
    def create_trade_plan(
        self,
        signal: Dict[str, Any],
        current_price: float,
        adv_20d: float,
        max_position_fraction: float = 0.01
    ) -> Optional[Dict[str, Any]]:
        """
        Convert a signal into a trade plan.
        
        Args:
            signal: Signal dict from generate_signal()
            current_price: Current price of the asset
            adv_20d: 20-day average daily volume
            max_position_fraction: Max fraction of ADV per trade
            
        Returns:
            Trade plan dict or None if no action
        """
        if signal.get("signal", 0) == 0 and signal.get("exposure", 0) == 0:
            return None  # No trade needed
        
        exposure = signal.get("exposure", 0)
        symbol = signal.get("symbol", "SPY")
        
        # Calculate position size based on ADV constraint
        max_shares_adv = int(adv_20d * max_position_fraction)
        target_shares = int(max_shares_adv * exposure)
        
        if target_shares == 0:
            return None
        
        # Create deterministic trade plan ID
        plan_content = {
            "symbol": symbol,
            "timestamp": signal.get("timestamp"),
            "exposure": exposure,
            "target_shares": target_shares,
            "snapshot_hash": signal.get("snapshot_hash")
        }
        plan_str = json.dumps(plan_content, sort_keys=True)
        plan_id = hashlib.sha256(plan_str.encode()).hexdigest()[:16]
        
        return {
            "trade_plan_id": plan_id,
            "symbol": symbol,
            "decision_time": signal.get("timestamp"),
            "action": "buy" if exposure > 0 else "hold",
            "target_exposure": exposure,
            "target_shares": target_shares,
            "current_price": current_price,
            "expected_execution_time": "OPEN_T+1",  # T+1 scheduling
            "signal_confidence": signal.get("confidence", 0),
            "signal_reason": signal.get("reason", ""),
            "snapshot_hash": signal.get("snapshot_hash"),
            "model_version": signal.get("model_version"),
            "trading_mode": TRADING_MODE
        }


# Singleton instance
_vol_gate_signal: Optional[VolGateSignal] = None


def get_vol_gate_signal(model_path: Optional[str] = None) -> VolGateSignal:
    """Get or create the singleton VolGateSignal instance."""
    global _vol_gate_signal
    if _vol_gate_signal is None:
        _vol_gate_signal = VolGateSignal(model_path)
    return _vol_gate_signal


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VolGate Signal Generator")
    parser.add_argument("--symbol", default="SPY", help="Trading symbol")
    parser.add_argument("--model-path", default=None, help="Path to model artifact")
    args = parser.parse_args()
    
    print(f"VolGate Signal Generator - {TRADING_MODE.upper()} MODE")
    print("=" * 50)
    
    # Load example snapshot
    example_path = os.path.join(
        os.path.dirname(__file__), 
        "../../workspace/volgate/example_snapshot.json"
    )
    
    if os.path.exists(example_path):
        with open(example_path) as f:
            snapshot = json.load(f)
        
        signal_gen = get_vol_gate_signal(args.model_path)
        signal = signal_gen.generate_signal(snapshot)
        
        print(f"\nSignal for {args.symbol}:")
        print(json.dumps(signal, indent=2))
        
        # Create trade plan
        plan = signal_gen.create_trade_plan(
            signal,
            current_price=591.20,
            adv_20d=41000000
        )
        
        if plan:
            print(f"\nTrade Plan:")
            print(json.dumps(plan, indent=2))
        else:
            print("\nNo trade plan generated (signal is neutral/abstain)")
    else:
        print(f"Example snapshot not found at {example_path}")
