"""
Volatility-Gated Model Adapter

Implements the model adapter interface for the VolGate trading signal system.
This adapter loads the model and produces predictions based on market snapshots.

PAPER-ONLY: This module is designed for paper trading only.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


# ============================================================================
# SAFETY: Paper-Only Trading Mode Enforcement
# ============================================================================
TRADING_MODE = "paper"  # Hardcoded default - NEVER change to "live" without explicit operator confirmation


@dataclass
class ModelHandle:
    """Handle for the loaded model."""
    model_version: str
    volatility_threshold_high: float
    volatility_threshold_low: float
    abstention_threshold: float
    is_placeholder: bool


def load_model(model_path: str = None) -> ModelHandle:
    """
    Load the volatility-gated model.
    
    If no model artifact is provided, returns a deterministic placeholder
    that uses a simple volatility threshold rule.
    
    Args:
        model_path: Path to model artifact (optional)
        
    Returns:
        ModelHandle for use with predict()
    """
    if model_path and model_path.strip():
        # TODO: Load actual model artifact
        # For now, return placeholder with configurable thresholds
        try:
            with open(model_path, 'r') as f:
                config = json.load(f)
            return ModelHandle(
                model_version=config.get("model_version", "volgate-v1.0"),
                volatility_threshold_high=config.get("volatility_threshold_high", 0.25),
                volatility_threshold_low=config.get("volatility_threshold_low", 0.10),
                abstention_threshold=config.get("abstention_threshold", 0.40),
                is_placeholder=False
            )
        except Exception:
            pass
    
    # Return placeholder model with deterministic rules
    return ModelHandle(
        model_version="volgate-v1.0-placeholder",
        volatility_threshold_high=0.25,  # Above this = reduce exposure
        volatility_threshold_low=0.10,   # Below this = increase exposure
        abstention_threshold=0.40,       # Abstain if confidence below this
        is_placeholder=True
    )


def _compute_snapshot_hash(snapshot: Dict[str, Any]) -> str:
    """Compute SHA256 hash of the snapshot for audit purposes."""
    # Create a deterministic string representation
    snapshot_copy = {k: v for k, v in snapshot.items() if k != 'meta'}
    snapshot_str = json.dumps(snapshot_copy, sort_keys=True, default=str)
    return hashlib.sha256(snapshot_str.encode()).hexdigest()


def _validate_time_causality(snapshot: Dict[str, Any], decision_time: datetime) -> None:
    """
    Validate that all data in the snapshot is from before or at the decision time.
    
    This prevents look-ahead bias in backtesting and ensures time causality.
    
    Raises:
        ValueError: If any data is from the future relative to decision_time
    """
    ohlcv = snapshot.get("ohlcv", [])
    
    for bar in ohlcv:
        bar_time_str = bar.get("time")
        if bar_time_str:
            # Parse the bar timestamp
            try:
                bar_time = datetime.fromisoformat(bar_time_str.replace('Z', '+00:00'))
                # Normalize decision_time if needed
                if decision_time.tzinfo is None:
                    bar_time = bar_time.replace(tzinfo=None)
                
                if bar_time > decision_time:
                    raise ValueError(
                        f"Time causality violation: Bar at {bar_time_str} is after "
                        f"decision_time {decision_time.isoformat()}. "
                        "Snapshot must contain only data ≤ decision_time."
                    )
            except (ValueError, TypeError) as e:
                if "Time causality violation" in str(e):
                    raise
                # Skip unparseable timestamps
                continue


def predict(model_handle: ModelHandle, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a trading signal from the snapshot.
    
    Args:
        model_handle: Handle from load_model()
        snapshot: Market snapshot matching snapshot_schema.json
        
    Returns:
        Prediction dict with signal, exposure, confidence, and metadata
        
    Raises:
        ValueError: If time causality is violated
    """
    # Parse decision time
    decision_time_str = snapshot.get("decision_time")
    if not decision_time_str:
        raise ValueError("snapshot must contain 'decision_time'")
    
    decision_time = datetime.fromisoformat(decision_time_str.replace('Z', '+00:00'))
    
    # CRITICAL: Validate time causality
    _validate_time_causality(snapshot, decision_time)
    
    # Extract indicators
    indicators = snapshot.get("indicators", {})
    vol_5d = indicators.get("vol_5d", 0.15)
    vol_30d = indicators.get("vol_30d", 0.15)
    vix_proxy = indicators.get("vix_proxy", 15.0)
    adx = indicators.get("adx", 20.0)
    
    # Compute snapshot hash for audit
    snapshot_hash = _compute_snapshot_hash(snapshot)
    
    # ========================================================================
    # Volatility-Gated Logic (Placeholder/Deterministic Implementation)
    # ========================================================================
    # This is a simple rule-based model that can be replaced with ML model
    
    # Normalize VIX to volatility scale
    vix_vol = vix_proxy / 100.0
    
    # Composite volatility measure
    composite_vol = (vol_5d * 0.5 + vol_30d * 0.3 + vix_vol * 0.2)
    
    # Trend strength factor from ADX
    trend_strength = min(adx / 50.0, 1.0)  # Normalize to 0-1
    
    # Decision logic
    signal = 0
    exposure = 0.0
    confidence = 0.5
    reason = ""
    
    if composite_vol > model_handle.volatility_threshold_high:
        # High volatility regime - reduce/eliminate exposure
        signal = 0
        exposure = 0.0
        confidence = 0.7 + (composite_vol - model_handle.volatility_threshold_high) * 0.5
        reason = f"High volatility regime (composite_vol={composite_vol:.3f} > threshold={model_handle.volatility_threshold_high})"
        
    elif composite_vol < model_handle.volatility_threshold_low:
        # Low volatility regime with strong trend - increase exposure
        if trend_strength > 0.5:
            signal = 1
            exposure = min(0.5 + trend_strength * 0.5, 1.0)
            confidence = 0.6 + trend_strength * 0.2
            reason = f"Low volatility regime with trend (composite_vol={composite_vol:.3f}, ADX={adx:.1f})"
        else:
            signal = 0
            exposure = 0.3
            confidence = 0.5
            reason = f"Low volatility but weak trend (ADX={adx:.1f})"
    else:
        # Medium volatility - neutral/small position
        signal = 1
        exposure = 0.3
        confidence = 0.5
        reason = f"Medium volatility regime (composite_vol={composite_vol:.3f})"
    
    # Apply abstention threshold
    if confidence < model_handle.abstention_threshold:
        signal = 0
        exposure = 0.0
        reason = f"Abstaining due to low confidence ({confidence:.2f} < {model_handle.abstention_threshold})"
    
    return {
        "timestamp": decision_time.isoformat(),
        "symbol": snapshot.get("symbol", "SPY"),
        "model_version": model_handle.model_version,
        "signal": signal,
        "exposure": round(exposure, 4),
        "confidence": round(min(confidence, 1.0), 4),
        "reason": reason,
        "snapshot_hash": snapshot_hash
    }
