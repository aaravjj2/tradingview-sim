# Options Overlay Runbook

> **Version**: 1.0
> **Status**: Paper-Only (until micro-live validated)
> **Scope**: Protective Puts (buy side only)

---

## Overview

The options overlay provides tail risk protection through protective puts.
Until micro-live is fully validated, all options activity is **paper-only**.

---

## Allowed Strategies

### ✅ Allowed (Paper/Conditional Live)

| Strategy | Description | Risk Level |
|----------|-------------|------------|
| Protective Puts | Long 30-delta puts | Low |
| Put Spreads | Long put + short lower put | Low |

### ❌ Not Allowed (Requires Separate Review)

| Strategy | Description | Why Blocked |
|----------|-------------|-------------|
| Naked Short Puts | Selling puts without hedge | Unlimited risk |
| Call Writing | Selling calls | Capped upside, unlimited risk |
| Complex Spreads | Iron condors, butterflies | Operational complexity |

---

## Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Target Delta | 30 | OTM for cost efficiency |
| DTE Range | 30-45 days | Theta balance |
| Protection % | 50% notional | Half the portfolio |
| Annual Budget | 2% of capital | Cost cap |
| Roll Window | 7 days before expiry | Avoid gamma risk |

---

## Order Construction

### Protective Put (Single Leg)

```python
from src.options.protective_puts import ProtectivePutsOverlay

overlay = ProtectivePutsOverlay()
result = overlay.add_protection(
    symbol="SPY",
    spot_price=590,
    portfolio_value=25000,
    current_date=date.today(),
    volatility=0.20
)
```

### Put Spread (Multi-Leg)

```python
from src.options.protective_puts import OptionsSimulator

sim = OptionsSimulator()
spread = sim.create_put_spread(
    symbol="SPY",
    spot=590,
    target_delta=0.30,
    dte=30,
    spread_width_pct=0.10
)
```

---

## Multi-Leg Execution Fallbacks

If the broker rejects a multi-leg order:

1. **Attempt 1**: Submit as single combo order
2. **Attempt 2**: Submit legs sequentially (long first)
3. **Attempt 3**: Abort and alert operator

```python
# Fallback logic in options_adapter.py
def execute_spread_with_fallback(spread):
    try:
        # Try combo order
        return broker.submit_combo(spread)
    except ComboRejectError:
        # Try sequential
        long_fill = broker.submit_single(spread.long_put)
        if long_fill:
            short_fill = broker.submit_single(spread.short_put)
            return (long_fill, short_fill)
        else:
            raise ExecutionFailure("Could not execute spread")
```

---

## Assignment Handling

If a put is assigned (spot < strike at expiry):

1. **Detection**: Check positions for unexpected stock assignment
2. **Action**: Close assigned stock position at market open
3. **Logging**: Log assignment event for reconciliation
4. **Margin**: Verify margin not breached

```python
def handle_assignment(position):
    if position.is_assigned:
        # Close immediately
        close_order = create_market_close(position.assigned_stock)
        submit_order(close_order)
        
        # Log
        log_assignment_event(position)
        
        # Check margin
        if margin_breached():
            trigger_kill_switch("margin_breach")
```

---

## Margin & Buying Power Checks

Before any options order:

```python
def check_margin_safety(order, account):
    required_margin = calculate_required_margin(order)
    available_margin = account.buying_power
    
    if required_margin > available_margin * 0.5:  # 50% buffer
        raise MarginSafetyError(
            f"Order requires {required_margin}, only {available_margin} available"
        )
    
    return True
```

### Rejection Scenarios

| Scenario | Action |
|----------|--------|
| Insufficient margin | Reject order |
| Spread exceeds width limit | Reject order |
| DTE outside range | Reject order |
| Delta outside range | Reject order |

---

## Stress Test Scenarios

The options overlay must handle these scenarios:

### 1. 2008 Financial Crisis

- SPY drops 50% over 12 months
- VIX spikes to 80+
- Put premium increases 5x

**Expected**: Puts offset losses

### 2. 2020 COVID Crash

- SPY drops 35% in 4 weeks
- VIX spikes to 82
- Liquidity dries up

**Expected**: Puts trigger, spreads may widen

### 3. Flash Crash

- SPY drops 10% in 15 minutes
- Immediate recovery
- Bid-ask spreads blow out

**Expected**: Do not panic-sell puts

---

## Testing Requirements

All tests in `tests/test_options_overlay.py` must pass:

- [ ] Greeks calculation
- [ ] Put price calculation
- [ ] Synthetic chain generation
- [ ] Delta targeting
- [ ] Protection config
- [ ] Budget limit
- [ ] Spread creation
- [ ] Crash scenario protection
- [ ] Margin safety

---

## Paper to Live Transition

To enable options in live:

1. Complete micro-live pilot (equities only)
2. Run paper options for 7+ days
3. Verify all tests passing
4. Submit 3-person signoff
5. Start with protective puts only
6. No spreads in first live week

---

## Emergency Procedures

### Option Position Emergency Close

```bash
# Close all options positions immediately
python scripts/emergency_close_options.py --market
```

### Disable Options Overlay

```yaml
# configs/config.volgate.yaml
options:
  enabled: false  # Disable all options activity
```

---

*Last Updated: 2026-01-08*
