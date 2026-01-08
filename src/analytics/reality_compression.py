"""
Reality Compression Engine

Simulates months of behavioral evidence in days through Monte Carlo stress testing.

Features:
- Randomized execution delays (0-2 days)
- Slippage inflation (1×-5×)
- Partial fills (50%-100%)

Outputs:
- Survival rate
- Max drawdown distribution
- Exit timing error histogram
"""

import os
import sys
import random
import hashlib
import numpy as np
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from workspace.volgate.model_adapter import predict, load_model


@dataclass
class SimulationResult:
    """Result of a single compressed reality simulation."""
    seed: int
    symbol: str
    days_simulated: int
    survival: bool
    max_drawdown_pct: float
    final_pnl: float
    exit_latency_bars: List[int]
    trades_executed: int
    partial_fill_rate: float
    avg_slippage_bps: float
    regime_flips: int
    breach_reason: Optional[str] = None


@dataclass
class CompressionConfig:
    """Configuration for reality compression simulation."""
    delay_range: Tuple[int, int] = (0, 2)  # days
    slippage_multiplier_range: Tuple[float, float] = (1.0, 5.0)
    partial_fill_range: Tuple[float, float] = (0.5, 1.0)
    max_dd_threshold: float = 0.25  # 25% max drawdown
    initial_capital: float = 100000.0
    base_slippage_bps: float = 8.0


