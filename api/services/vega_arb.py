"""
Calendar Vega Arbitrage Scanner
Finds stocks with low IV Rank for calendar spread opportunities
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class CalendarOpportunity:
    """Represents a calendar spread opportunity"""
    ticker: str
    iv_rank: float
    front_month_iv: float
    back_month_iv: float
    iv_term_structure: str  # 'contango' or 'backwardation'
    strike: float
    net_debit: float
    max_profit_estimate: float
    vega_exposure: float
    days_to_front: int
    days_to_back: int
    score: float


class VegaArbScanner:
    """
    Scans for calendar spread opportunities based on:
    1. Low IV Rank (< 5) - Options are cheap
    2. Contango in term structure - Back month IV > Front month IV
    3. Reasonable vega exposure
    """
    
    def __init__(self, alpaca_service):
        self.alpaca = alpaca_service
        self.iv_cache: Dict[str, Dict] = {}
        
        # Watchlist of liquid stocks for scanning
        self.watchlist = [
            'SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
            'NVDA', 'TSLA', 'AMD', 'NFLX', 'DIS', 'BA', 'JPM', 'GS',
            'XLF', 'XLE', 'XLK', 'XLV', 'GLD', 'SLV', 'TLT'
        ]
        
        self.config = {
            'max_iv_rank': 15,  # Only scan stocks with IV Rank < 15
            'min_iv_rank': 0,
            'min_term_spread': 0.02,  # Back IV - Front IV > 2%
            'min_vega': 0.05,
            'max_debit': 5.00,  # Max $5 per spread
            'front_dte_range': (21, 35),  # 3-5 weeks
            'back_dte_range': (45, 75),   # 6-10 weeks
        }
    
    def calculate_iv_rank(
        self, 
        current_iv: float, 
        iv_history: List[float]
    ) -> float:
        """
        Calculate IV Rank (percentile of current IV vs 52-week range)
        
        IV Rank = (Current IV - 52wk Low) / (52wk High - 52wk Low) * 100
        """
        if not iv_history or len(iv_history) < 20:
            return 50.0  # Default to middle
        
        iv_low = min(iv_history)
        iv_high = max(iv_history)
        
        if iv_high == iv_low:
            return 50.0
        
        rank = (current_iv - iv_low) / (iv_high - iv_low) * 100
        return max(0, min(100, rank))
    
    def estimate_calendar_value(
        self,
        front_iv: float,
        back_iv: float,
        front_dte: int,
        back_dte: int,
        current_price: float,
        strike: float
    ) -> Dict:
        """
        Estimate calendar spread value and Greeks
        
        Uses simplified Black-Scholes approximation
        """
        # Simplified vega calculation
        front_vega = 0.01 * current_price * np.sqrt(front_dte / 365)
        back_vega = 0.01 * current_price * np.sqrt(back_dte / 365)
        
        # Net vega (long back, short front)
        net_vega = back_vega - front_vega
        
        # Estimate premiums (very simplified)
        front_premium = front_iv * current_price * np.sqrt(front_dte / 365) * 0.4
        back_premium = back_iv * current_price * np.sqrt(back_dte / 365) * 0.4
        
        # Moneyness adjustment
        moneyness = abs(strike - current_price) / current_price
        otm_discount = np.exp(-10 * moneyness ** 2)
        
        front_premium *= otm_discount
        back_premium *= otm_discount
        
        net_debit = back_premium - front_premium
        
        # Max profit estimate (when front expires worthless and back retains value)
        max_profit = front_premium  # Approximately
        
        return {
            'front_premium': front_premium,
            'back_premium': back_premium,
            'net_debit': net_debit,
            'net_vega': net_vega,
            'max_profit': max_profit,
            'vega_dollars': net_vega * 100  # Per 1% IV move
        }
    
    async def scan_ticker(
        self, 
        ticker: str, 
        current_price: Optional[float] = None
    ) -> Optional[CalendarOpportunity]:
        """
        Scan a single ticker for calendar opportunities
        """
        try:
            # Get current price if not provided
            if current_price is None:
                price_data = await self.alpaca.get_current_price(ticker)
                if not price_data:
                    return None
                current_price = price_data['price']
            
            # Get options chain
            options = await self.alpaca.get_options_chain(ticker)
            if not options or not options.get('calls'):
                return None
            
            calls = options['calls']
            
            # Find ATM strike
            atm_strike = round(current_price / 5) * 5  # Round to nearest $5
            
            # Get IVs for different expirations
            front_options = [c for c in calls 
                           if abs(c['strike'] - atm_strike) < 3
                           and self.config['front_dte_range'][0] <= self._get_dte(c) <= self.config['front_dte_range'][1]]
            
            back_options = [c for c in calls
                          if abs(c['strike'] - atm_strike) < 3
                          and self.config['back_dte_range'][0] <= self._get_dte(c) <= self.config['back_dte_range'][1]]
            
            if not front_options or not back_options:
                return None
            
            # Get best front and back month options
            front = min(front_options, key=lambda x: abs(x['strike'] - atm_strike))
            back = min(back_options, key=lambda x: abs(x['strike'] - atm_strike))
            
            front_iv = front.get('iv', 0.25)
            back_iv = back.get('iv', 0.25)
            front_dte = self._get_dte(front)
            back_dte = self._get_dte(back)
            
            # Calculate IV Rank (using cached history or mock)
            iv_history = self._get_iv_history(ticker)
            current_iv = (front_iv + back_iv) / 2
            iv_rank = self.calculate_iv_rank(current_iv, iv_history)
            
            # Check if meets criteria
            if iv_rank > self.config['max_iv_rank']:
                return None
            
            # Check term structure
            iv_spread = back_iv - front_iv
            term_structure = 'contango' if iv_spread > 0 else 'backwardation'
            
            if iv_spread < self.config['min_term_spread']:
                return None
            
            # Estimate calendar value
            values = self.estimate_calendar_value(
                front_iv, back_iv, front_dte, back_dte,
                current_price, atm_strike
            )
            
            if values['net_debit'] > self.config['max_debit']:
                return None
            
            # Calculate opportunity score
            score = self._calculate_score(iv_rank, iv_spread, values['net_vega'])
            
            return CalendarOpportunity(
                ticker=ticker,
                iv_rank=iv_rank,
                front_month_iv=front_iv,
                back_month_iv=back_iv,
                iv_term_structure=term_structure,
                strike=atm_strike,
                net_debit=values['net_debit'],
                max_profit_estimate=values['max_profit'],
                vega_exposure=values['net_vega'],
                days_to_front=front_dte,
                days_to_back=back_dte,
                score=score
            )
            
        except Exception as e:
            print(f"Error scanning {ticker}: {e}")
            return None
    
    def _get_dte(self, option: Dict) -> int:
        """Calculate days to expiration"""
        exp_str = option.get('expiration', '')
        if not exp_str:
            return 30
        
        try:
            exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
            return (exp_date - datetime.now()).days
        except:
            return 30
    
    def _get_iv_history(self, ticker: str) -> List[float]:
        """Get historical IV data (mock for now)"""
        # In production, would fetch from database
        base_iv = 0.25 + np.random.uniform(-0.05, 0.05)
        return [base_iv + np.random.uniform(-0.10, 0.10) for _ in range(252)]
    
    def _calculate_score(
        self, 
        iv_rank: float, 
        iv_spread: float, 
        vega: float
    ) -> float:
        """Calculate opportunity score (0-100)"""
        # Lower IV rank is better
        rank_score = (100 - iv_rank) / 100 * 40
        
        # Higher IV spread is better
        spread_score = min(iv_spread * 500, 30)
        
        # Higher vega is better
        vega_score = min(vega * 200, 30)
        
        return rank_score + spread_score + vega_score
    
    async def scan_all(self) -> List[CalendarOpportunity]:
        """Scan all tickers in watchlist"""
        opportunities = []
        
        for ticker in self.watchlist:
            opp = await self.scan_ticker(ticker)
            if opp:
                opportunities.append(opp)
        
        # Sort by score descending
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        return opportunities
    
    def get_recommendation(
        self, 
        opportunities: List[CalendarOpportunity]
    ) -> Optional[Dict]:
        """Get top recommendation with trade details"""
        if not opportunities:
            return None
        
        top = opportunities[0]
        
        return {
            'ticker': top.ticker,
            'strategy': 'Calendar Spread',
            'reasoning': f"IV Rank at {top.iv_rank:.1f}% (cheap options). "
                        f"Term structure in {top.iv_term_structure}. "
                        f"Vega exposure: {top.vega_exposure:.4f}",
            'trade': {
                'sell': f"-1 {top.ticker} {top.days_to_front}DTE ${top.strike}C",
                'buy': f"+1 {top.ticker} {top.days_to_back}DTE ${top.strike}C",
                'net_debit': top.net_debit,
                'max_profit': top.max_profit_estimate
            },
            'score': top.score,
            'iv_details': {
                'rank': top.iv_rank,
                'front_iv': top.front_month_iv,
                'back_iv': top.back_month_iv
            }
        }
