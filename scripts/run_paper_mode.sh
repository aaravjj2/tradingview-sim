#!/bin/bash
#
# Run Paper Mode - Execute paper trading for specified duration
#
# Usage:
#   ./scripts/run_paper_mode.sh SYMBOL=SPY DURATION=7
#
# Environment Variables:
#   SYMBOL   - Trading symbol (default: SPY)
#   DURATION - Number of days to run (default: 7)
#
# PAPER TRADING ONLY - No live orders will be placed

set -e

# Parse arguments
for arg in "$@"; do
    case $arg in
        SYMBOL=*)
            SYMBOL="${arg#*=}"
            ;;
        DURATION=*)
            DURATION="${arg#*=}"
            ;;
    esac
done

# Defaults
SYMBOL=${SYMBOL:-SPY}
DURATION=${DURATION:-7}

# CRITICAL: Enforce paper mode
export TRADING_MODE=paper

echo "=========================================="
echo "VolGate Paper Trading Mode"
echo "=========================================="
echo "Symbol: $SYMBOL"
echo "Duration: $DURATION days"
echo "Mode: PAPER (no live orders)"
echo "=========================================="
echo ""
echo "⚠️  PAPER TRADING ONLY"
echo "⚠️  No real orders will be placed"
echo "⚠️  Using Alpaca Paper API (if configured)"
echo ""

# Check for required environment variables
if [ -z "$ALPACA_API_KEY" ] && [ -z "$ALPACA_PAPER_KEY" ]; then
    echo "Warning: No Alpaca API keys found in environment."
    echo "Running in fully simulated mode."
    echo ""
fi

# Create output directory
OUTPUT_DIR="./paper_output/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "Output directory: $OUTPUT_DIR"
echo ""

# Run paper trading
cd "$(dirname "$0")/.."

python3 << EOF
import os
import sys
import json
import time
from datetime import datetime, date, timedelta

sys.path.insert(0, os.getcwd())

from workspace.volgate.model_adapter import load_model
from src.signals.vol_gate import VolGateSignal
from src.order_manager import OrderManager

def run_paper_mode():
    symbol = "${SYMBOL}"
    duration = ${DURATION}
    output_dir = "${OUTPUT_DIR}"
    
    print(f"Starting paper trading for {symbol}")
    print(f"Duration: {duration} days")
    print(f"Trading mode: {os.environ.get('TRADING_MODE', 'paper')}")
    print("")
    
    # Initialize components
    signal_gen = VolGateSignal()
    order_manager = OrderManager(f"{output_dir}/paper_orders.db")
    
    # Track results
    daily_results = []
    
    for day in range(duration):
        current_date = date.today() + timedelta(days=day)
        
        # Skip weekends
        if current_date.weekday() >= 5:
            print(f"[DAY {day+1}] {current_date} - Weekend, skipping")
            continue
        
        print(f"[DAY {day+1}] {current_date} - Processing")
        
        # For paper mode, we simulate the day's action
        decision_time = datetime.combine(current_date, datetime.strptime("15:55", "%H:%M").time())
        
        # Mock market data (in production, would fetch real data)
        import random
        random.seed(current_date.toordinal())
        
        base_price = 590 + random.uniform(-5, 5)
        vol_5d = 0.10 + random.uniform(0, 0.15)
        adx = 20 + random.uniform(0, 20)
        
        ohlcv = [
            {
                "time": decision_time.isoformat(),
                "open": base_price,
                "high": base_price + random.uniform(0, 2),
                "low": base_price - random.uniform(0, 2),
                "close": base_price + random.uniform(-1, 1),
                "volume": 40000000 + random.randint(-5000000, 5000000)
            }
        ]
        
        indicators = {
            "vol_5d": vol_5d,
            "vol_30d": vol_5d + random.uniform(-0.02, 0.02),
            "adx": adx,
            "atr": 3.5,
            "vix_proxy": vol_5d * 100,
            "adv_20d": 40000000
        }
        
        try:
            # Generate signal
            snapshot = signal_gen.create_snapshot(
                symbol=symbol,
                decision_time=decision_time,
                ohlcv=ohlcv,
                indicators=indicators
            )
            
            signal = signal_gen.generate_signal(snapshot)
            
            trade_plan = signal_gen.create_trade_plan(
                signal=signal,
                current_price=base_price,
                adv_20d=40000000
            )
            
            result = {
                "date": str(current_date),
                "signal": signal["signal"],
                "exposure": signal["exposure"],
                "confidence": signal["confidence"],
                "trade_plan": trade_plan is not None,
                "status": "success"
            }
            
            if trade_plan:
                execution_date = current_date + timedelta(days=1)
                order_result = order_manager.place_order(trade_plan, execution_date)
                result["order_status"] = order_result["status"]
                result["client_order_id"] = order_result.get("client_order_id")
                
                print(f"  Signal: {signal['signal']}, Exposure: {signal['exposure']:.2f}")
                print(f"  Order: {order_result['status']}")
            else:
                print(f"  Signal: {signal['signal']}, Exposure: {signal['exposure']:.2f}")
                print("  No trade generated")
            
            daily_results.append(result)
            
        except Exception as e:
            print(f"  Error: {e}")
            daily_results.append({
                "date": str(current_date),
                "status": "error",
                "error": str(e)
            })
    
    # Write results
    results_path = f"{output_dir}/paper_results.json"
    with open(results_path, "w") as f:
        json.dump(daily_results, f, indent=2)
    
    print("")
    print(f"Paper trading complete!")
    print(f"Results: {results_path}")
    print(f"Orders DB: {output_dir}/paper_orders.db")
    
    # Summary
    successful = sum(1 for r in daily_results if r.get("status") == "success")
    trades = sum(1 for r in daily_results if r.get("trade_plan"))
    
    print("")
    print("Summary:")
    print(f"  Days processed: {len(daily_results)}")
    print(f"  Successful: {successful}")
    print(f"  Trades generated: {trades}")

if __name__ == "__main__":
    run_paper_mode()
EOF

echo ""
echo "Paper trading complete."
echo "Results: $OUTPUT_DIR/paper_results.json"
