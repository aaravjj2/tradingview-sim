"""
Walk-Forward Analysis
Rolling window train/test backtesting for robust strategy validation
"""

import math
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import random


class WalkForwardAnalyzer:
    """
    Walk-Forward Optimization (WFO) Backtester
    
    Instead of in-sample optimization followed by out-of-sample testing once,
    WFO performs multiple in-sample/out-of-sample cycles:
    
    1. Optimize parameters on period 1
    2. Test on period 2
    3. Optimize on periods 1+2
    4. Test on period 3
    ...and so on
    
    This provides more realistic performance estimates and validates
    that strategy parameters are stable over time.
    """
    
    def __init__(
        self,
        strategy_func: Optional[Callable] = None,
        train_window: int = 252,  # Trading days for optimization
        test_window: int = 63,    # Trading days for testing (~3 months)
        step_size: int = 63,      # Roll forward by this many days
        min_periods: int = 4      # Minimum number of walk-forward periods
    ):
        self.strategy_func = strategy_func
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size
        self.min_periods = min_periods
        
        self.results: List[Dict] = []
        self.aggregate_metrics: Dict = {}
    
    def generate_sample_data(self, num_days: int, start_price: float = 100.0) -> List[Dict]:
        """Generate sample price data for testing"""
        data = []
        price = start_price
        
        for i in range(num_days):
            # Random walk with slight upward drift
            daily_return = random.gauss(0.0003, 0.015)  # ~0.03% drift, 1.5% daily vol
            price *= (1 + daily_return)
            
            data.append({
                "day": i,
                "date": (datetime.now() - timedelta(days=num_days - i)).strftime("%Y-%m-%d"),
                "open": price * (1 + random.uniform(-0.005, 0.005)),
                "high": price * (1 + random.uniform(0, 0.02)),
                "low": price * (1 - random.uniform(0, 0.02)),
                "close": price,
                "volume": random.randint(1000000, 5000000)
            })
        
        return data
    
    def split_periods(self, data: List[Dict]) -> List[Dict]:
        """
        Split data into walk-forward periods
        
        Returns list of {train_start, train_end, test_start, test_end, train_data, test_data}
        """
        total_days = len(data)
        periods = []
        
        start = 0
        period_num = 1
        
        while start + self.train_window + self.test_window <= total_days:
            train_start = start
            train_end = start + self.train_window
            test_start = train_end
            test_end = min(train_end + self.test_window, total_days)
            
            periods.append({
                "period": period_num,
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "train_days": train_end - train_start,
                "test_days": test_end - test_start,
                "train_data": data[train_start:train_end],
                "test_data": data[test_start:test_end]
            })
            
            start += self.step_size
            period_num += 1
        
        return periods
    
    def run_simple_strategy(
        self,
        data: List[Dict],
        params: Dict
    ) -> Dict:
        """
        Run a simple momentum strategy on the data
        
        Params:
        - lookback: Number of days to look back for signal
        - threshold: Minimum return to trigger signal
        """
        lookback = params.get("lookback", 20)
        threshold = params.get("threshold", 0.02)
        
        trades = []
        position = 0  # 0 = flat, 1 = long, -1 = short
        entry_price = 0
        pnl = 0
        
        for i in range(lookback, len(data)):
            current_price = data[i]["close"]
            past_price = data[i - lookback]["close"]
            momentum = (current_price / past_price) - 1
            
            # Signal generation
            if momentum > threshold and position <= 0:
                # Buy signal
                if position == -1:  # Close short first
                    pnl += entry_price - current_price
                    trades.append({"type": "close_short", "price": current_price, "pnl": entry_price - current_price})
                
                position = 1
                entry_price = current_price
                trades.append({"type": "long", "price": current_price, "day": i})
                
            elif momentum < -threshold and position >= 0:
                # Sell signal
                if position == 1:  # Close long first
                    pnl += current_price - entry_price
                    trades.append({"type": "close_long", "price": current_price, "pnl": current_price - entry_price})
                
                position = -1
                entry_price = current_price
                trades.append({"type": "short", "price": current_price, "day": i})
        
        # Close final position
        if position != 0 and len(data) > 0:
            final_price = data[-1]["close"]
            if position == 1:
                pnl += final_price - entry_price
            else:
                pnl += entry_price - final_price
        
        # Calculate metrics
        num_trades = len([t for t in trades if t["type"] in ["long", "short"]])
        winning_trades = len([t for t in trades if t.get("pnl", 0) > 0])
        win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
        
        start_price = data[0]["close"] if data else 100
        total_return = pnl / start_price * 100
        
        return {
            "params": params,
            "pnl": round(pnl, 4),
            "total_return_pct": round(total_return, 2),
            "num_trades": num_trades,
            "win_rate": round(win_rate, 1),
            "trades": trades[-5:]  # Last 5 trades only
        }
    
    def optimize_params(self, train_data: List[Dict]) -> Dict:
        """
        Find optimal parameters for the strategy on training data
        
        Simple grid search over lookback and threshold
        """
        best_params = {"lookback": 20, "threshold": 0.02}
        best_pnl = float("-inf")
        
        for lookback in [10, 15, 20, 30, 40]:
            for threshold in [0.01, 0.02, 0.03, 0.05]:
                params = {"lookback": lookback, "threshold": threshold}
                result = self.run_simple_strategy(train_data, params)
                
                if result["pnl"] > best_pnl:
                    best_pnl = result["pnl"]
                    best_params = params
        
        return best_params
    
    def run_walk_forward(self, data: List[Dict]) -> Dict:
        """
        Execute full walk-forward analysis
        """
        periods = self.split_periods(data)
        
        if len(periods) < self.min_periods:
            return {
                "error": f"Insufficient data for {self.min_periods} walk-forward periods",
                "periods_available": len(periods)
            }
        
        self.results = []
        all_oos_returns = []
        
        for period in periods:
            # Optimize on training data
            optimal_params = self.optimize_params(period["train_data"])
            
            # Test on out-of-sample data
            train_result = self.run_simple_strategy(period["train_data"], optimal_params)
            test_result = self.run_simple_strategy(period["test_data"], optimal_params)
            
            period_result = {
                "period": period["period"],
                "train_days": period["train_days"],
                "test_days": period["test_days"],
                "optimal_params": optimal_params,
                "train_performance": {
                    "return_pct": train_result["total_return_pct"],
                    "win_rate": train_result["win_rate"],
                    "num_trades": train_result["num_trades"]
                },
                "test_performance": {
                    "return_pct": test_result["total_return_pct"],
                    "win_rate": test_result["win_rate"],
                    "num_trades": test_result["num_trades"]
                },
                "degradation": round(
                    train_result["total_return_pct"] - test_result["total_return_pct"], 2
                )
            }
            
            self.results.append(period_result)
            all_oos_returns.append(test_result["total_return_pct"])
        
        # Calculate aggregate metrics
        avg_oos_return = sum(all_oos_returns) / len(all_oos_returns) if all_oos_returns else 0
        positive_periods = len([r for r in all_oos_returns if r > 0])
        consistency_ratio = positive_periods / len(all_oos_returns) if all_oos_returns else 0
        
        # Calculate return variance
        if len(all_oos_returns) > 1:
            mean_return = avg_oos_return
            variance = sum((r - mean_return) ** 2 for r in all_oos_returns) / len(all_oos_returns)
            std_return = math.sqrt(variance)
            sharpe = avg_oos_return / std_return if std_return > 0 else 0
        else:
            std_return = 0
            sharpe = 0
        
        self.aggregate_metrics = {
            "num_periods": len(self.results),
            "avg_oos_return_pct": round(avg_oos_return, 2),
            "std_oos_return_pct": round(std_return, 2),
            "positive_periods": positive_periods,
            "consistency_ratio": round(consistency_ratio, 2),
            "sharpe_ratio": round(sharpe, 2),
            "total_oos_return_pct": round(sum(all_oos_returns), 2),
            "worst_period_return": round(min(all_oos_returns), 2) if all_oos_returns else 0,
            "best_period_return": round(max(all_oos_returns), 2) if all_oos_returns else 0
        }
        
        return {
            "status": "complete",
            "aggregate_metrics": self.aggregate_metrics,
            "period_results": self.results
        }


async def run_walk_forward_analysis(
    num_days: int = 756,  # 3 years
    train_window: int = 252,
    test_window: int = 63
) -> Dict:
    """API endpoint helper for walk-forward analysis"""
    analyzer = WalkForwardAnalyzer(
        train_window=train_window,
        test_window=test_window
    )
    
    data = analyzer.generate_sample_data(num_days)
    result = analyzer.run_walk_forward(data)
    
    return result
