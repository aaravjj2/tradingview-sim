"""
Roll Manager
Handles option position rolling (moving to later expiration)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class RollOpportunity:
    """Represents a roll opportunity"""
    symbol: str
    current_expiration: str
    current_strike: float
    current_value: float
    new_expiration: str
    new_strike: float
    new_value: float
    credit_debit: float  # Positive = credit, negative = debit
    delta_change: float
    theta_change: float
    days_added: int


class RollManager:
    """
    Manages option position rolling
    
    Roll strategies:
    - Roll out: Move to later expiration (same strike)
    - Roll up/down: Move to different strike (same expiration)
    - Roll out and up/down: Combination
    """
    
    def __init__(self, alpaca_service):
        self.alpaca = alpaca_service
    
    async def calculate_roll(
        self,
        ticker: str,
        current_position: Dict,
        target_dte: int = 7,
        strike_adjustment: float = 0.0
    ) -> Optional[RollOpportunity]:
        """
        Calculate roll opportunity for a position
        
        Args:
            ticker: Underlying symbol
            current_position: Current option position details
            target_dte: Target days to expiration after roll
            strike_adjustment: Strike change (positive = roll up, negative = roll down)
        
        Returns:
            RollOpportunity with details
        """
        try:
            current_strike = current_position.get('strike', 0)
            current_exp = current_position.get('expiration', '')
            option_type = current_position.get('option_type', 'call')
            is_short = current_position.get('position', 'long') == 'short'
            
            # Get current option value
            options = await self.alpaca.get_options_chain(ticker)
            if not options:
                return None
            
            chain = options['calls'] if option_type == 'call' else options['puts']
            
            # Find current option
            current_option = next(
                (o for o in chain if abs(o['strike'] - current_strike) < 0.5),
                None
            )
            
            if not current_option:
                return None
            
            current_value = current_option.get('mid', current_option.get('ask', 0))
            current_delta = current_option.get('delta', 0.5)
            current_theta = current_option.get('theta', -0.05)
            
            # Calculate new strike and find new option
            new_strike = current_strike + strike_adjustment
            new_exp_date = datetime.now() + timedelta(days=target_dte)
            new_exp = new_exp_date.strftime('%Y-%m-%d')
            
            # Find new option (would need to filter by expiration in real implementation)
            new_option = next(
                (o for o in chain if abs(o['strike'] - new_strike) < 0.5),
                None
            )
            
            if not new_option:
                # Estimate new value
                new_value = current_value * 1.15  # Add ~15% for time value
            else:
                new_value = new_option.get('mid', new_option.get('ask', 0))
            
            new_delta = new_option.get('delta', current_delta) if new_option else current_delta
            new_theta = new_option.get('theta', current_theta * 0.8) if new_option else current_theta * 0.8
            
            # Calculate credit/debit
            if is_short:
                # Rolling a short: buy back current, sell new
                credit_debit = new_value - current_value  # Credit if new > current
            else:
                # Rolling a long: sell current, buy new
                credit_debit = current_value - new_value  # Credit if current > new
            
            # Calculate current DTE
            try:
                current_exp_date = datetime.strptime(current_exp, '%Y-%m-%d')
                current_dte = (current_exp_date - datetime.now()).days
            except:
                current_dte = 0
            
            days_added = target_dte - current_dte
            
            return RollOpportunity(
                symbol=ticker,
                current_expiration=current_exp,
                current_strike=current_strike,
                current_value=current_value,
                new_expiration=new_exp,
                new_strike=new_strike,
                new_value=new_value,
                credit_debit=credit_debit,
                delta_change=new_delta - current_delta,
                theta_change=new_theta - current_theta,
                days_added=days_added
            )
            
        except Exception as e:
            print(f"Error calculating roll: {e}")
            return None
    
    async def execute_roll(
        self,
        roll: RollOpportunity,
        quantity: int = 1,
        option_type: str = 'call',
        is_short: bool = True
    ) -> Dict:
        """
        Execute a roll trade
        
        For a short position roll:
        1. Buy to close current position
        2. Sell to open new position
        
        For a long position roll:
        1. Sell to close current position
        2. Buy to open new position
        """
        orders = []
        
        if is_short:
            # Buy back current (BTC)
            orders.append({
                'action': 'buy_to_close',
                'symbol': f"{roll.symbol}{roll.current_expiration.replace('-', '')}{roll.current_strike}{option_type[0].upper()}",
                'quantity': quantity,
                'price': roll.current_value
            })
            
            # Sell new (STO)
            orders.append({
                'action': 'sell_to_open',
                'symbol': f"{roll.symbol}{roll.new_expiration.replace('-', '')}{roll.new_strike}{option_type[0].upper()}",
                'quantity': quantity,
                'price': roll.new_value
            })
        else:
            # Sell current (STC)
            orders.append({
                'action': 'sell_to_close',
                'symbol': f"{roll.symbol}{roll.current_expiration.replace('-', '')}{roll.current_strike}{option_type[0].upper()}",
                'quantity': quantity,
                'price': roll.current_value
            })
            
            # Buy new (BTO)
            orders.append({
                'action': 'buy_to_open',
                'symbol': f"{roll.symbol}{roll.new_expiration.replace('-', '')}{roll.new_strike}{option_type[0].upper()}",
                'quantity': quantity,
                'price': roll.new_value
            })
        
        return {
            'success': True,
            'orders': orders,
            'net_credit_debit': roll.credit_debit * quantity * 100,
            'roll_details': {
                'from': f"{roll.current_expiration} ${roll.current_strike}",
                'to': f"{roll.new_expiration} ${roll.new_strike}",
                'days_added': roll.days_added,
                'delta_change': roll.delta_change,
                'theta_change': roll.theta_change
            }
        }
    
    def recommend_roll(
        self,
        current_position: Dict,
        current_price: float,
        dte: int
    ) -> Dict:
        """
        Recommend optimal roll parameters
        
        Args:
            current_position: Current option position
            current_price: Current underlying price
            dte: Current days to expiration
        """
        current_strike = current_position.get('strike', current_price)
        option_type = current_position.get('option_type', 'call')
        is_short = current_position.get('position', 'long') == 'short'
        
        recommendations = []
        
        # Roll out only (same strike, more time)
        recommendations.append({
            'type': 'Roll Out',
            'description': f"Move to {dte + 7}DTE, same strike",
            'target_dte': dte + 7,
            'strike_adjustment': 0,
            'purpose': 'Add time, collect more premium' if is_short else 'Add time to be right'
        })
        
        # Evaluate if ITM/OTM for adjustment
        if option_type == 'call':
            is_itm = current_strike < current_price
            roll_direction = 'up' if not is_itm else 'down'
            adjustment = 5 if roll_direction == 'up' else -5
        else:
            is_itm = current_strike > current_price
            roll_direction = 'down' if not is_itm else 'up'
            adjustment = -5 if roll_direction == 'down' else 5
        
        # Roll out and adjust
        recommendations.append({
            'type': f'Roll Out and {roll_direction.capitalize()}',
            'description': f"Move to {dte + 7}DTE, adjust strike ${adjustment:+}",
            'target_dte': dte + 7,
            'strike_adjustment': adjustment,
            'purpose': 'Manage delta and add time'
        })
        
        return {
            'current_position': {
                'strike': current_strike,
                'dte': dte,
                'type': option_type,
                'is_short': is_short
            },
            'recommendations': recommendations,
            'is_threatened': is_itm,
            'urgency': 'high' if dte < 7 and is_itm else 'medium' if dte < 14 else 'low'
        }