class RealityCompressionEngine:
    """
    Monte Carlo stress test engine for the VolGate strategy.
    
    Mandate: Falsification, not improvement.
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self.model = load_model()
        
    def _generate_synthetic_bars(self, symbol: str, days: int, seed: int) -> List[Dict]:
        """Generate synthetic price bars for simulation."""
        random.seed(seed)
        np.random.seed(seed)
        
        # Base prices by symbol
        base_prices = {
            "SPY": 590.0,
            "GLD": 185.0,
            "TLT": 95.0,
        }
        base_price = base_prices.get(symbol, 100.0)
        
        bars = []
        price = base_price
        
        for i in range(days):
            # Random walk with mean reversion
            drift = np.random.normal(0.0002, 0.015)  # ~1.5% daily vol
            price = price * (1 + drift)
            
            # Generate OHLCV
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            open_price = low + (high - low) * random.random()
            close = low + (high - low) * random.random()
            volume = int(np.random.lognormal(16, 0.5))
            
            bar_date = date(2026, 1, 1) + timedelta(days=i)
            
            bars.append({
                "timestamp": datetime.combine(bar_date, datetime.min.time()).isoformat(),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume,
            })
            
            price = close
            
        return bars
    
    def _create_snapshot(self, symbol: str, bars: List[Dict], decision_time: str) -> Dict:
        """Create a snapshot for the model adapter."""
        return {
            "symbol": symbol,
            "decision_time": decision_time,
            "bars": bars[-30:] if len(bars) >= 30 else bars,  # Last 30 bars
            "vix": 15.0 + random.uniform(-5, 10),
            "regime": random.choice(["trending", "choppy", "volatile"]),
        }
    
    def run_single_simulation(self, symbol: str, days: int, seed: int) -> SimulationResult:
        """
        Run a single compressed reality simulation.
        
        Args:
            symbol: Trading symbol (SPY, GLD, TLT)
            days: Number of days to simulate
            seed: Random seed for reproducibility
        """
        random.seed(seed)
        np.random.seed(seed)
        
        # Generate synthetic price data
        bars = self._generate_synthetic_bars(symbol, days, seed)
        
        # Simulation state
        capital = self.config.initial_capital
        peak_capital = capital
        max_dd = 0.0
        position = 0
        entry_price = 0.0
        trades = []
        exit_latencies = []
        regime_flips = 0
        last_signal = 0
        slippage_samples = []
        partial_fills = []
        
        # Run through each day
        for i in range(30, len(bars)):  # Need 30 bars for lookback
            current_bar = bars[i]
            decision_time = current_bar["timestamp"]
            
            # Create snapshot and get prediction
            snapshot = self._create_snapshot(symbol, bars[:i+1], decision_time)
            
            try:
                prediction = predict(self.model, snapshot)
            except ValueError:
                continue  # Skip on time causality errors
            
            signal = prediction["signal"]
            exposure = prediction["exposure"]
            
            # Track regime flips
            if signal != last_signal:
                regime_flips += 1
            last_signal = signal
            
            # Apply randomized execution delay
            delay_days = random.randint(*self.config.delay_range)
            exec_bar_idx = min(i + delay_days, len(bars) - 1)
            exec_price = bars[exec_bar_idx]["close"]
            
            # Apply slippage inflation
            slippage_mult = random.uniform(*self.config.slippage_multiplier_range)
            slippage_bps = self.config.base_slippage_bps * slippage_mult
            slippage_pct = slippage_bps / 10000
            slippage_samples.append(slippage_bps)
            
            # Apply partial fills
            fill_rate = random.uniform(*self.config.partial_fill_range)
            partial_fills.append(fill_rate)
            
            # Execute trade logic
            if signal == 1 and position == 0:
                # Enter long position
                exec_price_adj = exec_price * (1 + slippage_pct)
                target_shares = int((capital * exposure) / exec_price_adj)
                actual_shares = int(target_shares * fill_rate)
                
                if actual_shares > 0:
                    position = actual_shares
                    entry_price = exec_price_adj
                    trades.append({
                        "type": "entry",
                        "day": i,
                        "price": exec_price_adj,
                        "shares": actual_shares,
                        "delay": delay_days,
                    })
                    exit_latencies.append(delay_days)
                    
            elif signal == -1 and position > 0:
                # Exit position
                exec_price_adj = exec_price * (1 - slippage_pct)
                pnl = (exec_price_adj - entry_price) * position
                capital += pnl
                
                trades.append({
                    "type": "exit",
                    "day": i,
                    "price": exec_price_adj,
                    "shares": position,
                    "pnl": pnl,
                    "delay": delay_days,
                })
                exit_latencies.append(delay_days)
                
                position = 0
                entry_price = 0.0
            
            # Update peak and drawdown
            # Mark-to-market if in position
            if position > 0:
                mtm_value = capital + (current_bar["close"] - entry_price) * position
            else:
                mtm_value = capital
                
            peak_capital = max(peak_capital, mtm_value)
            current_dd = (peak_capital - mtm_value) / peak_capital
            max_dd = max(max_dd, current_dd)
            
            # Check for DD breach
            if max_dd > self.config.max_dd_threshold:
                return SimulationResult(
                    seed=seed,
                    symbol=symbol,
                    days_simulated=i,
                    survival=False,
                    max_drawdown_pct=max_dd * 100,
                    final_pnl=capital - self.config.initial_capital,
                    exit_latency_bars=exit_latencies,
                    trades_executed=len(trades),
                    partial_fill_rate=np.mean(partial_fills) if partial_fills else 1.0,
                    avg_slippage_bps=np.mean(slippage_samples) if slippage_samples else 0.0,
                    regime_flips=regime_flips,
                    breach_reason=f"Max DD {max_dd*100:.1f}% exceeded threshold {self.config.max_dd_threshold*100:.0f}%",
                )
        
        # Close any remaining position
        if position > 0:
            final_price = bars[-1]["close"]
            pnl = (final_price - entry_price) * position
            capital += pnl
        
        return SimulationResult(
            seed=seed,
            symbol=symbol,
            days_simulated=days,
            survival=True,
            max_drawdown_pct=max_dd * 100,
            final_pnl=capital - self.config.initial_capital,
            exit_latency_bars=exit_latencies,
            trades_executed=len(trades),
            partial_fill_rate=np.mean(partial_fills) if partial_fills else 1.0,
            avg_slippage_bps=np.mean(slippage_samples) if slippage_samples else 0.0,
            regime_flips=regime_flips,
        )
    
    def run_batch(self, symbols: List[str], simulations_per_symbol: int, 
                  days: int = 252) -> Dict[str, List[SimulationResult]]:
        """
        Run batch of simulations across multiple symbols.
        
        Args:
            symbols: List of symbols to test
            simulations_per_symbol: Number of simulations per symbol
            days: Trading days to simulate (252 = 1 year)
        """
        results = {}
        
        for symbol in symbols:
            symbol_results = []
            for i in range(simulations_per_symbol):
                seed = hash(f"{symbol}-{i}") % (2**31)
                result = self.run_single_simulation(symbol, days, seed)
                symbol_results.append(result)
            results[symbol] = symbol_results
            
        return results
    
    def generate_report(self, results: Dict[str, List[SimulationResult]], 
                        output_dir: str) -> Dict:
        """Generate comprehensive report from simulation results."""
        os.makedirs(output_dir, exist_ok=True)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "delay_range": self.config.delay_range,
                "slippage_range": self.config.slippage_multiplier_range,
                "partial_fill_range": self.config.partial_fill_range,
                "max_dd_threshold": self.config.max_dd_threshold,
            },
            "symbols": {},
            "overall": {},
        }
        
        all_results = []
        for symbol, symbol_results in results.items():
            all_results.extend(symbol_results)
            
            survivals = [r.survival for r in symbol_results]
            max_dds = [r.max_drawdown_pct for r in symbol_results]
            pnls = [r.final_pnl for r in symbol_results]
            latencies = []
            for r in symbol_results:
                latencies.extend(r.exit_latency_bars)
            
            summary["symbols"][symbol] = {
                "total_simulations": len(symbol_results),
                "survival_rate": float(sum(survivals) / len(survivals) * 100),
                "avg_max_dd_pct": float(np.mean(max_dds)),
                "max_max_dd_pct": float(max(max_dds)),
                "avg_pnl": float(np.mean(pnls)),
                "median_pnl": float(np.median(pnls)),
                "avg_exit_latency_bars": float(np.mean(latencies)) if latencies else 0.0,
                "max_exit_latency_bars": int(max(latencies)) if latencies else 0,
            }
        
        # Overall statistics
        all_survivals = [r.survival for r in all_results]
        all_max_dds = [r.max_drawdown_pct for r in all_results]
        all_latencies = []
        for r in all_results:
            all_latencies.extend(r.exit_latency_bars)
        
        summary["overall"] = {
            "total_simulations": len(all_results),
            "survival_rate": float(sum(all_survivals) / len(all_survivals) * 100),
            "avg_max_dd_pct": float(np.mean(all_max_dds)),
            "p95_max_dd_pct": float(np.percentile(all_max_dds, 95)),
            "avg_exit_latency_bars": float(np.mean(all_latencies)) if all_latencies else 0.0,
            "exit_latency_p95": float(np.percentile(all_latencies, 95)) if all_latencies else 0.0,
            "acceptance_criteria": {
                "survival_rate_target": 95.0,
                "survival_rate_met": bool(sum(all_survivals) / len(all_survivals) * 100 >= 95.0),
                "exit_latency_target": 2,
                "exit_latency_met": bool(np.percentile(all_latencies, 95) <= 2) if all_latencies else True,
            }
        }
        
        # Save summary JSON
        with open(os.path.join(output_dir, "compression_summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        
        # Save detailed CSV
        with open(os.path.join(output_dir, "simulation_details.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "seed", "symbol", "days", "survival", "max_dd_pct", 
                "final_pnl", "trades", "avg_slippage_bps", "regime_flips", "breach_reason"
            ])
            for r in all_results:
                writer.writerow([
                    r.seed, r.symbol, r.days_simulated, r.survival,
                    f"{r.max_drawdown_pct:.2f}", f"{r.final_pnl:.2f}",
                    r.trades_executed, f"{r.avg_slippage_bps:.1f}",
                    r.regime_flips, r.breach_reason or ""
                ])
        
        # Save exit latency histogram data
        with open(os.path.join(output_dir, "exit_latency_histogram.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["latency_bars", "count"])
            latency_counts = {}
            for lat in all_latencies:
                latency_counts[lat] = latency_counts.get(lat, 0) + 1
            for lat in sorted(latency_counts.keys()):
                writer.writerow([lat, latency_counts[lat]])
        
        # Save max DD distribution
        with open(os.path.join(output_dir, "max_dd_distribution.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["percentile", "max_dd_pct"])
            for p in [5, 10, 25, 50, 75, 90, 95, 99]:
                writer.writerow([p, np.percentile(all_max_dds, p)])
        
        return summary


def run_compressed_reality(symbols: List[str], simulations: int = 100, 
                           days: int = 252, output_dir: str = None) -> Dict:
    """
    Main entry point for running compressed reality simulations.
    
    Args:
        symbols: Trading symbols to test
        simulations: Number of simulations per symbol
        days: Trading days per simulation
        output_dir: Output directory for results
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts", "reality_compression"
        )
    
    engine = RealityCompressionEngine()
    results = engine.run_batch(symbols, simulations, days)
    summary = engine.generate_report(results, output_dir)
    
    return summary


