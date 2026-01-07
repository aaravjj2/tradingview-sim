"""
Whale Alert Tracker
Detects unusual options activity and large block trades
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class WhaleAlert:
    """Represents a whale alert event"""
    timestamp: datetime
    ticker: str
    alert_type: str  # 'unusual_volume', 'large_block', 'sweep', 'dark_pool'
    details: str
    premium: float
    contracts: int
    strike: float
    expiration: str
    is_call: bool
    sentiment: str  # 'bullish', 'bearish', 'neutral'
    score: float  # Alert significance score


class WhaleTracker:
    """
    Tracks and alerts on unusual options activity:
    
    1. Unusual Volume: Volume > 3x average
    2. Large Blocks: Single trades > $100k premium
    3. Sweeps: Hitting multiple exchanges rapidly
    4. Dark Pool: Large equity blocks
    """
    
    def __init__(self, alpaca_service=None):
        self.alpaca = alpaca_service
        self.alerts: List[WhaleAlert] = []
        self.volume_baselines: Dict[str, float] = {}
        
        # Configuration
        self.config = {
            'volume_threshold': 3.0,  # 3x average volume
            'min_premium': 50000,  # $50k minimum for alerts
            'block_threshold': 100000,  # $100k for large block
            'sweep_threshold': 5,  # 5+ exchanges hit
        }
    
    async def scan_ticker(self, ticker: str) -> List[WhaleAlert]:
        """Scan a single ticker for whale activity"""
        alerts = []
        
        if not self.alpaca:
            # Generate mock alerts for demo
            return self._generate_mock_alerts(ticker)
        
        try:
            # Get options chain with volume data
            options = await self.alpaca.get_options_chain(ticker)
            if not options:
                return alerts
            
            # Get current price
            price_data = await self.alpaca.get_current_price(ticker)
            current_price = price_data['price'] if price_data else 0
            
            # Check calls
            for opt in options.get('calls', []):
                alert = self._analyze_option(opt, ticker, current_price, is_call=True)
                if alert:
                    alerts.append(alert)
            
            # Check puts
            for opt in options.get('puts', []):
                alert = self._analyze_option(opt, ticker, current_price, is_call=False)
                if alert:
                    alerts.append(alert)
            
        except Exception as e:
            print(f"Error scanning {ticker}: {e}")
        
        return alerts
    
    def _analyze_option(
        self, 
        option: Dict, 
        ticker: str, 
        current_price: float,
        is_call: bool
    ) -> Optional[WhaleAlert]:
        """Analyze a single option for unusual activity"""
        volume = option.get('volume', 0)
        open_interest = option.get('open_interest', 1)
        strike = option.get('strike', 0)
        premium = option.get('last', 0) * 100 * volume
        avg_volume = option.get('avg_volume', volume / 3)  # Fallback
        
        if avg_volume == 0:
            avg_volume = 1
        
        # Check for unusual volume
        volume_ratio = volume / avg_volume
        
        if volume_ratio < self.config['volume_threshold'] and premium < self.config['min_premium']:
            return None
        
        # Determine sentiment
        if is_call:
            sentiment = 'bullish' if strike > current_price else 'neutral'
        else:
            sentiment = 'bearish' if strike < current_price else 'neutral'
        
        # Determine alert type
        if premium >= self.config['block_threshold']:
            alert_type = 'large_block'
        elif volume_ratio >= self.config['volume_threshold']:
            alert_type = 'unusual_volume'
        else:
            alert_type = 'activity'
        
        # Calculate score
        score = (volume_ratio * 20) + (premium / 10000) + (10 if volume > open_interest else 0)
        
        return WhaleAlert(
            timestamp=datetime.now(),
            ticker=ticker,
            alert_type=alert_type,
            details=f"{volume:,} contracts @ ${option.get('last', 0):.2f} ({volume_ratio:.1f}x avg)",
            premium=premium,
            contracts=volume,
            strike=strike,
            expiration=option.get('expiration', ''),
            is_call=is_call,
            sentiment=sentiment,
            score=score
        )
    
    def _generate_mock_alerts(self, ticker: str) -> List[WhaleAlert]:
        """Generate mock alerts for demo purposes"""
        alerts = []
        
        # Random mock data
        mock_data = [
            {
                'type': 'large_block',
                'premium': 250000,
                'contracts': 500,
                'strike_mult': 1.05,
                'is_call': True,
                'sentiment': 'bullish',
            },
            {
                'type': 'unusual_volume',
                'premium': 75000,
                'contracts': 2500,
                'strike_mult': 0.95,
                'is_call': False,
                'sentiment': 'bearish',
            },
            {
                'type': 'sweep',
                'premium': 150000,
                'contracts': 1200,
                'strike_mult': 1.02,
                'is_call': True,
                'sentiment': 'bullish',
            },
        ]
        
        # Generate 1-3 random alerts
        num_alerts = np.random.randint(1, 4)
        
        for i in range(num_alerts):
            data = mock_data[i % len(mock_data)]
            base_price = 500  # Fallback price
            
            alerts.append(WhaleAlert(
                timestamp=datetime.now() - timedelta(minutes=np.random.randint(1, 60)),
                ticker=ticker,
                alert_type=data['type'],
                details=f"{data['contracts']:,} contracts ({np.random.uniform(3, 10):.1f}x avg vol)",
                premium=data['premium'] * np.random.uniform(0.8, 1.2),
                contracts=data['contracts'],
                strike=base_price * data['strike_mult'],
                expiration=(datetime.now() + timedelta(days=np.random.randint(7, 45))).strftime('%Y-%m-%d'),
                is_call=data['is_call'],
                sentiment=data['sentiment'],
                score=np.random.uniform(50, 100)
            ))
        
        return sorted(alerts, key=lambda x: x.score, reverse=True)
    
    def format_alerts(self, alerts: List[WhaleAlert]) -> List[Dict]:
        """Format alerts for API response"""
        return [
            {
                'timestamp': alert.timestamp.isoformat(),
                'ticker': alert.ticker,
                'type': alert.alert_type,
                'details': alert.details,
                'premium': alert.premium,
                'contracts': alert.contracts,
                'strike': alert.strike,
                'expiration': alert.expiration,
                'option_type': 'CALL' if alert.is_call else 'PUT',
                'sentiment': alert.sentiment,
                'score': alert.score,
                'color': 'green' if alert.sentiment == 'bullish' else 'red' if alert.sentiment == 'bearish' else 'gray'
            }
            for alert in alerts
        ]
    
    async def get_top_alerts(
        self, 
        tickers: List[str],
        limit: int = 10
    ) -> List[Dict]:
        """Get top whale alerts across multiple tickers"""
        all_alerts = []
        
        for ticker in tickers:
            alerts = await self.scan_ticker(ticker)
            all_alerts.extend(alerts)
        
        # Sort by score and limit
        all_alerts.sort(key=lambda x: x.score, reverse=True)
        top_alerts = all_alerts[:limit]
        
        return self.format_alerts(top_alerts)
