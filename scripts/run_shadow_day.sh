#!/bin/bash
#
# Run Shadow Day - Execute a single shadow replay day
#
# Usage:
#   ./scripts/run_shadow_day.sh SYMBOL=SPY DATE=2026-01-15
#
# Environment Variables:
#   SYMBOL - Trading symbol (default: SPY)
#   DATE   - Date to replay (YYYY-MM-DD format)
#
# Output:
#   - replay_actions.csv in replay_output directory
#   - Simulated orders placed (no broker connection)

set -e

# Parse arguments
for arg in "$@"; do
    case $arg in
        SYMBOL=*)
            SYMBOL="${arg#*=}"
            ;;
        DATE=*)
            DATE="${arg#*=}"
            ;;
    esac
done

# Defaults
SYMBOL=${SYMBOL:-SPY}
DATE=${DATE:-$(date +%Y-%m-%d)}
TRADING_MODE=shadow

echo "=========================================="
echo "VolGate Shadow Day Replay"
echo "=========================================="
echo "Symbol: $SYMBOL"
echo "Date: $DATE"
echo "Mode: $TRADING_MODE (NO BROKER CONNECTION)"
echo "=========================================="

# Set environment
export TRADING_MODE=$TRADING_MODE
export SYMBOL=$SYMBOL
export REPLAY_DATE=$DATE

# Create output directory
OUTPUT_DIR="./replay_output/${DATE}"
mkdir -p "$OUTPUT_DIR"

# Run the shadow replay
cd "$(dirname "$0")/.."

python3 << 'EOF'
import os
import sys
import json
import csv
from datetime import datetime, date

# Add project to path
sys.path.insert(0, os.getcwd())

from workspace.volgate.model_adapter import load_model, predict
from src.signals.vol_gate import VolGateSignal
from src.order_manager import OrderManager

def run_shadow_day():
    symbol = os.environ.get("SYMBOL", "SPY")
    replay_date = os.environ.get("REPLAY_DATE", "2026-01-15")
    output_dir = f"./replay_output/{replay_date}"
    
    print(f"\n[SHADOW] Initializing for {symbol} on {replay_date}")
    
    # Initialize components
    signal_gen = VolGateSignal()
    # Use in-memory DB for shadow mode
    order_manager = OrderManager(f"{output_dir}/shadow_orders.db")
    
    # Mock historical data (in production, would fetch from database)
    # This is a simplified example
    decision_time = datetime.fromisoformat(f"{replay_date}T15:55:00")
    
    ohlcv = [
        {"time": f"{replay_date}T09:30:00", "open": 585.0, "high": 586.0, "low": 584.5, "close": 585.5, "volume": 5000000},
        {"time": f"{replay_date}T10:00:00", "open": 585.5, "high": 587.0, "low": 585.0, "close": 586.5, "volume": 8000000},
        {"time": f"{replay_date}T12:00:00", "open": 586.5, "high": 588.0, "low": 586.0, "close": 587.5, "volume": 12000000},
        {"time": f"{replay_date}T15:00:00", "open": 587.5, "high": 589.0, "low": 587.0, "close": 588.5, "volume": 15000000},
        {"time": f"{replay_date}T15:55:00", "open": 588.5, "high": 589.5, "low": 588.0, "close": 589.0, "volume": 20000000},
    ]
    
    indicators = {
        "vol_5d": 0.12,
        "vol_30d": 0.14,
        "adx": 25.0,
        "atr": 3.5,
        "vix_proxy": 15.0,
        "adv_20d": 40000000
    }
    
    actions = []
    
    # Step 1: Create snapshot
    print(f"[SHADOW] Creating snapshot at {decision_time.isoformat()}")
    snapshot = signal_gen.create_snapshot(
        symbol=symbol,
        decision_time=decision_time,
        ohlcv=ohlcv,
        indicators=indicators
    )
    actions.append({
        "step": "snapshot_created",
        "timestamp": decision_time.isoformat(),
        "symbol": symbol,
        "bars_count": len(snapshot["ohlcv"]),
        "snapshot_hash": snapshot["meta"]["snapshot_hash"]
    })
    
    # Step 2: Generate signal
    print("[SHADOW] Generating signal")
    signal = signal_gen.generate_signal(snapshot)
    actions.append({
        "step": "signal_generated",
        "timestamp": decision_time.isoformat(),
        "signal": signal["signal"],
        "exposure": signal["exposure"],
        "confidence": signal["confidence"],
        "reason": signal["reason"]
    })
    print(f"[SHADOW] Signal: {signal['signal']}, Exposure: {signal['exposure']:.2f}, Confidence: {signal['confidence']:.2f}")
    
    # Step 3: Create trade plan
    trade_plan = signal_gen.create_trade_plan(
        signal=signal,
        current_price=589.0,
        adv_20d=40000000
    )
    
    if trade_plan:
        print(f"[SHADOW] Trade plan created: {trade_plan['target_shares']} shares")
        actions.append({
            "step": "trade_plan_created",
            "trade_plan_id": trade_plan["trade_plan_id"],
            "target_shares": trade_plan["target_shares"],
            "expected_execution": trade_plan["expected_execution_time"]
        })
        
        # Step 4: Place order (simulated)
        execution_date = date.fromisoformat(replay_date)
        order_result = order_manager.place_order(trade_plan, execution_date)
        actions.append({
            "step": "order_placed",
            "client_order_id": order_result.get("client_order_id"),
            "status": order_result["status"]
        })
        print(f"[SHADOW] Order placed: {order_result['client_order_id']}")
        
        # Step 5: Simulate fill (shadow mode - no actual execution)
        if order_result["status"] == "created":
            client_order_id = order_result["client_order_id"]
            order_manager.submit_order(client_order_id)
            
            # Simulate fill with realistic slippage
            import random
            random.seed(hash(client_order_id))
            slippage_bps = random.gauss(8, 3)  # Mean 8bps, std 3bps
            fill_price = 589.0 * (1 + slippage_bps / 10000)
            
            order_manager.fill_order(client_order_id, fill_price)
            
            actions.append({
                "step": "order_filled",
                "client_order_id": client_order_id,
                "fill_price": round(fill_price, 2),
                "slippage_bps": round(slippage_bps, 2)
            })
            print(f"[SHADOW] Order filled at ${fill_price:.2f} (slippage: {slippage_bps:.1f}bps)")
    else:
        print("[SHADOW] No trade plan generated (neutral signal)")
        actions.append({
            "step": "no_trade",
            "reason": "Signal did not generate trade plan"
        })
    
    # Write replay_actions.csv
    csv_path = f"{output_dir}/replay_actions.csv"
    with open(csv_path, "w", newline="") as f:
        if actions:
            headers = set()
            for action in actions:
                headers.update(action.keys())
            headers = sorted(headers)
            
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(actions)
    
    print(f"\n[SHADOW] Output written to {csv_path}")
    print("[SHADOW] Shadow day complete!")
    
    return actions

if __name__ == "__main__":
    run_shadow_day()
EOF

echo ""
echo "Shadow day replay complete."
echo "Output: $OUTPUT_DIR/replay_actions.csv"
