# Dashboard Walkthrough: Supergraph Pro (Manager's Suite)

> **Application**: Full Stack (React Frontend + FastAPI Backend)
> **Status**: Active / Paper Trading Ready
> **URL**: `http://localhost:5173`

![Supergraph Pro React Dashboard](/home/aarav/Tradingview/supergraph-pro/docs/assets/dashboard_react_overview.png)

The **Supergraph Pro (Manager's Suite)** is the advanced, production-grade interface for VolGate. Unlike the simulated prototype, this full-stack application connects to live market data streams and provides institutional-grade analytics.

---

## 1. Core Interface & Layout

The dashboard is built on a **React Grid Layout**, allowing for modular, draggable, and resizable panels.

-   **Top Deck (Market Context)**:
    -   **TradingView Chart**: Full-featured candlestick chart with drawing tools and indicators.
    -   **P/L Visualizer**: Interactive payoff diagram for the active portfolio.
-   **Middle Deck (Analytics)**:
    -   **Position Greeks**: Real-time aggregation of portfolio risk.
    -   **Strategy Comparison**: Side-by-side backtest/simulation of competing strategies.
    -   **Volatility Cone**: IV vs Realized Volatility analysis.
-   **Bottom Deck (Execution)**:
    -   **Active Legs**: Detailed breakdown of current positions.
    -   **Trade Journal**: Integrated logging of trading decisions.

---

## 2. Advanced Analytics Engines

### Position Greeks (Real-Time)
Aggregates risk across all active simulated positions:
-   **Beta-Weighted Delta**: Portfolio directional exposure standardized to SPY.
-   **Gamma**: Curvature risk (acceleration of Delta).
-   **Theta**: Daily time decay collection.
-   **Vega**: Sensitivity to volatility expansion/contraction.

### Strategy Comparison Tool
A "Sandbox" environment to pit two strategies against each other (e.g., *Iron Condor* vs. *Straddle*).
-   **Visual Comparison**: Overlaid payoff diagrams.
-   **Metric Diff**: Direct comparison of Max Profit, Max Loss, and Breakeven width.

### Volatility Analysis (IV vs RV Cone)
A dedicated module for regime detection:
-   **Cone Visualization**: Plots Implied Volatility (IV) against Realized Volatility (RV) cones (10th-90th percentile).
-   **Signal Generation**:
    -   **"Options Expensive"**: When IV > 90th percentile RV (Sell Premium).
    -   **"Options Cheap"**: When IV < 10th percentile RV (Buy Premium).

---

## 3. AutoPilot & Journaling

This dashboard integrates directly with the AI-driven components:

-   **AutoPilot Control**: Toggle algorithmic execution (e.g., "VolGate" logic) on/off directly from the UI.
-   **Trade Journal**:
    -   Automatically logs all trades (Paper/Live).
    -   Allows manual annotation of "Why" (e.g., "Faded the news").
    -   Tags trades by Regime (e.g., "High Volatility", "Trending").

---

## 4. Technical Stack

-   **Frontend**: React, Vite, Plotly.js, Lightweight Charts.
-   **Backend**: FastAPI (Python), Uvicorn.
-   **Data**: Live market feed via backend WebSocket bridge.
-   **State**: Real-time sync between UI and backend `Strategy` objects.
