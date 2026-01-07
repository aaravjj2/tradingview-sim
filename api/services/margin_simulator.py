"""
Portfolio Margin Simulator
Compares Reg-T vs Portfolio Margin requirements
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Position:
    """Represents a position for margin calculation"""
    symbol: str
    position_type: str  # 'stock', 'call', 'put'
    quantity: int
    current_price: float
    strike: Optional[float] = None
    expiration_days: Optional[int] = None
    is_long: bool = True


class MarginSimulator:
    """
    Calculates and compares margin requirements under different regimes:
    
    1. Reg-T Margin: Standard retail margin (Strategy-Based)
    2. Portfolio Margin: Risk-based margin (TIMS methodology)
    
    Portfolio margin typically offers 4-5x better capital efficiency 
    for hedged positions.
    """
    
    def __init__(self):
        # Reg-T margin requirements
        self.reg_t_rates = {
            'stock_initial': 0.50,  # 50% of stock value
            'stock_maintenance': 0.25,  # 25% maintenance
            'naked_call': 0.20,  # 20% of underlying + premium
            'naked_put': 0.20,
            'spread_max_loss': 1.0,  # Max loss of spread
            'covered_call': 0.0,  # No additional margin
        }
        
        # Portfolio margin stress scenarios
        self.stress_scenarios = [
            {'price_move': -0.15, 'vol_move': 0.25, 'name': 'Crash -15%'},
            {'price_move': -0.10, 'vol_move': 0.15, 'name': 'Down -10%'},
            {'price_move': -0.05, 'vol_move': 0.05, 'name': 'Down -5%'},
            {'price_move': 0.0, 'vol_move': 0.0, 'name': 'Unchanged'},
            {'price_move': 0.05, 'vol_move': -0.05, 'name': 'Up +5%'},
            {'price_move': 0.10, 'vol_move': -0.10, 'name': 'Rally +10%'},
            {'price_move': 0.15, 'vol_move': -0.15, 'name': 'Rally +15%'},
        ]
    
    def calculate_reg_t_margin(self, positions: List[Position]) -> Dict:
        """
        Calculate Reg-T margin requirement
        
        Uses strategy-based rules (not risk-based)
        """
        total_margin = 0.0
        breakdown = []
        
        # Group positions by symbol
        by_symbol: Dict[str, List[Position]] = {}
        for pos in positions:
            by_symbol.setdefault(pos.symbol, []).append(pos)
        
        for symbol, symbol_positions in by_symbol.items():
            symbol_margin = 0.0
            
            # Find stock position
            stock_pos = next((p for p in symbol_positions if p.position_type == 'stock'), None)
            long_calls = [p for p in symbol_positions if p.position_type == 'call' and p.is_long]
            short_calls = [p for p in symbol_positions if p.position_type == 'call' and not p.is_long]
            long_puts = [p for p in symbol_positions if p.position_type == 'put' and p.is_long]
            short_puts = [p for p in symbol_positions if p.position_type == 'put' and not p.is_long]
            
            # Stock margin
            if stock_pos:
                stock_value = abs(stock_pos.quantity * stock_pos.current_price * 100)
                stock_margin = stock_value * self.reg_t_rates['stock_initial']
                symbol_margin += stock_margin
            
            # Covered call: no additional margin
            if stock_pos and stock_pos.is_long and short_calls:
                covered = min(abs(stock_pos.quantity), sum(abs(c.quantity) for c in short_calls))
                # Reduce margin by covered amount
                pass
            
            # Naked options
            for call in short_calls:
                if not stock_pos or not stock_pos.is_long:
                    # Naked call: 20% of underlying + OTM amount - premium
                    underlying_value = call.current_price * 100 * abs(call.quantity)
                    margin = underlying_value * self.reg_t_rates['naked_call']
                    symbol_margin += margin
            
            for put in short_puts:
                # Cash-secured put or naked
                strike_value = put.strike * 100 * abs(put.quantity) if put.strike else 0
                margin = strike_value * self.reg_t_rates['naked_put']
                symbol_margin += margin
            
            # Spreads: max loss
            for long_call in long_calls:
                for short_call in short_calls:
                    if long_call.strike and short_call.strike:
                        if short_call.strike < long_call.strike:  # Credit spread
                            max_loss = (long_call.strike - short_call.strike) * 100
                            symbol_margin += max_loss
            
            breakdown.append({
                'symbol': symbol,
                'margin': symbol_margin,
                'positions': len(symbol_positions)
            })
            
            total_margin += symbol_margin
        
        return {
            'total_margin': total_margin,
            'breakdown': breakdown,
            'margin_type': 'Reg-T'
        }
    
    def calculate_portfolio_margin(self, positions: List[Position]) -> Dict:
        """
        Calculate Portfolio Margin using stress testing (TIMS-like)
        
        Tests portfolio across multiple scenarios and uses worst-case
        """
        scenario_results = []
        
        for scenario in self.stress_scenarios:
            # Calculate P/L under this scenario
            total_pnl = 0.0
            
            for pos in positions:
                pos_pnl = self._calculate_position_pnl(pos, scenario)
                total_pnl += pos_pnl
            
            scenario_results.append({
                'scenario': scenario['name'],
                'pnl': total_pnl
            })
        
        # Portfolio margin = worst case loss + buffer
        worst_loss = min(0, min(r['pnl'] for r in scenario_results))
        margin = abs(worst_loss) * 1.15  # 15% buffer
        
        # Minimum margin floor
        total_notional = sum(pos.current_price * abs(pos.quantity) * 100 for pos in positions)
        min_margin = total_notional * 0.05  # 5% minimum
        
        final_margin = max(margin, min_margin)
        
        return {
            'total_margin': final_margin,
            'scenarios': scenario_results,
            'worst_case_loss': worst_loss,
            'margin_type': 'Portfolio Margin',
            'buffer_rate': 0.15
        }
    
    def _calculate_position_pnl(
        self, 
        pos: Position, 
        scenario: Dict
    ) -> float:
        """Calculate P/L for a position under a stress scenario"""
        price_move = scenario['price_move']
        vol_move = scenario['vol_move']
        
        new_price = pos.current_price * (1 + price_move)
        multiplier = 100
        qty = pos.quantity if pos.is_long else -pos.quantity
        
        if pos.position_type == 'stock':
            pnl = qty * (new_price - pos.current_price) * multiplier
        
        elif pos.position_type in ['call', 'put']:
            # Simplified option P/L
            if pos.strike is None:
                return 0.0
            
            # Intrinsic value change
            if pos.position_type == 'call':
                old_intrinsic = max(0, pos.current_price - pos.strike)
                new_intrinsic = max(0, new_price - pos.strike)
            else:
                old_intrinsic = max(0, pos.strike - pos.current_price)
                new_intrinsic = max(0, pos.strike - new_price)
            
            # Time value impact (simplified)
            days = pos.expiration_days or 30
            time_factor = np.sqrt(days / 365)
            vol = 0.25 * (1 + vol_move)  # Base vol with stress
            
            time_value_change = vol * time_factor * pos.current_price * 0.4 * vol_move
            
            pnl = qty * (new_intrinsic - old_intrinsic + time_value_change) * multiplier
        
        else:
            pnl = 0.0
        
        return pnl
    
    def compare_margins(self, positions: List[Position]) -> Dict:
        """
        Compare Reg-T and Portfolio Margin for the same positions
        
        Returns comparison with efficiency metrics
        """
        reg_t = self.calculate_reg_t_margin(positions)
        portfolio = self.calculate_portfolio_margin(positions)
        
        reg_t_margin = reg_t['total_margin']
        pm_margin = portfolio['total_margin']
        
        # Calculate efficiency
        if pm_margin > 0:
            efficiency = reg_t_margin / pm_margin
        else:
            efficiency = 1.0
        
        savings = reg_t_margin - pm_margin
        savings_pct = (savings / reg_t_margin * 100) if reg_t_margin > 0 else 0
        
        return {
            'reg_t': {
                'margin': reg_t_margin,
                'breakdown': reg_t['breakdown']
            },
            'portfolio_margin': {
                'margin': pm_margin,
                'scenarios': portfolio['scenarios'],
                'worst_case': portfolio['worst_case_loss']
            },
            'comparison': {
                'efficiency_ratio': efficiency,
                'capital_savings': savings,
                'savings_percent': savings_pct,
                'recommendation': 'Portfolio Margin' if efficiency > 1.5 else 'Either'
            }
        }
    
    def calculate_for_strategy(
        self,
        strategy_type: str,
        current_price: float,
        quantity: int = 1
    ) -> Dict:
        """
        Quick calculation for common strategy types
        """
        positions = []
        
        if strategy_type == 'covered_call':
            positions = [
                Position('SPY', 'stock', quantity, current_price, is_long=True),
                Position('SPY', 'call', quantity, current_price, 
                        strike=current_price * 1.02, expiration_days=30, is_long=False)
            ]
        
        elif strategy_type == 'iron_condor':
            positions = [
                Position('SPY', 'put', quantity, current_price,
                        strike=current_price * 0.95, expiration_days=30, is_long=True),
                Position('SPY', 'put', quantity, current_price,
                        strike=current_price * 0.97, expiration_days=30, is_long=False),
                Position('SPY', 'call', quantity, current_price,
                        strike=current_price * 1.03, expiration_days=30, is_long=False),
                Position('SPY', 'call', quantity, current_price,
                        strike=current_price * 1.05, expiration_days=30, is_long=True),
            ]
        
        elif strategy_type == 'straddle':
            positions = [
                Position('SPY', 'call', quantity, current_price,
                        strike=current_price, expiration_days=30, is_long=True),
                Position('SPY', 'put', quantity, current_price,
                        strike=current_price, expiration_days=30, is_long=True),
            ]
        
        elif strategy_type == 'naked_put':
            positions = [
                Position('SPY', 'put', quantity, current_price,
                        strike=current_price * 0.95, expiration_days=30, is_long=False),
            ]
        
        return self.compare_margins(positions)
