"""
0DTE Theta Eater Bot
Automated Iron Condor entry for 0DTE/short-dated options
"""

import asyncio
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PositionStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"


@dataclass
class ThetaEaterPosition:
    """Represents an active Iron Condor position"""
    symbol: str
    entry_time: datetime
    entry_credit: float
    short_call_strike: float
    long_call_strike: float
    short_put_strike: float
    long_put_strike: float
    quantity: int
    current_value: float
    status: PositionStatus
    profit_target: float  # 50% of credit
    stop_loss: float  # 200% of credit


class ThetaEaterBot:
    """
    0DTE Theta Eater Strategy
    
    Entry Rules:
    - Enter at 10:00 AM ET
    - Sell 15-delta strangle
    - Add wings (iron condor) for defined risk
    
    Exit Rules:
    - Close at 50% profit
    - Stop loss at 200% of credit received
    - Close by 3:45 PM regardless
    """
    
    def __init__(self, alpaca_service):
        self.alpaca = alpaca_service
        self.positions: Dict[str, ThetaEaterPosition] = {}
        self.is_running = False
        self.config = {
            'entry_time': time(10, 0),  # 10:00 AM
            'exit_time': time(15, 45),  # 3:45 PM
            'target_delta': 0.15,
            'wing_width': 5,  # $5 wings
            'profit_target_pct': 0.50,
            'stop_loss_pct': 2.00,
            'min_credit': 0.50,  # Minimum credit to enter
            'max_positions': 3
        }
    
    async def find_strikes(
        self, 
        ticker: str, 
        current_price: float,
        target_delta: float = 0.15
    ) -> Optional[Dict]:
        """
        Find appropriate strikes for iron condor
        
        Returns strikes for:
        - Short call: ~15 delta
        - Long call: short call + wing width
        - Short put: ~15 delta
        - Long put: short put - wing width
        """
        try:
            options = await self.alpaca.get_options_chain(ticker)
            
            if not options['calls'] or not options['puts']:
                return None
            
            # Find 15 delta strikes
            calls = sorted(options['calls'], key=lambda x: x['strike'])
            puts = sorted(options['puts'], key=lambda x: x['strike'], reverse=True)
            
            # Find short call strike (delta ~0.15)
            short_call = None
            for opt in calls:
                if opt['strike'] > current_price and abs(opt.get('delta', 0)) <= target_delta + 0.05:
                    short_call = opt
                    break
            
            if not short_call:
                # Fallback: use strike ~5% OTM
                short_call = next(
                    (c for c in calls if c['strike'] > current_price * 1.03), 
                    calls[-1]
                )
            
            # Find short put strike (delta ~-0.15)
            short_put = None
            for opt in puts:
                if opt['strike'] < current_price and abs(opt.get('delta', 0)) <= target_delta + 0.05:
                    short_put = opt
                    break
            
            if not short_put:
                # Fallback: use strike ~5% OTM
                short_put = next(
                    (p for p in puts if p['strike'] < current_price * 0.97),
                    puts[-1]
                )
            
            # Calculate wing strikes
            long_call_strike = short_call['strike'] + self.config['wing_width']
            long_put_strike = short_put['strike'] - self.config['wing_width']
            
            # Calculate credit received
            short_credit = short_call.get('bid', 0) + short_put.get('bid', 0)
            
            # Estimate long cost (simplified)
            long_cost = 0.20  # Approximate cost for wings
            
            net_credit = short_credit - long_cost
            
            return {
                'short_call_strike': short_call['strike'],
                'short_call_premium': short_call.get('bid', 0),
                'long_call_strike': long_call_strike,
                'short_put_strike': short_put['strike'],
                'short_put_premium': short_put.get('bid', 0),
                'long_put_strike': long_put_strike,
                'net_credit': net_credit,
                'max_loss': self.config['wing_width'] - net_credit,
                'breakeven_upper': short_call['strike'] + net_credit,
                'breakeven_lower': short_put['strike'] - net_credit
            }
            
        except Exception as e:
            print(f"Error finding strikes: {e}")
            return None
    
    def should_enter(self) -> bool:
        """Check if it's time to enter new positions"""
        now = datetime.now().time()
        
        # Only enter at designated time
        entry_window_start = self.config['entry_time']
        entry_window_end = time(10, 30)  # 30 min window
        
        if not (entry_window_start <= now <= entry_window_end):
            return False
        
        # Check position limits
        if len(self.positions) >= self.config['max_positions']:
            return False
        
        return True
    
    def should_exit(self, position: ThetaEaterPosition) -> Tuple[bool, str]:
        """
        Check if position should be closed
        
        Returns:
            Tuple of (should_exit, reason)
        """
        now = datetime.now().time()
        
        # Time-based exit
        if now >= self.config['exit_time']:
            return True, "end_of_day"
        
        # Profit target (50% of credit)
        current_value = position.current_value
        profit = position.entry_credit - current_value
        
        if profit >= position.profit_target:
            return True, "profit_target"
        
        # Stop loss (200% of credit)
        loss = current_value - position.entry_credit
        if loss >= position.stop_loss:
            return True, "stop_loss"
        
        return False, ""
    
    async def enter_position(
        self, 
        ticker: str, 
        current_price: float,
        quantity: int = 1
    ) -> Optional[ThetaEaterPosition]:
        """Enter a new iron condor position"""
        strikes = await self.find_strikes(ticker, current_price)
        
        if not strikes:
            print(f"Could not find suitable strikes for {ticker}")
            return None
        
        if strikes['net_credit'] < self.config['min_credit']:
            print(f"Credit too low: ${strikes['net_credit']:.2f}")
            return None
        
        # Create position record
        position = ThetaEaterPosition(
            symbol=ticker,
            entry_time=datetime.now(),
            entry_credit=strikes['net_credit'],
            short_call_strike=strikes['short_call_strike'],
            long_call_strike=strikes['long_call_strike'],
            short_put_strike=strikes['short_put_strike'],
            long_put_strike=strikes['long_put_strike'],
            quantity=quantity,
            current_value=strikes['net_credit'],
            status=PositionStatus.OPEN,
            profit_target=strikes['net_credit'] * self.config['profit_target_pct'],
            stop_loss=strikes['net_credit'] * self.config['stop_loss_pct']
        )
        
        self.positions[ticker] = position
        
        print(f"Entered Iron Condor on {ticker}:")
        print(f"  Short Call: ${strikes['short_call_strike']}")
        print(f"  Long Call: ${strikes['long_call_strike']}")
        print(f"  Short Put: ${strikes['short_put_strike']}")
        print(f"  Long Put: ${strikes['long_put_strike']}")
        print(f"  Credit: ${strikes['net_credit']:.2f}")
        
        return position
    
    async def close_position(
        self, 
        ticker: str, 
        reason: str
    ) -> bool:
        """Close an existing position"""
        if ticker not in self.positions:
            return False
        
        position = self.positions[ticker]
        profit = position.entry_credit - position.current_value
        
        print(f"Closing {ticker} Iron Condor - Reason: {reason}")
        print(f"  P/L: ${profit:.2f} per spread")
        
        position.status = PositionStatus.CLOSED if profit >= 0 else PositionStatus.STOPPED
        
        return True
    
    async def update_positions(self):
        """Update current values for all positions"""
        for ticker, position in list(self.positions.items()):
            if position.status != PositionStatus.OPEN:
                continue
            
            try:
                # Get current option prices
                options = await self.alpaca.get_options_chain(ticker)
                
                if not options:
                    continue
                
                # Calculate current iron condor value
                # (simplified - would need actual option prices)
                price_data = await self.alpaca.get_current_price(ticker)
                if price_data:
                    current_price = price_data['price']
                    
                    # Estimate position value based on price movement
                    # This is simplified - real implementation needs actual option prices
                    distance_call = position.short_call_strike - current_price
                    distance_put = current_price - position.short_put_strike
                    
                    # Rough estimate of position value
                    if distance_call < 0 or distance_put < 0:
                        # ITM - losing money
                        position.current_value = position.entry_credit * 2
                    else:
                        # OTM - theta decay
                        time_elapsed = (datetime.now() - position.entry_time).seconds / 3600
                        decay_factor = 1 - (time_elapsed / 6.5)  # Trading day hours
                        position.current_value = position.entry_credit * max(0.1, decay_factor)
                
            except Exception as e:
                print(f"Error updating {ticker}: {e}")
    
    async def run_loop(self, tickers: List[str]):
        """Main bot loop"""
        self.is_running = True
        print("Theta Eater Bot started")
        
        while self.is_running:
            try:
                # Update existing positions
                await self.update_positions()
                
                # Check exits
                for ticker, position in list(self.positions.items()):
                    if position.status != PositionStatus.OPEN:
                        continue
                    
                    should_exit, reason = self.should_exit(position)
                    if should_exit:
                        await self.close_position(ticker, reason)
                
                # Check entries
                if self.should_enter():
                    for ticker in tickers:
                        if ticker in self.positions:
                            continue
                        
                        price_data = await self.alpaca.get_current_price(ticker)
                        if price_data:
                            await self.enter_position(ticker, price_data['price'])
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Bot error: {e}")
                await asyncio.sleep(60)
        
        print("Theta Eater Bot stopped")
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        open_positions = [
            {
                'symbol': p.symbol,
                'entry_credit': p.entry_credit,
                'current_value': p.current_value,
                'pnl': p.entry_credit - p.current_value,
                'status': p.status.value
            }
            for p in self.positions.values()
        ]
        
        return {
            'is_running': self.is_running,
            'positions': open_positions,
            'config': self.config
        }
