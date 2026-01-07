"""
Historical Stress Testing Module
Replay portfolio through historical crisis events
"""

from typing import Dict, List
from datetime import datetime
import math


# Historical crisis event data (simplified daily returns)
HISTORICAL_EVENTS = {
    "2008_financial_crisis": {
        "name": "2008 Financial Crisis",
        "description": "Lehman Brothers collapse and global financial meltdown",
        "start_date": "2008-09-15",
        "duration_days": 30,
        "peak_drawdown_pct": -46.0,
        "vix_spike": 80.0,
        "spy_returns": [-4.7, -1.2, 2.1, -3.8, -5.8, 4.3, -3.2, 1.8, -7.6, -4.9,
                        2.2, -0.9, -3.5, 4.5, -8.2, 1.1, -0.5, -2.1, 3.8, -6.1,
                        4.8, -3.3, 2.6, -5.2, 1.2, -4.1, 2.9, -1.8, -3.2, 1.5]
    },
    "2020_covid_crash": {
        "name": "2020 COVID Crash",
        "description": "Pandemic-induced market collapse",
        "start_date": "2020-02-20",
        "duration_days": 23,
        "peak_drawdown_pct": -34.0,
        "vix_spike": 82.0,
        "spy_returns": [-3.4, -4.4, -0.8, -3.4, -1.7, -4.3, 4.6, -2.8, -7.6, 4.9,
                        -9.5, 4.9, -5.2, -12.0, 9.3, -5.2, -4.9, 6.0, -3.4, -4.3,
                        2.3, 0.5, -3.4]
    },
    "1987_black_monday": {
        "name": "1987 Black Monday",
        "description": "Single-day crash of 22.6%",
        "start_date": "1987-10-19",
        "duration_days": 5,
        "peak_drawdown_pct": -22.6,
        "vix_spike": 150.0,
        "spy_returns": [-22.6, 5.3, 1.4, -3.2, 2.1]
    },
    "2011_debt_ceiling": {
        "name": "2011 Debt Ceiling Crisis",
        "description": "US debt downgrade and European crisis",
        "start_date": "2011-08-01",
        "duration_days": 10,
        "peak_drawdown_pct": -17.0,
        "vix_spike": 48.0,
        "spy_returns": [-2.6, -4.8, -4.5, 0.5, -6.7, 4.7, -4.4, 4.6, 2.2, -2.1]
    },
    "2018_volmageddon": {
        "name": "2018 Volmageddon",
        "description": "VIX spike that blew up short volatility products",
        "start_date": "2018-02-05",
        "duration_days": 5,
        "peak_drawdown_pct": -10.2,
        "vix_spike": 50.0,
        "spy_returns": [-4.1, -4.1, 1.7, -3.8, 1.5]
    },
    "flash_crash_2010": {
        "name": "2010 Flash Crash",
        "description": "Algorithmic trading caused intraday crash",
        "start_date": "2010-05-06",
        "duration_days": 1,
        "peak_drawdown_pct": -9.0,  # Intraday, recovered
        "vix_spike": 40.0,
        "spy_returns": [-3.2]  # Daily close
    }
}


