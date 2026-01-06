"""
Options Supergraph Dashboard - Main Application (Phase 2)
Professional Options Strategy Visualizer & Trading Simulator

Features:
- Split-panel layout (Candles | Supergraph)
- Real-time price streaming via WebSocket
- Paper trading mode
- Ghost curve for What-If analysis
- Dynamic crosshair with live P&L
- Technical indicators
- IV Surface visualization

Run with: streamlit run main.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import time

from config import (
    STRATEGY_TEMPLATES, DEFAULT_RISK_FREE_RATE, 
    PRICE_RANGE_PERCENT, DEFAULT_STRIKE_INTERVAL
)
from data_manager import (
    get_current_price, get_implied_volatility, 
    get_available_expirations, data_manager
)
from logic import (
    OptionLeg, build_strategy_legs, generate_price_range,
    calculate_expiration_payoff, calculate_theoretical_payoff,
    calculate_position_greeks, find_breakeven_points,
    calculate_max_profit_loss, calculate_probability_of_profit,
    calculate_pnl_at_price, calculate_sma, calculate_ema,
    calculate_rsi, calculate_bollinger_bands, calculate_iv_surface
)
from database import (
    init_db, store_candles, get_candles, get_candle_count
)
from paper_trading import paper_account
from strategy import Strategy, StrategyBuilder

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="Options Supergraph Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    :root {
        --profit-green: #00C853;
        --loss-red: #FF1744;
        --neutral-blue: #2196F3;
        --dark-bg: #0E1117;
        --card-bg: #1E2329;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.8);
        margin: 0.25rem 0 0 0;
        font-size: 0.9rem;
    }
    
    .metric-card {
        background: linear-gradient(145deg, #1a1f2e, #151923);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .metric-card.profit { border-left: 4px solid #00C853; }
    .metric-card.loss { border-left: 4px solid #FF1744; }
    .metric-card.info { border-left: 4px solid #2196F3; }
    .metric-card.warning { border-left: 4px solid #FF9800; }
    
    .metric-label {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.6);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.25rem;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    .metric-value.green { color: #00C853; }
    .metric-value.red { color: #FF1744; }
    .metric-value.blue { color: #2196F3; }
    .metric-value.purple { color: #9C27B0; }
    .metric-value.orange { color: #FF9800; }
    
    .mode-toggle {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .paper-badge {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        color: black;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    
    .live-badge {
        background: linear-gradient(135deg, #00C853, #00E676);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .ghost-curve-info {
        background: rgba(156, 39, 176, 0.1);
        border: 1px solid rgba(156, 39, 176, 0.3);
        border-radius: 8px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Session State Initialization
# =============================================================================

if "paper_mode" not in st.session_state:
    st.session_state.paper_mode = True

if "lock_curve" not in st.session_state:
    st.session_state.lock_curve = False

if "locked_iv" not in st.session_state:
    st.session_state.locked_iv = None

if "locked_days" not in st.session_state:
    st.session_state.locked_days = None

if "show_indicators" not in st.session_state:
    st.session_state.show_indicators = {"sma_20": True, "sma_50": False, "bb": False, "rsi": False}

if "candle_data" not in st.session_state:
    st.session_state.candle_data = []

if "last_price_update" not in st.session_state:
    st.session_state.last_price_update = time.time()

# =============================================================================
# Header
# =============================================================================

header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.markdown("""
    <div class="main-header">
        <h1>📈 Options Supergraph Pro</h1>
        <p>Professional Options Visualizer • Black-Scholes Engine • Paper Trading</p>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    # Trading mode toggle
    mode_label = "📝 PAPER" if st.session_state.paper_mode else "🔴 LIVE"
    mode_class = "paper-badge" if st.session_state.paper_mode else "live-badge"
    st.markdown(f'<span class="{mode_class}">{mode_label}</span>', unsafe_allow_html=True)
    
    if st.button("Switch Mode", key="mode_toggle"):
        st.session_state.paper_mode = not st.session_state.paper_mode
        st.rerun()

# =============================================================================
# Sidebar - Inputs
# =============================================================================

