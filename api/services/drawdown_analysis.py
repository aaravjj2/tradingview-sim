"""
Monte Carlo Drawdown Analysis
Probability of ruin and drawdown analysis through simulation
"""

from typing import Dict, List, Tuple
import math
import random
from datetime import datetime


class DrawdownAnalyzer:
    """
    Monte Carlo Drawdown Analysis
    
    Simulates portfolio paths to calculate:
    - Maximum drawdown distribution
    - Probability of ruin (hitting stop-loss)
    - Time underwater analysis
    - Drawdown duration statistics
    """
    
    def __init__(
        self,
        starting_capital: float = 100000,
        annual_return: float = 0.15,
        annual_volatility: float = 0.20,
        trading_days_per_year: int = 252
    ):
        self.starting_capital = starting_capital
        self.annual_return = annual_return
        self.annual_volatility = annual_volatility
        self.trading_days = trading_days_per_year
        
        # Daily parameters
        self.daily_return = annual_return / trading_days_per_year
        self.daily_vol = annual_volatility / math.sqrt(trading_days_per_year)
    
    def simulate_path(self, days: int) -> Dict:
        """Simulate a single portfolio path with drawdown tracking"""
        equity = self.starting_capital
        peak = equity
        
        equity_curve = [equity]
        drawdown_curve = [0]
        
        max_drawdown = 0
        max_dd_start = 0
        max_dd_end = 0
        current_dd_start = 0
        
        for day in range(days):
            # Daily return
            daily_r = random.gauss(self.daily_return, self.daily_vol)
            equity *= (1 + daily_r)
            equity_curve.append(equity)
            
            # Track peak and drawdown
            if equity > peak:
                peak = equity
                current_dd_start = day
            
            current_drawdown = (peak - equity) / peak
            drawdown_curve.append(current_drawdown)
            
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
                max_dd_start = current_dd_start
                max_dd_end = day
        
        return {
            "final_equity": equity,
            "total_return_pct": (equity / self.starting_capital - 1) * 100,
            "max_drawdown_pct": max_drawdown * 100,
            "max_drawdown_start_day": max_dd_start,
            "max_drawdown_end_day": max_dd_end,
            "max_drawdown_duration": max_dd_end - max_dd_start,
            "equity_curve": equity_curve,
            "drawdown_curve": drawdown_curve
        }
    
    def run_analysis(
        self,
        days: int = 252,
        num_simulations: int = 10000,
        ruin_threshold: float = 0.20  # 20% drawdown = "ruin"
    ) -> Dict:
        """Run full Monte Carlo drawdown analysis"""
        
        max_drawdowns = []
        final_equities = []
        drawdown_durations = []
        ruin_count = 0
        
        sample_paths = []
        
        for i in range(num_simulations):
            result = self.simulate_path(days)
            
            max_dd = result["max_drawdown_pct"]
            max_drawdowns.append(max_dd)
            final_equities.append(result["final_equity"])
            drawdown_durations.append(result["max_drawdown_duration"])
            
            if max_dd >= ruin_threshold * 100:
                ruin_count += 1
            
            # Store first 10 paths for visualization
            if i < 10:
                sample_paths.append({
                    "equity_curve": result["equity_curve"],
                    "drawdown_curve": result["drawdown_curve"]
                })
        
        # Sort for percentile calculations
        max_drawdowns_sorted = sorted(max_drawdowns)
        final_equities_sorted = sorted(final_equities)
        
        def percentile(data, p):
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]
        
        # Drawdown distribution
        dd_distribution = {
            "min": round(min(max_drawdowns), 2),
            "percentile_5": round(percentile(max_drawdowns_sorted, 5), 2),
            "percentile_25": round(percentile(max_drawdowns_sorted, 25), 2),
            "median": round(percentile(max_drawdowns_sorted, 50), 2),
            "percentile_75": round(percentile(max_drawdowns_sorted, 75), 2),
            "percentile_95": round(percentile(max_drawdowns_sorted, 95), 2),
            "percentile_99": round(percentile(max_drawdowns_sorted, 99), 2),
            "max": round(max(max_drawdowns), 2)
        }
        
        # Final equity distribution
        equity_distribution = {
            "min": round(min(final_equities), 2),
            "percentile_5": round(percentile(final_equities_sorted, 5), 2),
            "percentile_25": round(percentile(final_equities_sorted, 25), 2),
            "median": round(percentile(final_equities_sorted, 50), 2),
            "mean": round(sum(final_equities) / len(final_equities), 2),
            "percentile_75": round(percentile(final_equities_sorted, 75), 2),
            "percentile_95": round(percentile(final_equities_sorted, 95), 2),
            "max": round(max(final_equities), 2)
        }
        
        # Probability of various drawdown levels
        dd_probabilities = {}
        for level in [5, 10, 15, 20, 25, 30, 40, 50]:
            count = len([dd for dd in max_drawdowns if dd >= level])
            dd_probabilities[f"{level}%"] = round(count / num_simulations * 100, 2)
        
        return {
            "simulation_params": {
                "starting_capital": self.starting_capital,
                "annual_return": self.annual_return,
                "annual_volatility": self.annual_volatility,
                "days_simulated": days,
                "num_simulations": num_simulations,
                "ruin_threshold": ruin_threshold
            },
            "drawdown_distribution": dd_distribution,
            "equity_distribution": equity_distribution,
            "probability_of_ruin": round(ruin_count / num_simulations * 100, 2),
            "drawdown_probabilities": dd_probabilities,
            "avg_max_drawdown_duration": round(sum(drawdown_durations) / len(drawdown_durations), 1),
            "sample_paths": sample_paths,
            "timestamp": datetime.now().isoformat()
        }
    
    def calculate_safe_position_size(
        self,
        max_acceptable_drawdown: float = 0.10,  # 10% max drawdown
        confidence: float = 0.95  # 95% confidence
    ) -> Dict:
        """Calculate position size to limit drawdown at given confidence"""
        
        # Run simulations with different position sizes
        position_sizes = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        results = []
        
        original_vol = self.annual_volatility
        
        for size in position_sizes:
            # Adjust volatility by position size
            self.annual_volatility = original_vol * size
            self.daily_vol = self.annual_volatility / math.sqrt(self.trading_days)
            
            analysis = self.run_analysis(days=252, num_simulations=1000)
            
            # Get drawdown at confidence level
            percentile_key = f"percentile_{int(confidence * 100)}"
            dd_at_confidence = analysis["drawdown_distribution"].get(
                percentile_key, 
                analysis["drawdown_distribution"]["percentile_95"]
            )
            
            results.append({
                "position_size": size,
                "expected_drawdown_pct": dd_at_confidence,
                "acceptable": dd_at_confidence <= max_acceptable_drawdown * 100
            })
        
        # Restore original volatility
        self.annual_volatility = original_vol
        self.daily_vol = original_vol / math.sqrt(self.trading_days)
        
        # Find largest acceptable position size
        acceptable = [r for r in results if r["acceptable"]]
        recommended_size = max([r["position_size"] for r in acceptable]) if acceptable else 0.5
        
        return {
            "max_acceptable_drawdown": max_acceptable_drawdown * 100,
            "confidence_level": confidence,
            "recommended_position_size": recommended_size,
            "analysis": results
        }


async def run_drawdown_analysis(
    starting_capital: float = 100000,
    annual_return: float = 0.15,
    annual_volatility: float = 0.20,
    days: int = 252,
    num_simulations: int = 10000,
    ruin_threshold: float = 0.20
) -> Dict:
    """API helper for drawdown analysis"""
    analyzer = DrawdownAnalyzer(
        starting_capital=starting_capital,
        annual_return=annual_return,
        annual_volatility=annual_volatility
    )
    
    return analyzer.run_analysis(days, num_simulations, ruin_threshold)


async def calculate_position_size(
    annual_volatility: float = 0.20,
    max_drawdown: float = 0.10,
    confidence: float = 0.95
) -> Dict:
    """Calculate safe position size"""
    analyzer = DrawdownAnalyzer(annual_volatility=annual_volatility)
    return analyzer.calculate_safe_position_size(max_drawdown, confidence)
