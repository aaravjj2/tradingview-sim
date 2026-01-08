#!/bin/bash
# Nightly Smoke Test Script
#
# Runs a fast subset of reality compression simulations
# as a smoke test to catch any regressions.
#
# Usage:
#   ./scripts/nightly_smoke_test.sh [--simulations N] [--days D]

set -e

# Default parameters
SIMULATIONS=${SIMULATIONS:-10}
DAYS=${DAYS:-60}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/artifacts/nightly_smoke"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --simulations)
            SIMULATIONS="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "=========================================="
echo "NIGHTLY SMOKE TEST"
echo "=========================================="
echo "Simulations: $SIMULATIONS"
echo "Days: $DAYS"
echo "Output: $OUTPUT_DIR"
echo "=========================================="

# Ensure output directory
mkdir -p "$OUTPUT_DIR"

# Set environment
export TRADING_MODE=paper
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Run mini reality compression
cd "$PROJECT_DIR"

python3 -c "
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, '.')

from src.analytics.reality_compression import RealityCompressionEngine

print('Running Reality Compression Smoke Test...')

engine = RealityCompressionEngine()

# Run fast subset
results = engine.run_batch_simulations(
    symbols=['SPY'],
    n_simulations=${SIMULATIONS},
    n_days=${DAYS},
    seeds=range(${SIMULATIONS})
)

# Check results
all_survived = all(r['survived'] for r in results)
avg_dd = sum(r['max_dd_pct'] for r in results) / len(results)

print()
print('='*50)
print('SMOKE TEST RESULTS')
print('='*50)
print(f'Simulations: {len(results)}')
print(f'Survival Rate: {sum(r[\"survived\"] for r in results) / len(results) * 100:.1f}%')
print(f'Avg Max DD: {avg_dd:.1f}%')
print(f'Status: {\"✅ PASSED\" if all_survived else \"❌ FAILED\"}'  )
print('='*50)

# Save results
summary = {
    'timestamp': datetime.now().isoformat(),
    'simulations': len(results),
    'survival_rate': sum(r['survived'] for r in results) / len(results) * 100,
    'avg_max_dd': avg_dd,
    'passed': all_survived,
}

with open('$OUTPUT_DIR/smoke_test_latest.json', 'w') as f:
    json.dump(summary, f, indent=2)

sys.exit(0 if all_survived else 1)
"

SMOKE_EXIT=$?

# Run behavioral audit smoke
echo ""
echo "Running Behavioral Audit Smoke Test..."

python3 -c "
import sys
sys.path.insert(0, '.')

from src.analytics.behavioral_audit import BehavioralAudit

audit = BehavioralAudit()
result = audit.run_audit('SPY', days=60, seed=42)

passed = result['all_checks_passed']

print('='*50)
print(f'Behavioral Audit: {\"✅ PASSED\" if passed else \"❌ FAILED\"}')
print('Checks:')
for check, value in result['checks'].items():
    print(f'  {\"✅\" if value else \"❌\"} {check}')
print('='*50)

sys.exit(0 if passed else 1)
"

BEHAVIORAL_EXIT=$?

# Summary
echo ""
echo "=========================================="
echo "NIGHTLY SMOKE TEST SUMMARY"
echo "=========================================="

if [ $SMOKE_EXIT -eq 0 ] && [ $BEHAVIORAL_EXIT -eq 0 ]; then
    echo "✅ ALL SMOKE TESTS PASSED"
    exit 0
else
    echo "❌ SMOKE TESTS FAILED"
    exit 1
fi