with st.sidebar:
    st.markdown("### 📊 Strategy Builder")
    
    # Ticker Input
    ticker = st.text_input(
        "Stock Ticker",
        value="SPY",
        help="Enter a stock symbol (e.g., SPY, NVDA, AAPL)"
    ).upper()
    
    # Fetch current price
    if ticker:
        with st.spinner(f"Fetching {ticker} data..."):
            current_price = get_current_price(ticker)
            if current_price:
                st.success(f"**{ticker}**: ${current_price:.2f}")
                base_iv = get_implied_volatility(ticker, current_price)
            else:
                st.error("Could not fetch price. Using demo mode.")
                current_price = 500.0
                base_iv = 0.25
    else:
        current_price = 500.0
        base_iv = 0.25
    
    st.markdown("---")
    
    # Strategy Selection
    st.markdown("### 🎯 Strategy")
    strategy_name = st.selectbox(
        "Select Strategy",
        options=list(STRATEGY_TEMPLATES.keys()),
        index=0,
        help="Choose a predefined strategy or build custom"
    )
    
    # Expiration Selection
    st.markdown("---")
    st.markdown("### 📅 Expiration")
    
    expirations = get_available_expirations(ticker)
    if expirations:
        selected_expiration = st.selectbox(
            "Select Expiration",
            options=expirations,
            index=0
        )
        exp_date = datetime.strptime(selected_expiration, "%Y-%m-%d")
        days_to_expiration = max(1, (exp_date - datetime.now()).days)
    else:
        days_to_expiration = st.slider(
            "Days to Expiration",
            min_value=1,
            max_value=90,
            value=30,
            step=1
        )
    
    st.info(f"**DTE:** {days_to_expiration} days")
    
    # Strike Interval
    strike_interval = st.selectbox(
        "Strike Interval",
        options=[1.0, 2.5, 5.0, 10.0, 25.0],
        index=2
    )
    
    st.markdown("---")
    
    # Simulation Controls
    st.markdown("### ⚡ Simulation Controls")
    
    # Ghost Curve Toggle
    lock_curve = st.checkbox("🔒 Lock Live Curve (Ghost Mode)", 
                             value=st.session_state.lock_curve,
                             help="Lock current curve and show a 'ghost' for comparison")
    
    if lock_curve and not st.session_state.lock_curve:
        # Just locked - save current values
        st.session_state.locked_iv = base_iv
        st.session_state.locked_days = days_to_expiration
    
    st.session_state.lock_curve = lock_curve
    
    if lock_curve:
        st.markdown('<div class="ghost-curve-info">🔮 Ghost curve locked. Adjust sliders to compare.</div>', 
                    unsafe_allow_html=True)
    
    # IV Adjustment
    iv_adjustment = st.slider(
        "IV Adjustment",
        min_value=-50,
        max_value=50,
        value=0,
        step=5,
        help="Simulate IV crush or expansion",
        format="%d%%"
    ) / 100.0
    
    adjusted_iv = base_iv + iv_adjustment
    if iv_adjustment != 0:
        color = "🟢" if iv_adjustment > 0 else "🔴"
        st.caption(f"{color} IV: {base_iv*100:.1f}% → {adjusted_iv*100:.1f}%")
    
    # Time Slider
    days_forward = st.slider(
        "Days Forward (T+X)",
        min_value=0,
        max_value=days_to_expiration,
        value=0,
        step=1,
        help="Simulate the passage of time"
    )
    
    days_remaining = max(0.001, days_to_expiration - days_forward)
    if days_forward > 0:
        st.caption(f"⏰ Simulating T+{days_forward} ({days_remaining:.0f} DTE)")
    
    # Price Range
    price_range_pct = st.slider(
        "Price Range",
        min_value=10,
        max_value=50,
        value=20,
        step=5
    ) / 100.0
    
    st.markdown("---")
    
    # Indicator Controls
    st.markdown("### 📉 Chart Indicators")
    show_sma20 = st.checkbox("SMA (20)", value=st.session_state.show_indicators["sma_20"])
    show_sma50 = st.checkbox("SMA (50)", value=st.session_state.show_indicators["sma_50"])
    show_bb = st.checkbox("Bollinger Bands", value=st.session_state.show_indicators["bb"])
    show_rsi = st.checkbox("RSI (14)", value=st.session_state.show_indicators["rsi"])
    
    st.session_state.show_indicators = {
        "sma_20": show_sma20,
        "sma_50": show_sma50,
        "bb": show_bb,
        "rsi": show_rsi
    }

# =============================================================================
# Build Strategy
# =============================================================================

strategy_template = STRATEGY_TEMPLATES.get(strategy_name, [])

if strategy_template:
    legs = build_strategy_legs(
        strategy_template=strategy_template,
        current_price=current_price,
        strike_interval=strike_interval,
        base_iv=base_iv,
        days_to_expiration=days_to_expiration
    )
else:
    legs = []

# Generate price range
price_range = generate_price_range(current_price, price_range_pct)

# =============================================================================
# Calculate Payoffs
# =============================================================================