def calculate_option_pnl(
    position: Dict,
    price_change_pct: float,
    vix_change: float
) -> Dict:
    """
    Estimate option position P&L during stress event
    
    Uses simplified delta/vega approximation
    """
    delta = position.get("delta", 0)
    gamma = position.get("gamma", 0)
    vega = position.get("vega", 0)
    theta = position.get("theta", 0)
    position_value = position.get("value", 0)
    
    # Price P&L
    price_pnl = delta * price_change_pct * position_value
    
    # Second order price P&L (gamma)
    gamma_pnl = 0.5 * gamma * (price_change_pct ** 2) * position_value * 100
    
    # Volatility P&L (assume VIX change maps to option IV change)
    iv_change = vix_change / 100  # Simplification
    vega_pnl = vega * iv_change * position_value
    
    # Time decay (1 day)
    theta_pnl = theta
    
    total_pnl = price_pnl + gamma_pnl + vega_pnl + theta_pnl
    
    return {
        "price_pnl": round(price_pnl, 2),
        "gamma_pnl": round(gamma_pnl, 2),
        "vega_pnl": round(vega_pnl, 2),
        "theta_pnl": round(theta_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "pnl_pct": round(total_pnl / position_value * 100 if position_value > 0 else 0, 2)
    }


def stress_test_portfolio(
    positions: List[Dict],
    event_key: str,
    starting_capital: float = 100000
) -> Dict:
    """
    Run a portfolio through a historical stress event
    
    Positions should have: value, delta, gamma, vega, theta
    """
    event = HISTORICAL_EVENTS.get(event_key)
    if not event:
        return {"error": f"Unknown event: {event_key}"}
    
    returns = event["spy_returns"]
    vix_spike = event["vix_spike"]
    
    # Calculate total position value
    total_position_value = sum(p.get("value", 0) for p in positions)
    
    # Calculate portfolio greeks
    portfolio_delta = sum(p.get("delta", 0) * p.get("value", 0) for p in positions)
    portfolio_gamma = sum(p.get("gamma", 0) * p.get("value", 0) for p in positions)
    portfolio_vega = sum(p.get("vega", 0) * p.get("value", 0) for p in positions)
    portfolio_theta = sum(p.get("theta", 0) for p in positions)
    
    # Simulate day by day
    daily_results = []
    cumulative_pnl = 0
    peak_value = starting_capital
    max_drawdown = 0
    current_value = starting_capital
    
    for i, daily_return in enumerate(returns):
        # Estimate intraday VIX spike (front-loaded)
        day_vix_change = vix_spike * (0.5 if i == 0 else 0.1)
        
        # Calculate portfolio P&L
        price_pnl = (portfolio_delta / total_position_value if total_position_value > 0 else 0) * daily_return / 100 * current_value
        vega_pnl = (portfolio_vega / total_position_value if total_position_value > 0 else 0) * day_vix_change / 100 * current_value
        theta_pnl = portfolio_theta
        
        day_pnl = price_pnl + vega_pnl + theta_pnl
        cumulative_pnl += day_pnl
        current_value = starting_capital + cumulative_pnl
        
        # Track drawdown
        if current_value > peak_value:
            peak_value = current_value
        drawdown = (peak_value - current_value) / peak_value * 100
        max_drawdown = max(max_drawdown, drawdown)
        
        daily_results.append({
            "day": i + 1,
            "spy_return_pct": daily_return,
            "price_pnl": round(price_pnl, 2),
            "vega_pnl": round(vega_pnl, 2),
            "theta_pnl": round(theta_pnl, 2),
            "day_pnl": round(day_pnl, 2),
            "cumulative_pnl": round(cumulative_pnl, 2),
            "portfolio_value": round(current_value, 2),
            "drawdown_pct": round(drawdown, 2)
        })
    
    return {
        "event": {
            "key": event_key,
            "name": event["name"],
            "description": event["description"],
            "start_date": event["start_date"],
            "duration_days": event["duration_days"],
            "spy_peak_drawdown": event["peak_drawdown_pct"],
            "vix_spike": event["vix_spike"]
        },
        "portfolio": {
            "starting_capital": starting_capital,
            "total_position_value": round(total_position_value, 2),
            "delta_exposure": round(portfolio_delta, 4),
            "gamma_exposure": round(portfolio_gamma, 4),
            "vega_exposure": round(portfolio_vega, 4),
            "theta_decay": round(portfolio_theta, 2)
        },
        "results": {
            "final_value": round(current_value, 2),
            "total_pnl": round(cumulative_pnl, 2),
            "total_return_pct": round(cumulative_pnl / starting_capital * 100, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "worst_day_pnl": round(min(r["day_pnl"] for r in daily_results), 2),
            "best_day_pnl": round(max(r["day_pnl"] for r in daily_results), 2)
        },
        "daily_breakdown": daily_results
    }


async def run_stress_test(
    event_key: str,
    delta: float = 0.5,
    gamma: float = 0.02,
    vega: float = 10.0,
    theta: float = -15.0,
    position_value: float = 10000,
    capital: float = 100000
) -> Dict:
    """API helper for running a stress test"""
    positions = [{
        "name": "Options Position",
        "value": position_value,
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta
    }]
    
    return stress_test_portfolio(positions, event_key, capital)


async def get_available_events() -> List[Dict]:
    """Get list of available stress test events"""
    events = []
    for key, event in HISTORICAL_EVENTS.items():
        events.append({
            "key": key,
            "name": event["name"],
            "description": event["description"],
            "date": event["start_date"],
            "duration": event["duration_days"],
            "severity": event["peak_drawdown_pct"]
        })
    return sorted(events, key=lambda x: x["severity"])
