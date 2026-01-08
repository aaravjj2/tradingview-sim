# Dashboard Walkthrough: Supergraph Pro (Manager's Suite)

> **Application**: Full Stack (React Frontend + FastAPI Backend)
> **Status**: Active / Paper Trading Ready
> **URL**: `http://localhost:5173`

![Supergraph Pro React Dashboard](/home/aarav/Tradingview/supergraph-pro/docs/assets/dashboard_react_overview.png)

The **Supergraph Pro (Manager's Suite)** is the advanced, production-grade interface for VolGate. Unlike the simulated prototype, this full-stack application connects to live market data streams and provides institutional-grade analytics.

---

## 1. Core Architecture

The dashboard is built on a high-performance **React Grid Layout** powered by a **FastAPI** backend.

-   **Frontend State**: Real-time sync via React Query and WebSockets.
-   **Backend Engine**: Python-based pricing engine (Black-Scholes) serving data to the UI.
-   **Layout**: Fully modular; panels can be dragged, resized, or hidden via the *Context Sidebar*.

---

## 2. Advanced Analytics Engines

### A. The Supergraph (Payoff Visualizer)
The heart of the dashboard (`Supergraph.tsx`). It renders interactive P/L diagrams with institutional tools:
-   **Theoretical Pricing**: Uses Black-Scholes ($d_1, d_2$) to calculate option prices at any spot price point.
-   **Ghost Curves**: Allows locking a "baseline" curve to compare "What-If" scenarios (e.g., *What if IV drops 10%?*).
-   **Breakeven Scanner**: Automatically solves for $P/L = 0$ roots to display exact breakeven prices.
-   **Time Value Fill**: Visualizes the theta component (extrinsic value) as a shaded region between the T+0 and T+Exp curves.

### B. Strategy Comparison Sandbox
A dedicated environment (`StrategyComparison.tsx`) for pitting strategies against each other.
-   **Use Case**: deciding between an *Iron Condor* (neutral, defined risk) vs. a *Straddle* (neutral, undefined risk).
-   **Visual Diff**: Overlays two payoff curves on the same axes.
-   **Metric Diff**: Automatically calculates and compares:
    -   **Max Profit/Loss**
    -   **Breakeven Width** (which strategy needs a larger move to lose?)
    -   **Probability of Profit (POP)**

### C. Volatility Analysis (IV vs RV Cone)
A regime detection module (`IVRVCone.tsx`) critical for the VolGate strategy.
-   **Term Structure**: Visualizes IV across multiple timeframes (7, 14, 30, 60, 90 days).
-   **Cone Logic**: Plots 1$\sigma$ and 2$\sigma$ cones based on Realized Volatility (RV).
-   **Signal Generation**:
    -   **"Options Expensive"** (Sell Premium): Triggered when Current IV > 90th percentile RV.
    -   **"Options Cheap"** (Buy Premium): Triggered when Current IV < 10th percentile RV.
-   **Calculated Premium**: Displays the *IV Premium* spread ($IV / RV - 1$) in real-time.

---

## 3. Position Risk Management (Greeks)

The **Context Sidebar** and **Greeks Panel** provide granular risk control.

### Position Greeks (Real-Time)
Aggregates risk across the entire active portfolio:
-   **Beta-Weighted Delta ($\beta\Delta$)**: Portfolio directional exposure standardized to SPY. 
    -   *Formula*: $\sum (Position \Delta \times \frac{Price_{Asset}}{Price_{SPY}} \times \beta_{Asset})$
-   **Gamma ($\Gamma$)**: Curvature risk; how fast your Delta changes.
-   **Theta ($\Theta$)**: Daily time decay collection (your "rent" collection).
-   **Vega ($\nu$)**: Sensitivity to volatility expansion/contraction.

### Configuration Controls (`ContextSidebar.tsx`)
-   **Chart Overlays**: Toggle SMA (5-200), EMA, Bollinger Bands, RSI, MACD.
-   **Supergraph Simulation**:
    -   **IV Adjustment**: Slider to shock Implied Volatility (-50% to +50%) across all legs.
    -   **Day Step**: Time-travel slider to simulate P/L at T+7, T+14, etc.

---

## 4. Execution & Automation

### AutoPilot Integration
Direct control over the algorithmic execution engine:
-   **Toggle**: Enable/Disable the `VolGate` algo directly from the UI header.
-   **Status**: Visual indicator of the active regime (*Trending*, *Choppy*, *Panic*).

### Trade Journal
An integrated logging system (`TradeJournal.tsx`) for compliance and review:
-   **Auto-Logging**: All paper/live fills are automatically captured.
-   **Manual Annotation**: Add notes on *Why* a trade was taken (e.g., "Faded CPI print").
-   **Tagging**: tagging trades by Regime or Strategy Type for performance attribution.

---

## 5. Technical Components Stack

| Component | Library | Purpose |
|-----------|---------|---------|
| **Charts** | `react-plotly.js` | Interactive scientific plotting (Supergraph, Vol Cone) |
| **Candles** | `lightweight-charts` | High-performance canvas rendering for price history |
| **Grid** | `react-grid-layout` | Draggable/Resizable dashboard windows |
| **State** | React Query | Server state management (polling/caching) |
| **Styling** | Tailwind CSS | Utility-first "Premium Dark" theme |
