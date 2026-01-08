"""
Market Scanner Service
Scans S&P 100 tickers for trade candidates based on volume, IV rank, and liquidity.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Literal, Optional, Dict
from enum import Enum

from services.alpaca import AlpacaService


class SignalType(Enum):
    IV_LOW = "iv_low"      # Cheap premium - good for buying
    IV_HIGH = "iv_high"    # Expensive premium - good for selling
    VOLUME_SPIKE = "volume_spike"
    MOMENTUM = "momentum"


@dataclass
class ActiveCandidate:
    """Represents a ticker that passed the scanner filters."""
    ticker: str
    current_price: float
    iv_rank: float
    volume_ratio: float  # Current volume / 20-day average
    signal_type: SignalType
    bid_ask_spread_pct: float
    score: float = 0.0  # Composite score for ranking
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "current_price": self.current_price,
            "iv_rank": self.iv_rank,
            "volume_ratio": round(self.volume_ratio, 2),
            "signal_type": self.signal_type.value,
            "bid_ask_spread_pct": round(self.bid_ask_spread_pct, 2),
            "score": round(self.score, 2),
            "timestamp": self.timestamp.isoformat()
        }


# S&P 100 Tickers (OEX) - Most liquid US equities
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK.B", "C",
    "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS",
    "CVX", "DE", "DHR", "DIS", "DOW", "DUK", "EMR", "EXC", "F", "FDX",
    "GD", "GE", "GILD", "GM", "GOOG", "GOOGL", "GS", "HD", "HON", "IBM",
    "INTC", "JNJ", "JPM", "KHC", "KO", "LIN", "LLY", "LMT", "LOW", "MA",
    "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT",
    "NEE", "NFLX", "NKE", "NVDA", "ORCL", "PEP", "PFE", "PG", "PM", "PYPL",
    "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS",
    "TSLA", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM"
]


class MarketScanner:
    """
    Scans the market for trade candidates.
    
    Filters:
    1. Volume > 1.5x 20-day average (unusual activity)
    2. IV Rank < 30 (cheap) OR > 70 (expensive)
    3. Bid/Ask spread < 3% (liquidity)
    """
    
    def __init__(self, alpaca_service: Optional[AlpacaService] = None):
        self.alpaca = alpaca_service or AlpacaService()
        self.candidates: List[ActiveCandidate] = []
        self.last_scan_time: Optional[datetime] = None
        self.scan_interval_seconds = 60
        
        # Filter thresholds
        self.min_volume_ratio = 1.5
        self.iv_low_threshold = 30
        self.iv_high_threshold = 70
        self.max_spread_pct = 3.0
    
    async def scan(self, tickers: Optional[List[str]] = None) -> List[ActiveCandidate]:
        """
        Scan specified tickers (or S&P 100) for candidates.
        
        Returns:
            List of ActiveCandidate objects sorted by score (descending).
        """
        tickers = tickers or SP100_TICKERS
        candidates = []
        
        # Process in batches to avoid rate limiting
        batch_size = 10
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self._analyze_ticker(ticker) for ticker in batch],
                return_exceptions=True
            )
            
            for result in batch_results:
                if isinstance(result, ActiveCandidate):
                    candidates.append(result)
            
            # Small delay between batches to be nice to API
            if i + batch_size < len(tickers):
                await asyncio.sleep(0.5)
        
        # Sort by score and cache results
        candidates.sort(key=lambda x: x.score, reverse=True)
        self.candidates = candidates
        self.last_scan_time = datetime.now()
        
        return candidates
    
    async def _analyze_ticker(self, ticker: str) -> Optional[ActiveCandidate]:
        """Analyze a single ticker for trade signals."""
        try:
            # Get current price and quote
            price_data = await self.alpaca.get_current_price(ticker)
            if not price_data:
                return None
            
            current_price = price_data["price"]
            bid = price_data.get("bid", current_price * 0.999)
            ask = price_data.get("ask", current_price * 1.001)
            
            # Calculate bid/ask spread percentage
            spread_pct = ((ask - bid) / current_price) * 100 if current_price > 0 else 999
            
            # Filter by liquidity
            if spread_pct > self.max_spread_pct:
                return None
            
            # Get historical bars for volume analysis
            bars = await self.alpaca.get_historical_bars(ticker, "1Day", 21)
            if len(bars) < 20:
                return None
            
            # Calculate volume ratio
            current_volume = bars[-1].get("volume", 0) if bars else 0
            avg_volume = sum(b.get("volume", 0) for b in bars[:-1]) / len(bars[:-1])
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Get IV and calculate IV Rank
            iv = await self.alpaca.get_implied_volatility(ticker, current_price)
            iv_rank = self._estimate_iv_rank(iv, ticker)
            
            # Determine signal type
            signal_type = None
            if volume_ratio >= self.min_volume_ratio:
                if iv_rank <= self.iv_low_threshold:
                    signal_type = SignalType.IV_LOW
                elif iv_rank >= self.iv_high_threshold:
                    signal_type = SignalType.IV_HIGH
                else:
                    signal_type = SignalType.VOLUME_SPIKE
            elif iv_rank <= self.iv_low_threshold:
                signal_type = SignalType.IV_LOW
            elif iv_rank >= self.iv_high_threshold:
                signal_type = SignalType.IV_HIGH
            
            if not signal_type:
                return None
            
            # Calculate composite score
            score = self._calculate_score(volume_ratio, iv_rank, spread_pct, signal_type)
            
            return ActiveCandidate(
                ticker=ticker,
                current_price=current_price,
                iv_rank=iv_rank,
                volume_ratio=volume_ratio,
                signal_type=signal_type,
                bid_ask_spread_pct=spread_pct,
                score=score
            )
            
        except Exception as e:
            print(f"Scanner error for {ticker}: {e}")
            return None
    
    def _estimate_iv_rank(self, current_iv: float, ticker: str) -> float:
        """
        Estimate IV Rank (0-100) based on typical ranges.
        
        In production, this would compare to 52-week IV high/low.
        For now, we use heuristic ranges.
        """
        # Typical IV ranges by sector (simplified)
        tech_tickers = {"AAPL", "MSFT", "GOOGL", "GOOG", "META", "AMZN", "NVDA", "AMD", "TSLA"}
        
        if ticker in tech_tickers:
            # Tech typically has IV between 20-60%
            iv_low, iv_high = 0.20, 0.60
        else:
            # Others typically 15-45%
            iv_low, iv_high = 0.15, 0.45
        
        # Calculate percentile rank
        if current_iv <= iv_low:
            return 0.0
        elif current_iv >= iv_high:
            return 100.0
        else:
            return ((current_iv - iv_low) / (iv_high - iv_low)) * 100
    
    def _calculate_score(
        self, 
        volume_ratio: float, 
        iv_rank: float, 
        spread_pct: float,
        signal_type: SignalType
    ) -> float:
        """
        Calculate composite score for ranking candidates.
        
        Higher score = more attractive candidate.
        """
        score = 0.0
        
        # Volume component (0-40 points)
        # More volume = higher conviction
        volume_score = min(volume_ratio / 3.0, 1.0) * 40
        score += volume_score
        
        # IV Rank component (0-40 points)
        # Extreme IV ranks are more interesting
        if signal_type == SignalType.IV_LOW:
            # Lower IV = better for buying premium
            iv_score = (30 - iv_rank) / 30 * 40
        elif signal_type == SignalType.IV_HIGH:
            # Higher IV = better for selling premium
            iv_score = (iv_rank - 70) / 30 * 40
        else:
            iv_score = 20  # Neutral
        score += max(0, iv_score)
        
        # Liquidity bonus (0-20 points)
        # Tighter spread = easier execution
        spread_score = max(0, (3.0 - spread_pct) / 3.0 * 20)
        score += spread_score
        
        return score
    
    def get_top_candidates(self, n: int = 5) -> List[ActiveCandidate]:
        """Get top N candidates from last scan."""
        return self.candidates[:n]
    
    def get_candidates_by_signal(self, signal_type: SignalType) -> List[ActiveCandidate]:
        """Filter candidates by signal type."""
        return [c for c in self.candidates if c.signal_type == signal_type]
    
    def get_status(self) -> Dict:
        """Get scanner status summary."""
        return {
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "total_candidates": len(self.candidates),
            "by_signal": {
                "iv_low": len(self.get_candidates_by_signal(SignalType.IV_LOW)),
                "iv_high": len(self.get_candidates_by_signal(SignalType.IV_HIGH)),
                "volume_spike": len(self.get_candidates_by_signal(SignalType.VOLUME_SPIKE)),
            },
            "top_5": [c.to_dict() for c in self.get_top_candidates(5)]
        }


# Singleton instance for use across the application
_scanner_instance: Optional[MarketScanner] = None

def get_scanner() -> MarketScanner:
    """Get or create the global scanner instance."""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = MarketScanner()
    return _scanner_instance
