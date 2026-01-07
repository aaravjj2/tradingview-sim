# Supergraph Pro: Institutional Trading Workstation

A professional-grade algorithmic trading platform specifically designed for options analytics, automated execution, and risk management. 

![Grand Tour](/home/aarav/.gemini/antigravity/brain/5d81f7df-1c76-4b96-ad9e-64fa2068057e/final_grand_tour_state_1767806429543.png)

## 🚀 Key Features

### 📊 Market Intelligence
- **Whale Tracker**: Real-time detection of unusual block trades and institution flows.
- **Uncertainty Cone**: Hybrid forecasting model (GARCH + Monte Carlo) for 30/60/90-day price projections.
- **Micro-Structure Analysis**: Gamma Exposure (GEX) profiles to identify dealer hedging walls.

### 🧪 Strategy Lab
- **NLP Strategy Builder**: Type naturally (e.g., "Buy a straddle on SPY") to construct complex multi-leg positions.
- **Lego Builder**: Visual drag-and-drop interface for structuring option strategies.
- **AI Recommender**: Sentiment-driven and statistically optimized trade suggestions.

### ⚡ Algorithmic Execution
- **Theta Eater Bot**: Automated Iron Condor strategy for 0DTE income generation.
- **Vega Arbitrage**: Scans for calendar spread opportunities based on term structure dislocation.
- **Smart Legging**: RSI-based entry timing for individual legs of complex strategies.

### 🛡️ Risk & Simulation
- **Margin Simulator**: Compare capital efficiency of Reg-T vs. Portfolio Margin.
- **Panic Test**: Stress test your portfolio against historical crash scenarios (e.g., Black Monday, 2020 Covid Crash).

## 🛠️ Tech Stack
- **Frontend**: React 18, TypeScript, TailwindCSS, Lightweight Charts
- **Backend**: FastAPI, Python 3.10+, Alpaca Markets API
- **Data**: Real-time WebSocket feeds (Polygon/Alpaca), FRED Macro Data

## 🚦 Quick Start

### 1. Backend Setup
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Environment Config
Create a `keys.env` file in the root with your Alpaca credentials:
```env
APCA_API_KEY_ID=PK...
APCA_API_SECRET_KEY=...
APCA_ENDPOINT=https://paper-api.alpaca.markets
```

## 📜 System Status
- **Core Systems**: ✅ Online
- **Trading Bots**: ✅ 9 Strategies Active
- **Analytics Engine**: ✅ Integrated

---
*Built for the 2025 Algorithmic Trading Challenge*
