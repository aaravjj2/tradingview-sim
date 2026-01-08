# VolGate Model Metadata

## Model Version
- **Version**: volgate-v1.0-placeholder
- **Type**: Volatility-Gated Exposure Model
- **Status**: Placeholder (deterministic rule-based)

## Description
This is a volatility-gated exposure model that adjusts trading exposure based on
market volatility regimes. The current implementation is a deterministic 
placeholder that can be replaced with a trained ML model.

## Model Logic
1. **High Volatility (>25%)**: Reduce exposure to 0
2. **Low Volatility (<10%) + Strong Trend (ADX>25)**: Increase exposure up to 100%
3. **Medium Volatility**: Maintain small position (30% exposure)

## Requirements
- Python 3.9+
- numpy
- No external ML dependencies for placeholder model

## Input Schema
See `snapshot_schema.json` for the exact input format.

Required fields:
- `symbol`: Trading symbol (e.g., "SPY")
- `decision_time`: ISO8601 timestamp
- `ohlcv`: Array of price bars
- `indicators`: Object with vol_5d, vol_30d, adx, atr, vix_proxy, adv_20d
- `market_context`: Object with spy_return_5d, spy_vol_30d
- `meta`: Object with data_source_timestamps, snapshot_hash

## Output Schema
```json
{
  "timestamp": "ISO8601 decision_time",
  "symbol": "SPY",
  "model_version": "volgate-v1.0",
  "signal": 0,                // 0 or 1 (exposure state)
  "exposure": 0.0,            // numeric 0..1
  "confidence": 0.72,         // numeric 0..1
  "reason": "text explanation",
  "snapshot_hash": "sha256hex"
}
```

## Replacing with Real Model
1. Train your model using historical snapshots
2. Save model artifact to a file
3. Update `load_model()` to load your artifact
4. Update `predict()` to use your model's inference

## Notes
- All timestamps must satisfy time causality (data ≤ decision_time)
- The adapter will raise ValueError if future data is detected
- Paper trading mode is enforced by default
