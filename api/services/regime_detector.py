"""
Regime Detector
Classifies market conditions as TRENDING, CHOPPY, or CRASH to optimize strategy selection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math


class MarketRegime(Enum):
    TRENDING = "trending"    # Strong directional movement - favor Momentum
    CHOPPY = "choppy"        # Range-bound, sideways - favor Theta strategies
    CRASH = "crash"          # High volatility, sharp decline - Cash/Hedges only


@dataclass
class RegimeAnalysis:
    """Result of regime detection."""
    regime: MarketRegime
    confidence: float  # 0-1 how confident in the classification
    adx: float  # Average Directional Index
    vix: float  # Volatility Index
    rsi: float  # Relative Strength Index
    price_range_pct: float  # Recent price range as % of price
    trend_direction: Optional[str]  # "UP", "DOWN", or None
    recommended_strategy: str
    reasoning: str
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "regime": self.regime.value,
            "confidence": round(self.confidence, 2),
            "adx": round(self.adx, 1),
            "vix": round(self.vix, 1),
            "rsi": round(self.rsi, 1),
            "price_range_pct": round(self.price_range_pct, 2),
            "trend_direction": self.trend_direction,
            "recommended_strategy": self.recommended_strategy,
            "reasoning": self.reasoning,
            "analyzed_at": self.analyzed_at.isoformat()
        }


# Strategy recommendations by regime
REGIME_STRATEGIES = {
    MarketRegime.TRENDING: {
        "primary": "Gamma Scalping",
        "secondary": "Momentum Breakout",
        "avoid": "Iron Condors"
    },
    MarketRegime.CHOPPY: {
        "primary": "Iron Condor",
        "secondary": "Put Credit Spreads", 
        "avoid": "Directional Bets"
    },
    MarketRegime.CRASH: {
        "primary": "Cash / Capital Preservation",
        "secondary": "Protective Puts",
        "avoid": "All Selling Strategies"
    }
}


class RegimeDetector:
    """
    Detects current market regime using technical indicators.
    
    Classification Logic:
    - CRASH: VIX > 30 OR SPY down > 3% intraday
    - TRENDING: ADX > 25 AND clear directional bias
    - CHOPPY: ADX < 20 AND price oscillating in narrow range
    """
    
    def __init__(self):
        self.current_regime: Optional[RegimeAnalysis] = None
        self.history: List[RegimeAnalysis] = []
        
        # Thresholds
        self.vix_crash_threshold = 30
        self.vix_elevated_threshold = 25
        self.adx_trending_threshold = 25
        self.adx_choppy_threshold = 20
        self.intraday_crash_pct = 3.0  # 3% drop = crash
    
    def detect(
        self,
        spy_bars: List[Dict],
        vix: float,
        intraday_change_pct: Optional[float] = None
    ) -> RegimeAnalysis:
        """
        Analyze market conditions and classify the regime.
        
        Args:
            spy_bars: Recent OHLCV bars for SPY (at least 14 bars)
            vix: Current VIX level
            intraday_change_pct: Optional intraday % change
            
        Returns:
            RegimeAnalysis with classification and metadata
        """
        # Calculate technical indicators
        adx = self._calculate_adx(spy_bars)
        rsi = self._calculate_rsi(spy_bars)
        price_range_pct = self._calculate_price_range(spy_bars)
        trend = self._detect_trend_direction(spy_bars)
        
        # Classification logic
        regime, confidence, reasoning = self._classify(
            adx=adx,
            vix=vix,
            rsi=rsi,
            price_range_pct=price_range_pct,
            intraday_change_pct=intraday_change_pct
        )
        
        # Get recommended strategy
        recommended = REGIME_STRATEGIES[regime]["primary"]
        
        analysis = RegimeAnalysis(
            regime=regime,
            confidence=confidence,
            adx=adx,
            vix=vix,
            rsi=rsi,
            price_range_pct=price_range_pct,
            trend_direction=trend,
            recommended_strategy=recommended,
            reasoning=reasoning
        )
        
        # Cache result
        self.current_regime = analysis
        self.history.append(analysis)
        
        # Keep only last 100 entries
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return analysis
    
    def _classify(
        self,
        adx: float,
        vix: float,
        rsi: float,
        price_range_pct: float,
        intraday_change_pct: Optional[float]
    ) -> Tuple[MarketRegime, float, str]:
        """
        Core classification logic.
        
        Returns: (regime, confidence, reasoning)
        """
        reasons = []
        
        # Priority 1: Check for CRASH conditions
        if vix > self.vix_crash_threshold:
            reasons.append(f"VIX elevated at {vix:.1f} (threshold: {self.vix_crash_threshold})")
            return MarketRegime.CRASH, 0.9, "; ".join(reasons)
        
        if intraday_change_pct is not None and intraday_change_pct <= -self.intraday_crash_pct:
            reasons.append(f"Sharp intraday decline: {intraday_change_pct:.1f}%")
            return MarketRegime.CRASH, 0.95, "; ".join(reasons)
        
        # Priority 2: Check for TRENDING
        if adx >= self.adx_trending_threshold:
            confidence = min(0.7 + (adx - 25) / 50, 0.95)
            reasons.append(f"Strong trend (ADX={adx:.1f})")
            
            if rsi > 70:
                reasons.append("RSI overbought (>70)")
            elif rsi < 30:
                reasons.append("RSI oversold (<30)")
            
            return MarketRegime.TRENDING, confidence, "; ".join(reasons)
        
        # Priority 3: Check for CHOPPY
        if adx < self.adx_choppy_threshold:
            confidence = 0.6 + (20 - adx) / 40
            reasons.append(f"Weak trend (ADX={adx:.1f})")
            reasons.append(f"Price range: {price_range_pct:.1f}%")
            return MarketRegime.CHOPPY, confidence, "; ".join(reasons)
        
        # Default: Transitional state, lean choppy
        reasons.append(f"Transitional (ADX={adx:.1f} between thresholds)")
        return MarketRegime.CHOPPY, 0.5, "; ".join(reasons)
    
    def _calculate_adx(self, bars: List[Dict], period: int = 14) -> float:
        """
        Calculate Average Directional Index.
        
        ADX measures trend strength (not direction).
        - ADX > 25: Strong trend
        - ADX < 20: Weak trend / ranging
        """
        if len(bars) < period + 1:
            return 20.0  # Default to neutral
        
        try:
            # Calculate True Range and Directional Movement
            tr_list = []
            plus_dm_list = []
            minus_dm_list = []
            
            for i in range(1, len(bars)):
                high = bars[i]["high"]
                low = bars[i]["low"]
                close_prev = bars[i-1]["close"]
                high_prev = bars[i-1]["high"]
                low_prev = bars[i-1]["low"]
                
                # True Range
                tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
                tr_list.append(tr)
                
                # Directional Movement
                up_move = high - high_prev
                down_move = low_prev - low
                
                plus_dm = up_move if up_move > down_move and up_move > 0 else 0
                minus_dm = down_move if down_move > up_move and down_move > 0 else 0
                
                plus_dm_list.append(plus_dm)
                minus_dm_list.append(minus_dm)
            
            # Smooth with EMA
            def ema(data, period):
                if len(data) < period:
                    return sum(data) / len(data) if data else 0
                alpha = 2 / (period + 1)
                result = sum(data[:period]) / period
                for val in data[period:]:
                    result = alpha * val + (1 - alpha) * result
                return result
            
            atr = ema(tr_list[-period*2:], period)
            plus_di = 100 * ema(plus_dm_list[-period*2:], period) / atr if atr > 0 else 0
            minus_di = 100 * ema(minus_dm_list[-period*2:], period) / atr if atr > 0 else 0
            
            # Calculate DX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
            
            # ADX is smoothed DX (simplified here)
            return max(0, min(dx, 100))
            
        except Exception as e:
            print(f"ADX calculation error: {e}")
            return 20.0
    
    def _calculate_rsi(self, bars: List[Dict], period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(bars) < period + 1:
            return 50.0
        
        try:
            gains = []
            losses = []
            
            for i in range(1, len(bars)):
                change = bars[i]["close"] - bars[i-1]["close"]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            # Use last 'period' values
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return max(0, min(rsi, 100))
            
        except Exception as e:
            print(f"RSI calculation error: {e}")
            return 50.0
    
    def _calculate_price_range(self, bars: List[Dict], lookback: int = 10) -> float:
        """Calculate price range as percentage of current price."""
        if len(bars) < lookback:
            return 2.0
        
        recent = bars[-lookback:]
        high = max(b["high"] for b in recent)
        low = min(b["low"] for b in recent)
        close = recent[-1]["close"]
        
        if close == 0:
            return 2.0
        
        return ((high - low) / close) * 100
    
    def _detect_trend_direction(self, bars: List[Dict]) -> Optional[str]:
        """Detect trend direction using simple moving averages."""
        if len(bars) < 20:
            return None
        
        # Compare short vs long MA
        closes = [b["close"] for b in bars]
        ma_short = sum(closes[-5:]) / 5
        ma_long = sum(closes[-20:]) / 20
        
        diff_pct = ((ma_short - ma_long) / ma_long) * 100
        
        if diff_pct > 0.5:
            return "UP"
        elif diff_pct < -0.5:
            return "DOWN"
        else:
            return None
    
    def get_status(self) -> Dict:
        """Get current regime status."""
        if not self.current_regime:
            return {"regime": "UNKNOWN", "message": "No analysis performed yet"}
        
        return self.current_regime.to_dict()


# Singleton
_detector: Optional[RegimeDetector] = None

def get_regime_detector() -> RegimeDetector:
    """Get or create the global regime detector instance."""
    global _detector
    if _detector is None:
        _detector = RegimeDetector()
    return _detector
