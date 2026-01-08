# Live Pilot Runbook

> **Version**: 1.0
> **Status**: REQUIRES 3-PERSON SIGNOFF
> **Mode**: Micro-Live Seed Deployment

---

## Pre-Flight Checklist

### Required Signoffs (3-person minimum)

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Quant Lead | _____________ | _____________ | _____________ |
| Ops Lead | _____________ | _____________ | _____________ |
| Risk Lead | _____________ | _____________ | _____________ |

> [!CAUTION]
> DO NOT proceed until all three signoffs are obtained.

---

## Phase A Verification (Pre-Requisite)

Before enabling live mode, verify Phase A completion:

- [ ] 14+ observation days completed
- [ ] No unexplained regime flips (≤5 total)
- [ ] Slippage within modeled tolerance (≤15 bps)
- [ ] Time-in-market consistent (15-90%)
- [ ] All nightly smoke tests passing
- [ ] Full falsification re-run passed

```bash
# Verify observation status
python scripts/daily_observation.py --date $(date +%Y-%m-%d)
```

---

## Pilot Parameters (STRICT)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Initial Capital | ≤$2,500 | 10% of $25k recommendation |
| Max Position | $2,500 | 100% in single position |
| Single Asset | SPY only | No diversification in pilot |
| Options | DISABLED | Paper-only until validated |
| Target Trades | 10-30 | Over minimum 5 trading days |

---

## Live Mode Activation Steps

> [!WARNING]
> These steps enable real money trading. Proceed with extreme caution.

### Step 1: Environment Preparation

```bash
# Verify paper mode is default
echo $TRADING_MODE  # Should be 'paper' or empty

# Verify broker keys are configured
echo $ALPACA_API_KEY | head -c 5  # Should show first 5 chars
```

### Step 2: Config Update

> [!CAUTION]
> Do NOT commit this change. Revert after pilot.

```yaml
# configs/config.volgate.yaml - TEMPORARY ONLY
trading:
  mode: live  # DANGEROUS - revert after pilot
  pilot_mode: true  # Enables pilot safety limits
  pilot_capital: 2500
  pilot_asset: SPY
```

### Step 3: Code Assertion Bypass

The live mode assertion in `model_adapter.py` must be temporarily bypassed:

```python
# workspace/volgate/model_adapter.py - LINE ~50
# COMMENT OUT FOR PILOT ONLY:
# if trading_mode == "live":
#     raise RuntimeError("Live trading disabled in this release")
```

### Step 4: Start Pilot Monitor

```bash
# Terminal 1: Main trading process
TRADING_MODE=live python scripts/daily_observation.py --symbol SPY

# Terminal 2: Live pilot monitor (required)
python scripts/live_pilot_monitor.py --capital 2500 --asset SPY
```

---

## Kill Switch Thresholds

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Slippage | >50 bps | Halt + alert |
| Daily Loss | >1% ($25) | Halt + exit positions |
| Fill Miss | >5% | Halt + review |
| API Error | 3 consecutive | Halt + manual review |

---

## Auto-Rollback Procedure

If any kill switch triggers:

1. **Immediate**: All pending orders cancelled
2. **Immediate**: All positions closed at market
3. **Immediate**: Mode reverted to paper
4. **Within 1 hour**: Incident report generated
5. **Within 24 hours**: Root cause analysis

```bash
# Manual rollback command
python scripts/emergency_rollback.py --reason "Kill switch triggered"
```

---

## Daily Pilot Monitoring

### Pre-Market (8:30 AM ET)

- [ ] Verify broker connection
- [ ] Check overnight fills (if any)
- [ ] Confirm capital allocation correct

### Market Hours

- [ ] Monitor slippage alerts
- [ ] Check regime signal
- [ ] Verify fill confirmations

### Post-Market (4:15 PM ET)

- [ ] Run reconciliation
- [ ] Log daily metrics
- [ ] Update pilot log

---

## Pilot Success Criteria

After 10-30 trades over 5+ days:

| Metric | Target | Actual |
|--------|--------|--------|
| Live slippage ≈ simulated | ±5 bps | _______ |
| No position mismatches | 0 | _______ |
| No unrecoverable errors | 0 | _______ |
| Kill switch triggers | 0 | _______ |

---

## Post-Pilot Actions

### If Pilot PASSES:

1. Document results in `artifacts/live_pilot_report.zip`
2. Update `docs/capital_decision.md` with live observations
3. Propose staged scale plan (→$10k→$25k)

### If Pilot FAILS:

1. Immediately revert to paper mode
2. Document all failures
3. Return to Phase A for extended observation
4. Do NOT re-attempt without root cause fix

---

## Emergency Contacts

| Role | Contact | Phone |
|------|---------|-------|
| Quant Lead | _______ | _______ |
| Ops Lead | _______ | _______ |
| Broker Support | Alpaca | support@alpaca.markets |

---

*This runbook requires physical or electronic signature from all three signoffs before any live trading is permitted.*

*Last Updated: 2026-01-08*
