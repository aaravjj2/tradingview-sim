#!/bin/bash
#
# Reality Compression Runner
#
# Runs ≥100 randomized simulations across SPY, GLD, TLT
# Saves results to artifacts/reality_compression/
#
# Usage:
#   ./scripts/run_compressed_reality.sh [--simulations=100] [--days=252]
#

set -e

# Parse arguments
SIMULATIONS=100
DAYS=252

for arg in "$@"; do
    case $arg in
        --simulations=*)
            SIMULATIONS="${arg#*=}"
            ;;
        --days=*)
            DAYS="${arg#*=}"
            ;;
    esac
done

echo "=========================================="
echo "Reality Compression Engine"
echo "=========================================="
echo "Simulations per symbol: $SIMULATIONS"
echo "Days per simulation: $DAYS"
echo "Symbols: SPY, GLD, TLT"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Ensure output directory exists
mkdir -p artifacts/reality_compression

# Run the compression engine
TRADING_MODE=shadow python3 << EOF
import sys
sys.path.insert(0, ".")

from src.analytics.reality_compression import run_compressed_reality

symbols = ["SPY", "GLD", "TLT"]
summary = run_compressed_reality(symbols, simulations=$SIMULATIONS, days=$DAYS)

print()
print("=" * 50)
print("REALITY COMPRESSION COMPLETE")
print("=" * 50)
print(f"Total Simulations: {summary['overall']['total_simulations']}")
print(f"Survival Rate: {summary['overall']['survival_rate']:.1f}%")
print(f"Avg Max DD: {summary['overall']['avg_max_dd_pct']:.1f}%")
print(f"P95 Max DD: {summary['overall']['p95_max_dd_pct']:.1f}%")
print(f"Avg Exit Latency: {summary['overall']['avg_exit_latency_bars']:.1f} bars")
print("=" * 50)

# Per-symbol breakdown
print()
print("Per-Symbol Results:")
print("-" * 50)
for symbol, stats in summary['symbols'].items():
    print(f"  {symbol}:")
    print(f"    Survival Rate: {stats['survival_rate']:.1f}%")
    print(f"    Avg Max DD: {stats['avg_max_dd_pct']:.1f}%")
    print(f"    Avg P&L: \${stats['avg_pnl']:,.0f}")
print()

# Check acceptance criteria
criteria = summary['overall']['acceptance_criteria']
if criteria['survival_rate_met'] and criteria['exit_latency_met']:
    print("✅ ALL ACCEPTANCE CRITERIA MET")
    exit_code = 0
else:
    print("❌ ACCEPTANCE CRITERIA NOT MET")
    if not criteria['survival_rate_met']:
        print(f"   - Survival rate {summary['overall']['survival_rate']:.1f}% < {criteria['survival_rate_target']}%")
    if not criteria['exit_latency_met']:
        print(f"   - Exit latency P95 > {criteria['exit_latency_target']} bars")
    exit_code = 1

print()
print(f"Results saved to: artifacts/reality_compression/")

sys.exit(exit_code)
EOF

echo ""
echo "Reality compression simulation complete."
echo "Results: artifacts/reality_compression/"
