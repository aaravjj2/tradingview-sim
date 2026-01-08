# VolGate Model Adapter

Volatility-Gated trading model adapter for paper-only trading.

## ⚠️ PAPER TRADING ONLY

This system is configured for **paper trading only**. Live trading is disabled
by default and requires explicit operator confirmation to enable.

## Quick Start

```bash
# Set environment variables
export TRADING_MODE=paper
export ALPACA_API_KEY=your_paper_key
export ALPACA_API_SECRET=your_paper_secret

# Run the signal generator
python -m src.signals.vol_gate --symbol SPY

# Run paper trading mode
./scripts/run_paper_mode.sh SYMBOL=SPY DURATION=7
```

## Files

| File | Description |
|------|-------------|
| `model_adapter.py` | Core adapter with `load_model()` and `predict()` |
| `snapshot_schema.json` | JSON Schema for input snapshots |
| `example_snapshot.json` | Example snapshot for testing |
| `model_metadata.md` | Model version, requirements, notes |
| `calibrate_confidence.py` | Optional confidence calibration helper |

## Model Interface

### load_model(model_path: str) -> ModelHandle

Loads the model. If no artifact is provided, uses a deterministic placeholder
based on volatility thresholds.

### predict(model_handle, snapshot: dict) -> dict

Generates a trading signal from the snapshot.

**Output:**
```json
{
  "timestamp": "2026-01-07T16:00:00-05:00",
  "symbol": "SPY",
  "model_version": "volgate-v1.0",
  "signal": 1,
  "exposure": 0.75,
  "confidence": 0.82,
  "reason": "Low volatility regime with trend",
  "snapshot_hash": "a1b2c3..."
}
```

## Replacing the Placeholder Model

The default implementation uses a simple volatility threshold rule:

1. **High Vol (>25%)**: Exposure = 0
2. **Low Vol (<10%) + Strong Trend**: Exposure up to 100%
3. **Medium Vol**: Exposure = 30%

To replace with your own model:

1. Save your trained model artifact
2. Modify `load_model()` to load your artifact
3. Modify `predict()` to call your model's inference
4. Run `test_adapter_predict.py` to verify

## Time Causality

The adapter enforces strict time causality:
- All OHLCV bars must have timestamps ≤ decision_time
- Violations raise a `ValueError`
- This prevents look-ahead bias in backtesting

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRADING_MODE` | `paper` | Trading mode (paper only) |
| `MODEL_PATH` | None | Path to model artifact |
| `ABSTENTION_THRESHOLD` | 0.40 | Minimum confidence to trade |