if legs:
    # Expiration payoff
    expiration_payoff = calculate_expiration_payoff(legs, price_range)
    
    # Current theoretical payoff
    theoretical_payoff = calculate_theoretical_payoff(
        legs, price_range, days_remaining, iv_adjustment
    )
    
    # Ghost curve (if locked)
    ghost_payoff = None
    if st.session_state.lock_curve and st.session_state.locked_iv is not None:
        ghost_payoff = calculate_theoretical_payoff(
            legs, price_range, 
            st.session_state.locked_days, 
            0  # No adjustment for locked curve
        )
    
    # Greeks and metrics
    position_greeks = calculate_position_greeks(legs, current_price, days_remaining)
    breakevens = find_breakeven_points(legs, price_range)
    max_profit, max_loss = calculate_max_profit_loss(legs, price_range)
    pop = calculate_probability_of_profit(legs, current_price, days_remaining, adjusted_iv)
else:
    expiration_payoff = np.zeros_like(price_range)
    theoretical_payoff = np.zeros_like(price_range)
    ghost_payoff = None
    position_greeks = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
    breakevens = []
    max_profit, max_loss = 0, 0
    pop = 0

# =============================================================================
# Main Content - Split Layout
# =============================================================================

# Create two columns for split layout
left_col, right_col = st.columns([1, 1])

# =============================================================================
# Left Column - Candle Chart
# =============================================================================

with left_col:
    st.markdown("### 📊 Price Chart")
    
    # Generate sample candle data for demonstration
    # In production, this would come from database/API
    np.random.seed(42)
    n_candles = 100
    
    base_price = current_price * 0.95
    prices = [base_price]
    for i in range(n_candles - 1):
        change = np.random.randn() * (current_price * 0.01)
        prices.append(prices[-1] + change)
    
    # Create OHLCV data
    candle_data = []
    for i, p in enumerate(prices):
        high = p * (1 + abs(np.random.randn() * 0.005))
        low = p * (1 - abs(np.random.randn() * 0.005))
        close = p + np.random.randn() * (high - low) * 0.3
        open_price = prices[i-1] if i > 0 else p
        
        candle_data.append({
            "timestamp": (datetime.now() - timedelta(days=n_candles-i)).strftime("%Y-%m-%d"),
            "open": open_price,
            "high": max(high, open_price, close),
            "low": min(low, open_price, close),
            "close": close,
            "volume": int(np.random.randint(1000000, 5000000))
        })
    
    # Create candlestick chart
    df = pd.DataFrame(candle_data)
    
    # Calculate indicators
    closes = df["close"].tolist()
    
    fig_candles = make_subplots(
        rows=2 if show_rsi else 1, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3] if show_rsi else [1]
    )
    
    # Candlestick
    fig_candles.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color="#00C853",
            decreasing_line_color="#FF1744"
        ),
        row=1, col=1
    )
    
    # SMA 20
    if show_sma20:
        sma20 = calculate_sma(closes, 20)
        fig_candles.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=sma20,
                name="SMA 20",
                line=dict(color="#FFD700", width=1.5)
            ),
            row=1, col=1
        )
    
    # SMA 50
    if show_sma50:
        sma50 = calculate_sma(closes, 50)
        fig_candles.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=sma50,
                name="SMA 50",
                line=dict(color="#00BCD4", width=1.5)
            ),
            row=1, col=1
        )
    
    # Bollinger Bands
    if show_bb:
        upper, middle, lower = calculate_bollinger_bands(closes, 20, 2.0)
        fig_candles.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=upper,
                name="BB Upper",
                line=dict(color="rgba(156, 39, 176, 0.5)", width=1),
                showlegend=False
            ),
            row=1, col=1
        )
        fig_candles.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=lower,
                name="BB Lower",
                line=dict(color="rgba(156, 39, 176, 0.5)", width=1),
                fill="tonexty",
                fillcolor="rgba(156, 39, 176, 0.1)",
                showlegend=False
            ),
            row=1, col=1
        )
    
    # RSI
    if show_rsi:
        rsi = calculate_rsi(closes, 14)
        fig_candles.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=rsi,
                name="RSI",
                line=dict(color="#FF9800", width=1.5)
            ),
            row=2, col=1
        )
        # Overbought/Oversold lines
        fig_candles.add_hline(y=70, line_dash="dash", line_color="red", 
                              opacity=0.5, row=2, col=1)
        fig_candles.add_hline(y=30, line_dash="dash", line_color="green", 
                              opacity=0.5, row=2, col=1)
    
    # Current price line
    fig_candles.add_hline(
        y=current_price,
        line_dash="dash",
        line_color="#2196F3",
        annotation_text=f"${current_price:.2f}",
        annotation_position="right",
        row=1, col=1
    )
    
    fig_candles.update_layout(
        height=400,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,1)",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0.5)"
        ),
        margin=dict(l=50, r=20, t=30, b=30)
    )
    
    fig_candles.update_xaxes(gridcolor="rgba(255,255,255,0.1)")
    fig_candles.update_yaxes(gridcolor="rgba(255,255,255,0.1)")
    
    st.plotly_chart(fig_candles, use_container_width=True)

