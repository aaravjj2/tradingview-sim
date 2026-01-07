"""
Monte Carlo Simulation Service
Price path simulations for probability calculations
"""

import math
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation"""
    paths: List[List[float]]  # List of price paths
    final_prices: List[float]  # Terminal prices
    pop: float  # Probability of Profit
    expected_return: float  # Average return
    max_profit: float
    max_loss: float
    percentiles: Dict[str, float]


def simulate_gbm_paths(
    spot: float,
    drift: float,  # Expected return (risk-free rate)
    volatility: float,  # Annualized volatility
    days: int,
    num_paths: int = 1000,
    seed: int = None
) -> List[List[float]]:
    """
    Simulate price paths using Geometric Brownian Motion
    
    dS = μSdt + σSdW
    
    S(t) = S(0) * exp((μ - σ²/2)t + σW(t))
    """
    if seed is not None:
        random.seed(seed)
    
    dt = 1 / 252  # Daily step (252 trading days)
    paths = []
    
    for _ in range(num_paths):
        path = [spot]
        current = spot
        
        for _ in range(days):
            # Generate random shock
            dW = random.gauss(0, 1) * math.sqrt(dt)
            
            # GBM step
            daily_return = (drift - 0.5 * volatility ** 2) * dt + volatility * dW
            current = current * math.exp(daily_return)
            path.append(current)
        
        paths.append(path)
    
    return paths


def calculate_strategy_payoff(
    final_price: float,
    legs: List[Dict]
) -> float:
    """
    Calculate strategy P/L at expiration for a given final price
    
    Each leg has: option_type, position (long/short), strike, premium, quantity
    """
    payoff = 0
    
    for leg in legs:
        opt_type = leg.get("option_type", "call")
        position = leg.get("position", "long")
        strike = leg.get("strike", 0)
        premium = leg.get("premium", 0)
        qty = leg.get("quantity", 1)
        
        sign = 1 if position == "long" else -1
        
        if opt_type == "call":
            intrinsic = max(0, final_price - strike)
            payoff += sign * qty * 100 * (intrinsic - premium)
        elif opt_type == "put":
            intrinsic = max(0, strike - final_price)
            payoff += sign * qty * 100 * (intrinsic - premium)
        elif opt_type == "stock":
            payoff += sign * qty * (final_price - strike)
    
    return payoff


def monte_carlo_pop(
    spot: float,
    volatility: float,
    days: int,
    legs: List[Dict],
    risk_free_rate: float = 0.05,
    num_simulations: int = 1000
) -> SimulationResult:
    """
    Run Monte Carlo simulation to calculate Probability of Profit
    
    Returns detailed simulation results
    """
    # Simulate price paths
    paths = simulate_gbm_paths(
        spot=spot,
        drift=risk_free_rate,
        volatility=volatility,
        days=days,
        num_paths=num_simulations
    )
    
    # Get final prices
    final_prices = [path[-1] for path in paths]
    
    # Calculate P/L for each path
    pnls = [calculate_strategy_payoff(fp, legs) for fp in final_prices]
    
    # Statistics
    profitable_count = sum(1 for pnl in pnls if pnl > 0)
    pop = profitable_count / num_simulations
    
    expected_return = sum(pnls) / num_simulations
    max_profit = max(pnls)
    max_loss = min(pnls)
    
    # Percentiles
    sorted_pnls = sorted(pnls)
    percentiles = {
        "5th": sorted_pnls[int(0.05 * len(sorted_pnls))],
        "25th": sorted_pnls[int(0.25 * len(sorted_pnls))],
        "50th": sorted_pnls[int(0.50 * len(sorted_pnls))],
        "75th": sorted_pnls[int(0.75 * len(sorted_pnls))],
        "95th": sorted_pnls[int(0.95 * len(sorted_pnls))]
    }
    
    # Only return sampled paths for visualization (max 100)
    sampled_paths = paths[:min(100, len(paths))]
    
    return SimulationResult(
        paths=sampled_paths,
        final_prices=final_prices,
        pop=round(pop * 100, 2),  # As percentage
        expected_return=round(expected_return, 2),
        max_profit=round(max_profit, 2),
        max_loss=round(max_loss, 2),
        percentiles=percentiles
    )


def price_distribution(final_prices: List[float], bins: int = 50) -> Dict:
    """
    Create histogram of final price distribution
    """
    min_price = min(final_prices)
    max_price = max(final_prices)
    bin_width = (max_price - min_price) / bins
    
    histogram = []
    for i in range(bins):
        bin_start = min_price + i * bin_width
        bin_end = bin_start + bin_width
        count = sum(1 for p in final_prices if bin_start <= p < bin_end)
        histogram.append({
            "bin_start": round(bin_start, 2),
            "bin_end": round(bin_end, 2),
            "count": count,
            "frequency": round(count / len(final_prices), 4)
        })
    
    return {
        "histogram": histogram,
        "mean": round(sum(final_prices) / len(final_prices), 2),
        "std": round(
            math.sqrt(sum((p - sum(final_prices)/len(final_prices))**2 
                         for p in final_prices) / len(final_prices)),
            2
        )
    }
