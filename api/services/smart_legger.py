"""
Smart Legging Execution
RSI-based entry timing for multi-leg strategies
"""

import numpy as np
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class LegStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass 
class StrategyLeg:
    """Represents a single leg of a multi-leg strategy"""
    leg_id: str
    option_type: str  # 'call' or 'put'
    position: str  # 'long' or 'short'
    strike: float
    expiration: str
    quantity: int
    status: LegStatus
    entry_condition: str  # 'rsi_pullback', 'rsi_spike', 'immediate'
    target_price: Optional[float] = None
    filled_price: Optional[float] = None
    filled_time: Optional[datetime] = None


class SmartLegger:
    """
    Smart execution engine for multi-leg options strategies
    
    Uses RSI and other indicators to time leg entries:
    - Sell Puts on RSI pullback (oversold)
    - Sell Calls on RSI spike (overbought)
    - Buy options at specified targets
    """
    
    def __init__(self, alpaca_service):
        self.alpaca = alpaca_service
        self.pending_legs: Dict[str, List[StrategyLeg]] = {}
        self.rsi_cache: Dict[str, float] = {}
        
        self.config = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'max_wait_minutes': 60,
            'price_improvement_pct': 0.02,  # Try to get 2% better price
        }
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI from price series"""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        prices = np.array(prices)
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def determine_entry_condition(self, leg: Dict) -> str:
        """
        Determine optimal entry condition for a leg
        
        Short options: Wait for favorable RSI
        Long options: Enter immediately or on dip
        """
        position = leg.get('position', 'long')
        option_type = leg.get('option_type', 'call')
        
        if position == 'short':
            if option_type == 'put':
                return 'rsi_pullback'  # Sell puts when oversold
            else:
                return 'rsi_spike'  # Sell calls when overbought
        else:
            return 'immediate'  # Buy legs immediately
    
    async def create_legging_plan(
        self,
        ticker: str,
        strategy_legs: List[Dict]
    ) -> Dict:
        """
        Create a smart execution plan for a multi-leg strategy
        
        Args:
            ticker: Underlying symbol
            strategy_legs: List of leg definitions
        
        Returns:
            Execution plan with conditions for each leg
        """
        plan_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        legs = []
        
        for i, leg_def in enumerate(strategy_legs):
            condition = self.determine_entry_condition(leg_def)
            
            leg = StrategyLeg(
                leg_id=f"{plan_id}_leg{i}",
                option_type=leg_def.get('option_type', 'call'),
                position=leg_def.get('position', 'long'),
                strike=leg_def.get('strike', 0),
                expiration=leg_def.get('expiration', ''),
                quantity=leg_def.get('quantity', 1),
                status=LegStatus.PENDING,
                entry_condition=condition
            )
            legs.append(leg)
        
        self.pending_legs[plan_id] = legs
        
        # Order legs: immediate first, then conditional
        execution_order = sorted(legs, key=lambda x: 0 if x.entry_condition == 'immediate' else 1)
        
        return {
            'plan_id': plan_id,
            'ticker': ticker,
            'total_legs': len(legs),
            'execution_order': [
                {
                    'leg_id': leg.leg_id,
                    'description': f"{leg.position} {leg.option_type} ${leg.strike}",
                    'condition': leg.entry_condition,
                    'status': leg.status.value
                }
                for leg in execution_order
            ]
        }
    
    async def check_entry_conditions(
        self,
        plan_id: str,
        current_rsi: float
    ) -> List[StrategyLeg]:
        """
        Check which legs are ready to execute based on current conditions
        
        Returns list of legs ready for execution
        """
        if plan_id not in self.pending_legs:
            return []
        
        ready_legs = []
        
        for leg in self.pending_legs[plan_id]:
            if leg.status != LegStatus.PENDING:
                continue
            
            if leg.entry_condition == 'immediate':
                ready_legs.append(leg)
            
            elif leg.entry_condition == 'rsi_pullback':
                if current_rsi <= self.config['rsi_oversold']:
                    ready_legs.append(leg)
            
            elif leg.entry_condition == 'rsi_spike':
                if current_rsi >= self.config['rsi_overbought']:
                    ready_legs.append(leg)
        
        return ready_legs
    
    async def execute_leg(
        self,
        leg: StrategyLeg,
        ticker: str,
        paper_mode: bool = True
    ) -> bool:
        """Execute a single leg"""
        try:
            # Build option symbol
            side = 'buy' if leg.position == 'long' else 'sell'
            
            # Get current option price
            options = await self.alpaca.get_options_chain(ticker)
            
            if not options:
                return False
            
            # Find the specific option
            chain = options['calls'] if leg.option_type == 'call' else options['puts']
            option = next(
                (o for o in chain if abs(o['strike'] - leg.strike) < 0.5),
                None
            )
            
            if not option:
                return False
            
            # Submit order
            result = await self.alpaca.submit_order(
                symbol=option.get('symbol', f"{ticker}{leg.expiration}{leg.strike}{leg.option_type[0].upper()}"),
                qty=leg.quantity,
                side=side,
                order_type='limit',
                limit_price=option.get('mid', option.get('ask', 0))
            )
            
            if result.get('status') in ['accepted', 'filled', 'new']:
                leg.status = LegStatus.FILLED
                leg.filled_price = option.get('mid', 0)
                leg.filled_time = datetime.now()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error executing leg: {e}")
            return False
    
    async def run_execution_loop(
        self,
        plan_id: str,
        ticker: str,
        historical_prices: List[float]
    ):
        """
        Main execution loop for a legging plan
        
        Monitors RSI and executes legs when conditions are met
        """
        start_time = datetime.now()
        max_wait = self.config['max_wait_minutes'] * 60
        
        while (datetime.now() - start_time).seconds < max_wait:
            # Calculate current RSI
            current_rsi = self.calculate_rsi(historical_prices)
            
            # Check which legs are ready
            ready_legs = await self.check_entry_conditions(plan_id, current_rsi)
            
            # Execute ready legs
            for leg in ready_legs:
                success = await self.execute_leg(leg, ticker)
                if success:
                    print(f"Executed: {leg.position} {leg.option_type} ${leg.strike}")
            
            # Check if all legs are filled
            all_filled = all(
                leg.status == LegStatus.FILLED 
                for leg in self.pending_legs.get(plan_id, [])
            )
            
            if all_filled:
                print(f"All legs filled for plan {plan_id}")
                return
            
            await asyncio.sleep(60)  # Check every minute
        
        # Timeout - execute remaining legs at market
        for leg in self.pending_legs.get(plan_id, []):
            if leg.status == LegStatus.PENDING:
                await self.execute_leg(leg, ticker)
    
    def get_plan_status(self, plan_id: str) -> Dict:
        """Get current status of an execution plan"""
        if plan_id not in self.pending_legs:
            return {'error': 'Plan not found'}
        
        legs = self.pending_legs[plan_id]
        
        return {
            'plan_id': plan_id,
            'legs': [
                {
                    'leg_id': leg.leg_id,
                    'description': f"{leg.position} {leg.option_type} ${leg.strike}",
                    'condition': leg.entry_condition,
                    'status': leg.status.value,
                    'filled_price': leg.filled_price,
                    'filled_time': leg.filled_time.isoformat() if leg.filled_time else None
                }
                for leg in legs
            ],
            'filled_count': sum(1 for leg in legs if leg.status == LegStatus.FILLED),
            'total_count': len(legs)
        }


# End of file