# =============================================================================
# Right Column - Supergraph
# =============================================================================

with right_col:
    st.markdown("### 📈 The Supergraph")
    
    fig = go.Figure()
    
    # Zero line
    fig.add_hline(y=0, line_dash="solid", line_color="rgba(255,255,255,0.3)", line_width=1)
    
    # Current price line
    fig.add_vline(
        x=current_price,
        line_dash="dash",
        line_color="rgba(255,255,255,0.5)",
        line_width=1,
        annotation_text=f"${current_price:.2f}",
        annotation_position="top"
    )
    
    # Ghost curve (if locked)
    if ghost_payoff is not None:
        fig.add_trace(go.Scatter(
            x=price_range,
            y=ghost_payoff,
            mode="lines",
            name="Locked Curve (Ghost)",
            line=dict(color="rgba(156, 39, 176, 0.5)", width=2, dash="dot"),
            hovertemplate="<b>Ghost:</b> $%{y:.2f}<extra></extra>"
        ))
    
    # Expiration Profile
    fig.add_trace(go.Scatter(
        x=price_range,
        y=expiration_payoff,
        mode="lines",
        name="At Expiration",
        line=dict(color="#FFD700", width=3, shape="linear"),
        hovertemplate="<b>Price:</b> $%{x:.2f}<br><b>P/L at Expiry:</b> $%{y:.2f}<extra></extra>"
    ))
    
    # Theoretical Curve
    curve_name = f"T+{days_forward}" if days_forward > 0 else "Current (T+0)"
    fig.add_trace(go.Scatter(
        x=price_range,
        y=theoretical_payoff,
        mode="lines",
        name=curve_name,
        line=dict(color="#00BCD4", width=3, dash="dash"),
        hovertemplate="<b>Price:</b> $%{x:.2f}<br><b>Theoretical:</b> $%{y:.2f}<extra></extra>"
    ))
    
    # Time value fill
    fig.add_trace(go.Scatter(
        x=np.concatenate([price_range, price_range[::-1]]),
        y=np.concatenate([theoretical_payoff, expiration_payoff[::-1]]),
        fill="toself",
        fillcolor="rgba(156, 39, 176, 0.15)",
        line=dict(width=0),
        name="Time Value",
        hoverinfo="skip"
    ))
    
    # Breakeven markers
    for be in breakevens:
        fig.add_trace(go.Scatter(
            x=[be],
            y=[0],
            mode="markers+text",
            marker=dict(size=10, color="#FF9800", symbol="diamond"),
            text=[f"${be:.2f}"],
            textposition="top center",
            textfont=dict(color="#FF9800", size=10),
            name=f"BE ${be:.2f}",
            showlegend=False
        ))
    
    # Layout
    fig.update_layout(
        height=400,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,1)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0.5)"
        ),
        xaxis=dict(
            title="Stock Price ($)",
            gridcolor="rgba(255,255,255,0.1)",
            tickformat="$.2f"
        ),
        yaxis=dict(
            title="Profit / Loss ($)",
            gridcolor="rgba(255,255,255,0.1)",
            tickformat="$,.0f",
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.3)"
        ),
        margin=dict(l=50, r=20, t=30, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# Metrics Row
# =============================================================================

st.markdown("### 💰 Position Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    profit_str = f"${max_profit:,.2f}" if max_profit < 1e6 else "Unlimited"
    st.markdown(f"""
    <div class="metric-card profit">
        <div class="metric-label">Max Profit</div>
        <div class="metric-value green">{profit_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    loss_str = f"${max_loss:,.2f}" if max_loss > -1e6 else "Unlimited"
    st.markdown(f"""
    <div class="metric-card loss">
        <div class="metric-label">Max Loss</div>
        <div class="metric-value red">{loss_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    be_str = " / ".join([f"${be:.2f}" for be in breakevens[:2]]) if breakevens else "N/A"
    st.markdown(f"""
    <div class="metric-card info">
        <div class="metric-label">Breakeven(s)</div>
        <div class="metric-value blue">{be_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #9C27B0;">
        <div class="metric-label">Prob. of Profit</div>
        <div class="metric-value purple">{pop:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    net_delta = position_greeks.get("delta", 0)
    delta_color = "green" if net_delta > 0 else "red" if net_delta < 0 else "blue"
    st.markdown(f"""
    <div class="metric-card warning">
        <div class="metric-label">Net Delta</div>
        <div class="metric-value orange">{net_delta:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# Greeks & Account Row
# =============================================================================

st.markdown("### 📐 Position Greeks & Account")

greek_col1, greek_col2, greek_col3, greek_col4, account_col = st.columns([1, 1, 1, 1, 2])

with greek_col1:
    st.metric("Delta (Δ)", f"{position_greeks.get('delta', 0):.2f}")

with greek_col2:
    st.metric("Gamma (Γ)", f"{position_greeks.get('gamma', 0):.4f}")

with greek_col3:
    theta = position_greeks.get('theta', 0)
    st.metric("Theta (Θ)", f"${theta:.2f}/day")

with greek_col4:
    st.metric("Vega (ν)", f"${position_greeks.get('vega', 0):.2f}")

with account_col:
    if st.session_state.paper_mode:
        summary = paper_account.get_summary()
        st.markdown(f"""
        **📝 Paper Account**
        - Balance: **${summary['balance']:,.2f}**
        - P/L: {'🟢' if summary['total_pnl'] >= 0 else '🔴'} ${summary['total_pnl']:,.2f} ({summary['pnl_percent']:.1f}%)
        - Open Positions: {summary['open_positions']}
        """)
        
        # Execute strategy button
        if st.button("📥 Execute Strategy (Paper)", type="primary"):
            prices = {str(i): leg.premium for i, leg in enumerate(legs)}
            strategy = Strategy(
                name=strategy_name,
                ticker=ticker,
                legs=[OptionLeg(
                    option_type=leg.option_type,
                    position=leg.position,
                    strike=leg.strike,
                    premium=leg.premium,
                    quantity=leg.quantity,
                    expiration_days=leg.expiration_days,
                    iv=leg.iv
                ) for leg in legs]
            )
            if paper_account.execute_strategy(strategy, prices):
                st.success("✅ Strategy executed in paper account!")
                st.rerun()
            else:
                st.error("❌ Insufficient funds")
    else:
        st.warning("🔴 LIVE MODE - Connected to real broker")

# =============================================================================
# Strategy Legs
# =============================================================================

if legs:
    st.markdown("### 📋 Strategy Legs")
    
    legs_data = []
    for i, leg in enumerate(legs):
        if leg.option_type == "stock":
            leg_desc = f"{'Long' if leg.sign > 0 else 'Short'} {leg.quantity} shares"
            strike_str = f"@ ${leg.strike:.2f}"
            premium_str = "-"
        else:
            direction = "LONG" if leg.sign > 0 else "SHORT"
            leg_desc = f"{direction} {leg.quantity} {leg.option_type.upper()}"
            strike_str = f"${leg.strike:.2f}"
            premium_str = f"${leg.premium:.2f}"
        
        legs_data.append({
            "Leg": i + 1,
            "Position": leg_desc,
            "Strike": strike_str,
            "Premium": premium_str,
            "IV": f"{leg.iv * 100:.1f}%" if leg.iv > 0 else "-"
        })
    
    legs_df = pd.DataFrame(legs_data)
    st.dataframe(legs_df, hide_index=True, use_container_width=True)

# =============================================================================
# Educational Section
# =============================================================================

with st.expander("📚 Understanding the Dashboard", expanded=False):
    st.markdown("""
    ### Split-Panel Layout
    - **Left Panel**: Candlestick chart with technical indicators (SMA, Bollinger Bands, RSI)
    - **Right Panel**: Options payoff diagram (The Supergraph)
    
    ### Ghost Curve Feature
    Click **🔒 Lock Live Curve** to freeze the current theoretical curve in purple.
    Then adjust IV or time sliders to see how the strategy changes compared to the locked baseline.
    
    ### Paper Trading
    Test your strategies with $100,000 virtual capital. Click "Execute Strategy" to simulate trades.
    
    ### Net Delta
    The **Net Delta** metric shows your total directional exposure. Delta-neutral strategies target 0.
    """)

# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
mode_text = "Paper Trading" if st.session_state.paper_mode else "Live Trading"
st.markdown(
    f"<p style='text-align: center; color: rgba(255,255,255,0.4);'>"
    f"Options Supergraph Pro • {mode_text} • Black-Scholes Engine"
    f"</p>",
    unsafe_allow_html=True
)
