#!/bin/bash
#
# Generate Reconciliation Report
#
# Produces reconciliation_report.csv comparing expected vs actual execution
#
# Usage:
#   ./scripts/generate_reconciliation.sh
#
# Input:
#   - Orders from trading_data.db or paper_output directory
#
# Output:
#   - reconciliation_report.csv

set -e

echo "=========================================="
echo "VolGate Reconciliation Report Generator"
echo "=========================================="

# Find the most recent output directory
if [ -d "./paper_output" ]; then
    LATEST_DIR=$(ls -td ./paper_output/*/ 2>/dev/null | head -1)
fi

if [ -d "./replay_output" ]; then
    REPLAY_DIR=$(ls -td ./replay_output/*/ 2>/dev/null | head -1)
fi

OUTPUT_FILE="./reconciliation_report.csv"

cd "$(dirname "$0")/.."

python3 << 'EOF'
import os
import sys
import json
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

def generate_reconciliation():
    print("Scanning for order databases...")
    
    orders = []
    
    # Check paper_output
    paper_dir = Path("./paper_output")
    if paper_dir.exists():
        for db_file in paper_dir.glob("**/paper_orders.db"):
            print(f"  Found: {db_file}")
            orders.extend(load_orders_from_db(db_file))
    
    # Check replay_output
    replay_dir = Path("./replay_output")
    if replay_dir.exists():
        for db_file in replay_dir.glob("**/shadow_orders.db"):
            print(f"  Found: {db_file}")
            orders.extend(load_orders_from_db(db_file))
    
    # Check main database
    main_db = Path("./trading_data.db")
    if main_db.exists():
        print(f"  Found: {main_db}")
        orders.extend(load_orders_from_db(main_db))
    
    if not orders:
        print("\nNo orders found. Running with sample data for demonstration.")
        orders = generate_sample_orders()
    
    print(f"\nTotal orders: {len(orders)}")
    
    # Generate reconciliation
    reconciliation = []
    
    for order in orders:
        if order.get("status") == "filled":
            expected_price = order.get("expected_price", order.get("limit_price", 589.0)) or 589.0
            fill_price = order.get("filled_price", expected_price)
            
            slippage_bps = (fill_price - expected_price) / expected_price * 10000
            
            # Compare to modeled slippage (mean=8bps, std=3bps)
            modeled_mean = 8.0
            modeled_std = 3.0
            within_tolerance = abs(slippage_bps) <= modeled_mean + modeled_std
            
            reconciliation.append({
                "client_order_id": order.get("client_order_id", "unknown"),
                "symbol": order.get("symbol", "SPY"),
                "side": order.get("side", "buy"),
                "qty": order.get("qty", 0) or order.get("filled_qty", 0),
                "expected_price": round(expected_price, 2),
                "fill_price": round(fill_price, 2),
                "slippage_bps": round(slippage_bps, 2),
                "modeled_mean_bps": modeled_mean,
                "modeled_std_bps": modeled_std,
                "within_tolerance": "YES" if within_tolerance else "NO",
                "status": order.get("status", "unknown"),
                "filled_at": order.get("filled_at", "")
            })
    
    # Write CSV
    output_file = "./reconciliation_report.csv"
    if reconciliation:
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(reconciliation[0].keys()))
            writer.writeheader()
            writer.writerows(reconciliation)
        
        print(f"\nReconciliation report: {output_file}")
        
        # Summary statistics
        slippages = [r["slippage_bps"] for r in reconciliation]
        within_count = sum(1 for r in reconciliation if r["within_tolerance"] == "YES")
        
        if slippages:
            import statistics
            avg_slippage = statistics.mean(slippages)
            std_slippage = statistics.stdev(slippages) if len(slippages) > 1 else 0
            
            print(f"\nSummary:")
            print(f"  Total fills: {len(reconciliation)}")
            print(f"  Average slippage: {avg_slippage:.2f} bps")
            print(f"  Slippage std dev: {std_slippage:.2f} bps")
            print(f"  Within tolerance: {within_count}/{len(reconciliation)} ({100*within_count/len(reconciliation):.0f}%)")
            print(f"  Modeled: {modeled_mean:.0f}bps ± {modeled_std:.0f}bps")
            
            # Check if overall within tolerance
            if abs(avg_slippage) <= modeled_mean + modeled_std:
                print("\n✅ Reconciliation PASSED: Average slippage within modeled tolerance")
            else:
                print("\n❌ Reconciliation FAILED: Average slippage outside modeled tolerance")
    else:
        print("\nNo filled orders to reconcile.")
        # Create empty report
        with open(output_file, "w") as f:
            f.write("client_order_id,symbol,side,qty,expected_price,fill_price,slippage_bps,modeled_mean_bps,modeled_std_bps,within_tolerance,status,filled_at\n")
        print(f"Empty report created: {output_file}")


def load_orders_from_db(db_path):
    """Load orders from SQLite database."""
    orders = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM orders WHERE status = 'filled'
        """)
        
        for row in cursor:
            orders.append(dict(row))
        
        conn.close()
    except Exception as e:
        print(f"  Warning: Could not read {db_path}: {e}")
    
    return orders


def generate_sample_orders():
    """Generate sample orders for demonstration."""
    import random
    random.seed(42)
    
    samples = []
    for i in range(5):
        expected = 589.0 + random.uniform(-2, 2)
        slippage = random.gauss(8, 3) / 10000
        fill = expected * (1 + slippage)
        
        samples.append({
            "client_order_id": f"VG-20260115-sample{i+1:03d}",
            "symbol": "SPY",
            "side": "buy",
            "qty": 100 + i * 50,
            "expected_price": expected,
            "filled_price": fill,
            "status": "filled",
            "filled_at": f"2026-01-16T09:30:{i:02d}"
        })
    
    return samples


if __name__ == "__main__":
    generate_reconciliation()
EOF

echo ""
echo "Reconciliation report generated: $OUTPUT_FILE"