if __name__ == "__main__":
    # Default run with SPY, GLD, TLT
    symbols = ["SPY", "GLD", "TLT"]
    summary = run_compressed_reality(symbols, simulations=100, days=252)
    
    print("\n" + "=" * 50)
    print("REALITY COMPRESSION COMPLETE")
    print("=" * 50)
    print(f"Total Simulations: {summary['overall']['total_simulations']}")
    print(f"Survival Rate: {summary['overall']['survival_rate']:.1f}%")
    print(f"Avg Max DD: {summary['overall']['avg_max_dd_pct']:.1f}%")
    print(f"P95 Max DD: {summary['overall']['p95_max_dd_pct']:.1f}%")
    print(f"Avg Exit Latency: {summary['overall']['avg_exit_latency_bars']:.1f} bars")
    print("=" * 50)
    
    # Check acceptance criteria
    criteria = summary['overall']['acceptance_criteria']
    if criteria['survival_rate_met'] and criteria['exit_latency_met']:
        print("✅ ALL ACCEPTANCE CRITERIA MET")
    else:
        print("❌ ACCEPTANCE CRITERIA NOT MET")
        if not criteria['survival_rate_met']:
            print(f"   - Survival rate {summary['overall']['survival_rate']:.1f}% < {criteria['survival_rate_target']}%")
        if not criteria['exit_latency_met']:
            print(f"   - Exit latency P95 > {criteria['exit_latency_target']} bars")
