"""
Behavioral Consistency Audit

Ensures the VolGate system behaves predictably and boringly.

Measures:
- % time in market
- Average hold duration
- Trade clustering
- Regime flip frequency

Compares against:
- Buy & Hold baseline
- Random Gate baseline
- Always-Risk-Off baseline
"""

import os
import sys
import random
import numpy as np
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from workspace.volgate.model_adapter import predict, load_model


@dataclass
class BehavioralMetrics:
    """Behavioral metrics for a strategy."""
    name: str
    time_in_market_pct: float
    avg_hold_duration_days: float
    trade_count: int
    regime_flips: int
    churn_rate: float  # trades per day
    max_drawdown_pct: float
    dd_slope: float  # rate of DD increase
    final_pnl: float
    sharpe_ratio: float
    trade_clustering_score: float  # 0 = evenly spread, 1 = heavily clustered


class BehavioralAudit:
    """
    Behavioral consistency audit for the VolGate strategy.
    
    Compares strategy behavior against baselines to ensure
    predictable and boring behavior.
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.model = load_model()
        
    def _generate_price_series(self, symbol: str, days: int, seed: int) -> List[float]:
        """Generate synthetic price series."""
        random.seed(seed)
        np.random.seed(seed)
        
        base_prices = {"SPY": 590.0, "GLD": 185.0, "TLT": 95.0}
        price = base_prices.get(symbol, 100.0)
        
        prices = [price]
        for _ in range(days - 1):
            drift = np.random.normal(0.0003, 0.012)  # ~1.2% daily vol
            price = price * (1 + drift)
            prices.append(price)
            
        return prices
    
    def _calculate_metrics(self, name: str, positions: List[int], 
                           prices: List[float], trades: List[Dict]) -> BehavioralMetrics:
        """Calculate behavioral metrics from positions and prices."""
        days = len(positions)
        
        # Time in market
        time_in_market = sum(1 for p in positions if p > 0) / days * 100
        
        # Hold durations
        hold_durations = []
        current_hold = 0
        for p in positions:
            if p > 0:
                current_hold += 1
            elif current_hold > 0:
                hold_durations.append(current_hold)
                current_hold = 0
        if current_hold > 0:
            hold_durations.append(current_hold)
        avg_hold = np.mean(hold_durations) if hold_durations else 0
        
        # Trade count and regime flips
        trade_count = len(trades)
        regime_flips = sum(1 for i in range(1, len(positions)) 
                          if (positions[i] > 0) != (positions[i-1] > 0))
        
        # Churn rate
        churn_rate = trade_count / days if days > 0 else 0
        
        # Drawdown calculation
        equity = [self.initial_capital]
        for i in range(1, len(prices)):
            if positions[i-1] > 0:
                pnl = (prices[i] - prices[i-1]) * positions[i-1]
            else:
                pnl = 0
            equity.append(equity[-1] + pnl)
        
        peak = [equity[0]]
        for e in equity[1:]:
            peak.append(max(peak[-1], e))
        
        drawdowns = [(peak[i] - equity[i]) / peak[i] if peak[i] > 0 else 0 
                     for i in range(len(equity))]
        max_dd = max(drawdowns) * 100
        
        # DD slope (rate of increase during drawdown periods)
        dd_slopes = []
        for i in range(1, len(drawdowns)):
            if drawdowns[i] > drawdowns[i-1]:
                dd_slopes.append(drawdowns[i] - drawdowns[i-1])
        dd_slope = np.mean(dd_slopes) if dd_slopes else 0
        
        # Final P&L
        final_pnl = equity[-1] - self.initial_capital
        
        # Sharpe ratio (simplified, assuming risk-free = 0)
        returns = [(equity[i] - equity[i-1]) / equity[i-1] if equity[i-1] > 0 else 0 
                   for i in range(1, len(equity))]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Trade clustering (Gini coefficient of trade spacing)
        if len(trades) > 1:
            trade_days = [t.get("day", i) for i, t in enumerate(trades)]
            spacings = [trade_days[i+1] - trade_days[i] for i in range(len(trade_days)-1)]
            if spacings:
                spacings_sorted = sorted(spacings)
                n = len(spacings_sorted)
                cumsum = np.cumsum(spacings_sorted)
                gini = (2 * sum((i+1) * s for i, s in enumerate(spacings_sorted)) - 
                        (n+1) * cumsum[-1]) / (n * cumsum[-1]) if cumsum[-1] > 0 else 0
                clustering = max(0, min(1, gini))
            else:
                clustering = 0
        else:
            clustering = 0
        
        return BehavioralMetrics(
            name=name,
            time_in_market_pct=time_in_market,
            avg_hold_duration_days=avg_hold,
            trade_count=trade_count,
            regime_flips=regime_flips,
            churn_rate=churn_rate,
            max_drawdown_pct=max_dd,
            dd_slope=dd_slope,
            final_pnl=final_pnl,
            sharpe_ratio=sharpe,
            trade_clustering_score=clustering,
        )
    
    def run_volgate_strategy(self, symbol: str, prices: List[float], 
                             seed: int) -> Tuple[List[int], List[Dict]]:
        """Run VolGate strategy with behavioral state machine."""
        random.seed(seed)
        
        # Import and create fresh state machine for this run
        from src.signals.behavioral_state import BehavioralStateMachine, BehavioralConfig
        
        config = BehavioralConfig(
            N_exit_confirm=3,
            M_reentry_confirm=2,
            cooldown_days=5,
            phased_reentry_steps=[0.25, 0.5, 1.0],
            enable_hysteresis=True,
            enable_cooldown=True,
            enable_phased_reentry=True,
        )
        state_machine = BehavioralStateMachine(config)
        
        positions = []
        trades = []
        position = 0
        entry_price = 0.0
        
        # Base date for proper date arithmetic
        from datetime import datetime as dt, timedelta
        base_date = dt(2026, 1, 1)
        
        for i, price in enumerate(prices):
            if i < 30:  # Need lookback
                positions.append(0)
                continue
            
            # Generate proper dates using timedelta
            current_date = base_date + timedelta(days=i)
            decision_time = current_date.strftime("%Y-%m-%dT15:55:00")
            
            # Create synthetic snapshot with proper dates
            bars = []
            for j in range(max(0, i-30), i+1):
                bar_date = base_date + timedelta(days=j)
                bars.append({
                    "close": prices[j], 
                    "timestamp": bar_date.strftime("%Y-%m-%dT15:55:00")
                })
            
            snapshot = {
                "symbol": symbol,
                "decision_time": decision_time,
                "bars": bars,
                "vix": 15.0 + random.uniform(-3, 5),
                "regime": random.choice(["trending", "choppy"]),
            }
            
            try:
                prediction = predict(self.model, snapshot)
                raw_signal = prediction["signal"]
                confidence = prediction["confidence"]
                
                # Calculate volatility from price history
                if len(prices) > i and i > 20:
                    returns = [(prices[j] - prices[j-1]) / prices[j-1] 
                               for j in range(max(1, i-20), i+1)]
                    volatility = np.std(returns) * np.sqrt(252) if returns else 0.15
                else:
                    volatility = 0.15
                
                # Process through behavioral state machine
                filtered_signal, exposure = state_machine.process_signal(
                    raw_signal, confidence, volatility, current_date.strftime("%Y-%m-%d")
                )
                
            except Exception:
                filtered_signal = 0
                exposure = 0.0
            
            # Execute filtered signal
            if filtered_signal == 1 and position == 0:
                shares = int((self.initial_capital * exposure) / price) if exposure > 0 else 0
                if shares > 0:
                    position = shares
                    entry_price = price
                    trades.append({"type": "entry", "day": i, "price": price, "shares": shares})
            elif filtered_signal == -1 and position > 0:
                trades.append({"type": "exit", "day": i, "price": price, "shares": position})
                position = 0
                entry_price = 0.0
            
            positions.append(position)
            
        return positions, trades
    
    def run_buy_and_hold(self, prices: List[float]) -> Tuple[List[int], List[Dict]]:
        """Buy and hold baseline."""
        shares = int(self.initial_capital / prices[0])
        positions = [shares] * len(prices)
        trades = [{"type": "entry", "day": 0, "price": prices[0], "shares": shares}]
        return positions, trades
    
    def run_random_gate(self, prices: List[float], seed: int) -> Tuple[List[int], List[Dict]]:
        """Random gate baseline - randomly enters/exits."""
        random.seed(seed)
        
        positions = []
        trades = []
        position = 0
        
        for i, price in enumerate(prices):
            if random.random() < 0.02:  # 2% chance to flip
                if position == 0:
                    shares = int(self.initial_capital * 0.5 / price)
                    position = shares
                    trades.append({"type": "entry", "day": i, "price": price, "shares": shares})
                else:
                    trades.append({"type": "exit", "day": i, "price": price, "shares": position})
                    position = 0
            positions.append(position)
            
        return positions, trades
    
    def run_always_risk_off(self, prices: List[float]) -> Tuple[List[int], List[Dict]]:
        """Always risk-off baseline - never invests."""
        return [0] * len(prices), []
    
    def run_audit(self, symbol: str, days: int = 252, seed: int = 42) -> Dict:
        """Run full behavioral audit comparison."""
        prices = self._generate_price_series(symbol, days, seed)
        
        # Run all strategies
        vg_positions, vg_trades = self.run_volgate_strategy(symbol, prices, seed)
        bh_positions, bh_trades = self.run_buy_and_hold(prices)
        rg_positions, rg_trades = self.run_random_gate(prices, seed)
        ro_positions, ro_trades = self.run_always_risk_off(prices)
        
        # Calculate metrics
        volgate = self._calculate_metrics("VolGate", vg_positions, prices, vg_trades)
        buy_hold = self._calculate_metrics("Buy & Hold", bh_positions, prices, bh_trades)
        random_gate = self._calculate_metrics("Random Gate", rg_positions, prices, rg_trades)
        risk_off = self._calculate_metrics("Always Risk-Off", ro_positions, prices, ro_trades)
        
        # Comparison checks
        checks = {
            "lower_churn_than_random": volgate.churn_rate < random_gate.churn_rate,
            "lower_dd_slope_than_buy_hold": volgate.dd_slope < buy_hold.dd_slope,
            "no_regime_thrashing": volgate.regime_flips < days * 0.1,  # <10% days have flips
            "reasonable_time_in_market": 15 <= volgate.time_in_market_pct <= 90,  # Allow hysteresis strategies
        }
        
        return {
            "symbol": symbol,
            "days": days,
            "strategies": {
                "volgate": volgate.__dict__,
                "buy_hold": buy_hold.__dict__,
                "random_gate": random_gate.__dict__,
                "risk_off": risk_off.__dict__,
            },
            "checks": checks,
            "all_checks_passed": all(checks.values()),
        }
    
    def generate_report(self, symbols: List[str], output_dir: str, 
                        days: int = 252, seeds: int = 10) -> Dict:
        """Generate comprehensive behavioral audit report."""
        os.makedirs(output_dir, exist_ok=True)
        
        all_results = []
        for symbol in symbols:
            for seed in range(seeds):
                result = self.run_audit(symbol, days, seed)
                all_results.append(result)
        
        # Aggregate checks
        check_results = {
            "lower_churn_than_random": [],
            "lower_dd_slope_than_buy_hold": [],
            "no_regime_thrashing": [],
            "reasonable_time_in_market": [],
        }
        
        for r in all_results:
            for check, passed in r["checks"].items():
                check_results[check].append(passed)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_audits": len(all_results),
            "symbols": symbols,
            "check_pass_rates": {k: sum(v)/len(v)*100 for k, v in check_results.items()},
            "overall_pass_rate": sum(r["all_checks_passed"] for r in all_results) / len(all_results) * 100,
            "acceptance_criteria": {
                "all_checks_pass_rate_target": 95.0,
                "all_checks_pass_rate_met": sum(r["all_checks_passed"] for r in all_results) / len(all_results) * 100 >= 95.0,
            }
        }
        
        # Save summary
        with open(os.path.join(output_dir, "behavioral_audit_summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        
        # Save detailed results
        with open(os.path.join(output_dir, "behavioral_audit_details.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "symbol", "seed", "volgate_time_in_market", "volgate_churn", 
                "volgate_max_dd", "volgate_dd_slope", "volgate_regime_flips",
                "bh_max_dd", "random_churn", "all_checks_passed"
            ])
            for r in all_results:
                vg = r["strategies"]["volgate"]
                bh = r["strategies"]["buy_hold"]
                rg = r["strategies"]["random_gate"]
                writer.writerow([
                    r["symbol"], 
                    all_results.index(r) % seeds,
                    f"{vg['time_in_market_pct']:.1f}",
                    f"{vg['churn_rate']:.4f}",
                    f"{vg['max_drawdown_pct']:.1f}",
                    f"{vg['dd_slope']:.6f}",
                    vg['regime_flips'],
                    f"{bh['max_drawdown_pct']:.1f}",
                    f"{rg['churn_rate']:.4f}",
                    r["all_checks_passed"],
                ])
        
        return summary


def run_behavioral_audit(symbols: List[str], output_dir: str = None, 
                         days: int = 252, seeds: int = 10) -> Dict:
    """Main entry point for behavioral audit."""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts", "behavioral_audit"
        )
    
    audit = BehavioralAudit()
    summary = audit.generate_report(symbols, output_dir, days, seeds)
    
    return summary


if __name__ == "__main__":
    symbols = ["SPY", "GLD", "TLT"]
    summary = run_behavioral_audit(symbols, days=252, seeds=10)
    
    print("\n" + "=" * 50)
    print("BEHAVIORAL AUDIT COMPLETE")
    print("=" * 50)
    print(f"Total Audits: {summary['total_audits']}")
    print(f"Overall Pass Rate: {summary['overall_pass_rate']:.1f}%")
    print()
    print("Check Pass Rates:")
    for check, rate in summary['check_pass_rates'].items():
        status = "✅" if rate >= 95 else "❌"
        print(f"  {status} {check}: {rate:.1f}%")
    print("=" * 50)
