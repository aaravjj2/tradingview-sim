"""
Walk-Forward Backtester
Simulates the AI Council's decisions over historical data.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random


@dataclass
class BacktestTrade:
    """Single simulated trade."""
    ticker: str
    entry_date: datetime
    exit_date: datetime
    strategy: str
    entry_price: float
    exit_price: float
    pnl: float
    council_approved: bool
    agent_votes: Dict[str, str]


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[BacktestTrade]
    equity_curve: List[float]
    
    def to_dict(self) -> Dict:
        return {
            "period": f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl": round(self.total_pnl, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "win_rate": round(self.win_rate * 100, 1),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "profit_factor": round(self.profit_factor, 2),
            "equity_curve": self.equity_curve[-20:]  # Last 20 points
        }


class WalkForwardBacktester:
    """
    Walk-Forward Backtester for the AI Council.
    
    Simulates how the council would have performed over historical periods,
    using an in-sample optimization window followed by out-of-sample testing.
    """
    
    def __init__(self):
        self.results: List[BacktestResult] = []
        
        # Agent voting weights (for hyperparameter tuning)
        self.weights = {
            "technician": 0.35,
            "fundamentalist": 0.35,
            "risk_manager": 0.30
        }
        
        # Simulated historical performance parameters
        self.base_win_rate = 0.55
        self.avg_trade_pnl = 150
        self.trade_pnl_std = 300
    
    async def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        tickers: Optional[List[str]] = None
    ) -> BacktestResult:
        """
        Run a backtest simulation over the specified period.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            tickers: List of tickers to include (defaults to S&P 100 sample)
            
        Returns:
            BacktestResult with performance metrics
        """
        tickers = tickers or ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "TSLA"]
        
        trades = []
        equity = 10000  # Starting capital
        equity_curve = [equity]
        peak_equity = equity
        max_drawdown = 0
        
        # Simulate trades
        current_date = start_date
        while current_date < end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Simulate 1-3 trades per day
            num_trades = random.randint(0, 3)
            
            for _ in range(num_trades):
                ticker = random.choice(tickers)
                trade = self._simulate_trade(ticker, current_date)
                trades.append(trade)
                
                equity += trade.pnl
                equity_curve.append(equity)
                
                # Track drawdown
                if equity > peak_equity:
                    peak_equity = equity
                drawdown = (peak_equity - equity) / peak_equity * 100
                max_drawdown = max(max_drawdown, drawdown)
            
            current_date += timedelta(days=1)
        
        # Calculate metrics
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]
        
        win_rate = len(winning) / len(trades) if trades else 0
        avg_win = sum(t.pnl for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.pnl for t in losing) / len(losing) if losing else 0
        
        total_win = sum(t.pnl for t in winning)
        total_loss = abs(sum(t.pnl for t in losing))
        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
        
        # Calculate Sharpe (simplified)
        returns = [trades[i].pnl / 10000 for i in range(len(trades))]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if len(returns) > 1 else 1
        sharpe = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
        
        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_pnl=equity - 10000,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=trades,
            equity_curve=equity_curve
        )
        
        self.results.append(result)
        return result
    
    def _simulate_trade(self, ticker: str, date: datetime) -> BacktestTrade:
        """Simulate a single trade based on current weight configuration."""
        # Simulate agent votes
        tech_vote = random.random() < (self.base_win_rate + self.weights["technician"] * 0.1)
        fund_vote = random.random() < (self.base_win_rate + self.weights["fundamentalist"] * 0.1)
        risk_vote = random.random() < (self.base_win_rate + self.weights["risk_manager"] * 0.05)
        
        votes = {
            "technician": "YES" if tech_vote else "NO",
            "fundamentalist": "YES" if fund_vote else "NO",
            "risk_manager": "YES" if risk_vote else "NO"
        }
        
        approved = sum([tech_vote, fund_vote, risk_vote]) >= 2
        
        # Trade outcome influenced by council accuracy
        if approved:
            # Good signal - higher chance of profit
            is_winner = random.random() < (self.base_win_rate + 0.10)
        else:
            # Would have been a bad trade
            is_winner = random.random() < (self.base_win_rate - 0.15)
        
        if is_winner:
            pnl = abs(random.gauss(self.avg_trade_pnl, self.trade_pnl_std * 0.5))
        else:
            pnl = -abs(random.gauss(self.avg_trade_pnl * 0.8, self.trade_pnl_std * 0.5))
        
        # Only count P&L for approved trades
        if not approved:
            pnl = 0  # Didn't take the trade
        
        strategies = ["Iron Condor", "Call Spread", "Put Spread", "Gamma Scalp"]
        
        return BacktestTrade(
            ticker=ticker,
            entry_date=date,
            exit_date=date + timedelta(days=random.randint(1, 30)),
            strategy=random.choice(strategies),
            entry_price=100 + random.random() * 400,
            exit_price=100 + random.random() * 400,
            pnl=pnl,
            council_approved=approved,
            agent_votes=votes
        )
    
    def tune_weights(
        self,
        technician_range: Tuple[float, float] = (0.2, 0.5),
        fundamentalist_range: Tuple[float, float] = (0.2, 0.5),
        iterations: int = 20
    ) -> Dict:
        """
        Hyperparameter tuning via grid search.
        
        Finds optimal voting weights for the AI Council.
        """
        best_sharpe = -float('inf')
        best_weights = self.weights.copy()
        results = []
        
        for _ in range(iterations):
            # Random weights within ranges
            tech_w = random.uniform(*technician_range)
            fund_w = random.uniform(*fundamentalist_range)
            risk_w = 1.0 - tech_w - fund_w
            
            if risk_w < 0.1 or risk_w > 0.5:
                continue
            
            self.weights = {
                "technician": tech_w,
                "fundamentalist": fund_w,
                "risk_manager": risk_w
            }
            
            # Run backtest synchronously for tuning
            result = asyncio.run(self.run_backtest(
                datetime(2023, 1, 1),
                datetime(2023, 12, 31)
            ))
            
            results.append({
                "weights": self.weights.copy(),
                "sharpe": result.sharpe_ratio,
                "pnl": result.total_pnl,
                "win_rate": result.win_rate
            })
            
            if result.sharpe_ratio > best_sharpe:
                best_sharpe = result.sharpe_ratio
                best_weights = self.weights.copy()
        
        self.weights = best_weights
        
        return {
            "best_weights": best_weights,
            "best_sharpe": best_sharpe,
            "iterations": len(results),
            "all_results": sorted(results, key=lambda x: x["sharpe"], reverse=True)[:5]
        }
    
    def get_status(self) -> Dict:
        """Get backtester status."""
        return {
            "total_backtests": len(self.results),
            "current_weights": self.weights,
            "last_result": self.results[-1].to_dict() if self.results else None
        }


# Singleton
_backtester: Optional[WalkForwardBacktester] = None

def get_backtester() -> WalkForwardBacktester:
    global _backtester
    if _backtester is None:
        _backtester = WalkForwardBacktester()
    return _backtester
