# Dashboard Walkthrough: Options Supergraph Pro

> **Application**: `main.py` (Phase 2)
> **Status**: Active / Paper Trading Ready

The **Options Supergraph Pro** is a professional-grade options strategy visualizer and trading simulator designed for rapid prototyping and risk analysis. It features a modern, split-panel dark mode interface optimized for analyzing complex multi-leg options strategies.

---

## 1. Core Interface & Layout

The dashboard utilizes a **dual-pane split layout** to maximize information density without clutter:

-   **Left Panel (Market Data)**: Dedicated to price action, displaying real-time candlestick charts with technical overlays.
-   **Right Panel (The Supergraph)**: The core visualization engine displaying interactive payoff diagrams.
-   **Sidebar (Controls)**: Collapsible command center for strategy configuration and inputs.
-   **Bottom Deck (Analytics)**: High-level metrics, Greeks, and account summary.

> **Visual Style**: "Premium Dark" theme with color-coded directional cues (Green/Red for P&L, Purple/Orange for probabilities/Greeks).

---

## 2. "The Supergraph" Visualizer (Right Panel)

The flagship feature of the dashboard is the interactive payoff diagram.

-   **Theoretical Curves**:
    -   **Gold Line**: P&L at expiration (T+Exp).
    -   **Cyan Dashed Line**: Current theoretical P&L (T+0), adjusted for Volatility and Time to Expiry.
    -   **Purple Dot Line**: "Ghost Curve" (Locked baseline) for comparing "What-If" scenarios.
-   **Interactive Elements**:
    -   **Hover Tooltips**: Exact P&L values at any price point for both current and expiration curves.
    -   **Breakeven Diamonds**: Orange diamond markers indicating exact breakeven price points.
    -   **Current Price Line**: Vertical dashed line showing the asset's current live trading price.
    -   **Time Value Fill**: Shaded region visualizing the theta (time value) component of the position.

### "Ghost Curve" What-If Analysis
A specialized feature allowing traders to **Lock** the current curve as a baseline.
-   **Workflow**: Configure a strategy -> Click "Lock Curve" -> Adjust Implied Volatility (IV) sliders.
-   **Result**: See the new curve superimposed over the "Ghost" (locked) curve to visualize Vega risk or Theta decay dynamics instantly.

---

## 3. Real-Time Price Charting (Left Panel)

A professional Charting interface built with Plotly:

-   **Candlesticks**: OHLC(V) bars for granular price action analysis.
-   **Technical Overlays** (Toggleable):
    -   **SMA 20 & 50**: Key trend lines.
    -   **Bollinger Bands**: Volatility envelopes.
    -   **RSI (14)**: Momentum oscillator (appears in sub-panel when enabled).
-   **Live Price Marker**: Dashed blue line indicating current market price relative to history.

---

## 4. Strategy Builder Engine (Sidebar)

A flexible configuration engine for defining trades:

-   **Templates**: Quick-load presets for common strategies:
    -   *Iron Condor, Butterfly, Straddle, Strangle, Vertical Spreads, Protective Puts*.
-   **Custom Leg Designer**:
    -   Add/Remove unlimited legs.
    -   Configure: Type (Stock/Call/Put), Action (Buy/Sell), Strike, Expiration, Quantity.
-   **Dynamic Pricing**:
    -   Auto-fetches real options chain data (via keys/adapter).
    -   Calculates Black-Scholes premiums on the fly for simulation.
-   **Simulation Controls**:
    -   **IV Adjustment**: Slider to shock Implied Volatility (-50% to +50%).
    -   **Time Travel**: Slider to simulate "Days to Expiration" passing.

---

## 5. Analytics & Risk Metrics

A comprehensive "Heads Up Display" for risk management:

### Probability & Returns
-   **Max Profit**: Green metric (supports "Unlimited").
-   **Max Loss**: Red metric (supports "Unlimited").
-   **Probability of Profit (POP)**: Monte-Carlo derived probability score.
-   **Breakevens**: Exact price levels where P&L = 0.

### The Greeks (Risk Sensitivities)
-   **Delta (Δ)**: Directional exposure.
-   **Gamma (Γ)**: Acceleration of directional exposure.
-   **Theta (Θ)**: Time decay (dollars per day).
-   **Vega (ν)**: Sensitivity to volatility changes.

---

## 6. Trading Engine Controls

Seamlessly switch between simulation and execution:

-   **Mode Toggle**:
    -   **📝 PAPER**: Safety mode using virtual funds ($100k start).
    -   **🔴 LIVE**: Connects to real broker API (Disabled by default for safety).
-   **Execution Routing**:
    -   **Local Simulator**: Instant fills based on theoretical prices.
    -   **Alpaca Paper API**: Routes orders to Alpaca's paper trading environment for realistic fill validation.
-   **Account Summary**:
    -   Live P&L tracking.
    -   Open positions list.
    -   Buying power monitoring.
-   **Legs Table**: Detail view of every component in the active strategy (Strike, Premium, IV).

---

## 7. Educational Layer

Built-in "Onboarding" features for new users:
-   **Collapsible Help**: Explains layout, "Ghost Curve" usage, and Greeks.
-   **Tooltips**: Contextual help on hover for complex inputs.
