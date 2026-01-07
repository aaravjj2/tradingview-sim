"""
AI Strategy Recommender
Uses multi-criteria analysis to recommend optimal options strategies
"""

from typing import Dict, List, Optional
from datetime import datetime
import math


class StrategyRecommender:
    """
    AI-powered Options Strategy Recommender
    
    Analyzes market conditions and recommends strategies based on:
    - IV Rank/Percentile
    - Price trend & momentum
    - Days to expiration
    - Account risk tolerance
    - Market regime (bullish/bearish/neutral)
    """
    
    # Strategy definitions with criteria
    STRATEGIES = {
        "long_call": {
            "name": "Long Call",
            "bias": "bullish",
            "iv_preference": "low",  # Buy when IV is low
            "max_risk": "defined",
            "reward": "unlimited",
            "best_for": "Strong upward move expected",
            "avoid_when": "High IV, sideways market"
        },
        "long_put": {
            "name": "Long Put",
            "bias": "bearish",
            "iv_preference": "low",
            "max_risk": "defined",
            "reward": "substantial", 
            "best_for": "Strong downward move expected",
            "avoid_when": "High IV, uptrend"
        },
        "covered_call": {
            "name": "Covered Call",
            "bias": "neutral_bullish",
            "iv_preference": "high",
            "max_risk": "stock_decline",
            "reward": "limited",
            "best_for": "Generate income on existing position",
            "avoid_when": "Strong uptrend expected"
        },
        "cash_secured_put": {
            "name": "Cash Secured Put",
            "bias": "bullish",
            "iv_preference": "high",
            "max_risk": "stock_assignment",
            "reward": "limited",
            "best_for": "Want to own stock at lower price",
            "avoid_when": "Bearish outlook"
        },
        "iron_condor": {
            "name": "Iron Condor",
            "bias": "neutral",
            "iv_preference": "high",
            "max_risk": "defined",
            "reward": "limited",
            "best_for": "Low volatility, range-bound",
            "avoid_when": "Expected big move, low IV"
        },
        "straddle": {
            "name": "Long Straddle",
            "bias": "neutral_volatile",
            "iv_preference": "low",
            "max_risk": "defined",
            "reward": "unlimited",
            "best_for": "Big move expected either direction",
            "avoid_when": "High IV, time decay concern"
        },
        "strangle": {
            "name": "Long Strangle", 
            "bias": "neutral_volatile",
            "iv_preference": "low",
            "max_risk": "defined",
            "reward": "unlimited",
            "best_for": "Big move expected, cheaper than straddle",
            "avoid_when": "High IV"
        },
        "bull_call_spread": {
            "name": "Bull Call Spread",
            "bias": "moderately_bullish",
            "iv_preference": "neutral",
            "max_risk": "defined",
            "reward": "limited",
            "best_for": "Moderate upside, reduce cost",
            "avoid_when": "Strong move expected"
        },
        "bear_put_spread": {
            "name": "Bear Put Spread",
            "bias": "moderately_bearish",
            "iv_preference": "neutral",
            "max_risk": "defined",
            "reward": "limited",
            "best_for": "Moderate downside expected",
            "avoid_when": "Strong uptrend"
        },
        "butterfly": {
            "name": "Long Butterfly",
            "bias": "neutral",
            "iv_preference": "high",
            "max_risk": "defined",
            "reward": "limited",
            "best_for": "Pin at specific price",
            "avoid_when": "High volatility expected"
        },
        "calendar_spread": {
            "name": "Calendar Spread",
            "bias": "neutral",
            "iv_preference": "low_near_high_far",
            "max_risk": "defined",
            "reward": "limited",
            "best_for": "Volatility increase expected",
            "avoid_when": "IV crush expected"
        },
        "jade_lizard": {
            "name": "Jade Lizard",
            "bias": "neutral_bullish",
            "iv_preference": "high",
            "max_risk": "downside_only",
            "reward": "limited",
            "best_for": "Collect premium, no upside risk",
            "avoid_when": "Strong bearish move expected"
        }
    }
    
    def __init__(self):
        self.analysis_history: List[Dict] = []
    
    def analyze_market_conditions(
        self,
        current_price: float,
        iv_rank: float,  # 0-100
        iv_percentile: float,  # 0-100
        hv_20: float,  # 20-day historical vol
        price_change_5d: float,  # 5-day % change
        price_change_20d: float,  # 20-day % change
        rsi: float = 50,  # Relative Strength Index
        vix: float = 20
    ) -> Dict:
        """Analyze current market conditions"""
        
        # Determine trend
        if price_change_20d > 5 and price_change_5d > 2:
            trend = "strong_bullish"
        elif price_change_20d > 2:
            trend = "bullish"
        elif price_change_20d < -5 and price_change_5d < -2:
            trend = "strong_bearish"
        elif price_change_20d < -2:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # IV assessment
        if iv_rank > 70:
            iv_level = "high"
        elif iv_rank < 30:
            iv_level = "low"
        else:
            iv_level = "neutral"
        
        # Volatility assessment
        iv_hv_ratio = iv_percentile / (hv_20 * 100 + 0.001)
        if iv_hv_ratio > 1.3:
            vol_premium = "expensive"
        elif iv_hv_ratio < 0.8:
            vol_premium = "cheap"
        else:
            vol_premium = "fair"
        
        # Market regime
        if vix > 30:
            regime = "high_fear"
        elif vix < 15:
            regime = "complacent"
        else:
            regime = "normal"
        
        return {
            "trend": trend,
            "iv_level": iv_level,
            "iv_rank": iv_rank,
            "iv_percentile": iv_percentile,
            "vol_premium": vol_premium,
            "iv_hv_ratio": round(iv_hv_ratio, 2),
            "regime": regime,
            "rsi": rsi,
            "overbought": rsi > 70,
            "oversold": rsi < 30
        }
    
    def score_strategy(
        self,
        strategy_key: str,
        conditions: Dict,
        days_to_expiry: int = 30,
        risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    ) -> Dict:
        """Score a strategy based on current conditions"""
        strategy = self.STRATEGIES.get(strategy_key)
        if not strategy:
            return {"score": 0, "reasons": ["Unknown strategy"]}
        
        score = 50  # Base score
        reasons = []
        warnings = []
        
        # IV preference scoring
        iv_level = conditions["iv_level"]
        iv_pref = strategy["iv_preference"]
        
        if iv_pref == "low" and iv_level == "low":
            score += 20
            reasons.append("✅ Low IV is ideal for buying options")
        elif iv_pref == "low" and iv_level == "high":
            score -= 25
            warnings.append("⚠️ High IV makes buying expensive")
        elif iv_pref == "high" and iv_level == "high":
            score += 20
            reasons.append("✅ High IV is ideal for selling premium")
        elif iv_pref == "high" and iv_level == "low":
            score -= 20
            warnings.append("⚠️ Low IV reduces premium collected")
        
        # Trend alignment
        bias = strategy["bias"]
        trend = conditions["trend"]
        
        if bias in ["bullish", "moderately_bullish"] and trend in ["bullish", "strong_bullish"]:
            score += 15
            reasons.append("✅ Bullish bias aligns with uptrend")
        elif bias in ["bullish", "moderately_bullish"] and trend in ["bearish", "strong_bearish"]:
            score -= 20
            warnings.append("⚠️ Bullish strategy in downtrend")
        elif bias in ["bearish", "moderately_bearish"] and trend in ["bearish", "strong_bearish"]:
            score += 15
            reasons.append("✅ Bearish bias aligns with downtrend")
        elif bias in ["bearish", "moderately_bearish"] and trend in ["bullish", "strong_bullish"]:
            score -= 20
            warnings.append("⚠️ Bearish strategy in uptrend")
        elif bias == "neutral" and trend == "neutral":
            score += 10
            reasons.append("✅ Neutral strategy in range-bound market")
        elif bias == "neutral_volatile" and conditions["regime"] == "high_fear":
            score += 10
            reasons.append("✅ Volatility play in high VIX environment")
        
        # Risk tolerance adjustment
        if risk_tolerance == "conservative":
            if strategy["max_risk"] == "defined":
                score += 10
                reasons.append("✅ Defined risk suits conservative approach")
            else:
                score -= 15
                warnings.append("⚠️ Undefined risk for conservative investor")
        elif risk_tolerance == "aggressive":
            if strategy["reward"] == "unlimited":
                score += 5
                reasons.append("✅ Unlimited reward for aggressive approach")
        
        # Time decay concerns
        if days_to_expiry < 14 and iv_pref == "low":
            score -= 10
            warnings.append("⚠️ Short DTE with theta decay concern")
        
        # Cap score
        score = max(0, min(100, score))
        
        return {
            "strategy_key": strategy_key,
            "name": strategy["name"],
            "score": score,
            "grade": self._score_to_grade(score),
            "reasons": reasons,
            "warnings": warnings,
            "best_for": strategy["best_for"],
            "avoid_when": strategy["avoid_when"]
        }
    
    def _score_to_grade(self, score: int) -> str:
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "F"
    
    def recommend(
        self,
        ticker: str,
        current_price: float,
        iv_rank: float = 50,
        iv_percentile: float = 50,
        hv_20: float = 0.25,
        price_change_5d: float = 0,
        price_change_20d: float = 0,
        rsi: float = 50,
        vix: float = 20,
        days_to_expiry: int = 30,
        risk_tolerance: str = "moderate",
        top_n: int = 5
    ) -> Dict:
        """
        Get top strategy recommendations
        """
        # Analyze conditions
        conditions = self.analyze_market_conditions(
            current_price, iv_rank, iv_percentile, hv_20,
            price_change_5d, price_change_20d, rsi, vix
        )
        
        # Score all strategies
        scored = []
        for key in self.STRATEGIES:
            result = self.score_strategy(key, conditions, days_to_expiry, risk_tolerance)
            scored.append(result)
        
        # Sort by score
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        # Build recommendation
        top_picks = scored[:top_n]
        avoid = [s for s in scored if s["score"] < 35][:3]
        
        recommendation = {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            "market_conditions": conditions,
            "parameters": {
                "iv_rank": iv_rank,
                "days_to_expiry": days_to_expiry,
                "risk_tolerance": risk_tolerance
            },
            "top_strategies": top_picks,
            "avoid_strategies": avoid,
            "best_pick": {
                "strategy": top_picks[0]["name"],
                "score": top_picks[0]["score"],
                "grade": top_picks[0]["grade"],
                "reasoning": top_picks[0]["reasons"]
            }
        }
        
        self.analysis_history.append(recommendation)
        
        return recommendation


# API helpers
_recommender: Optional[StrategyRecommender] = None


def get_recommender() -> StrategyRecommender:
    global _recommender
    if _recommender is None:
        _recommender = StrategyRecommender()
    return _recommender


async def get_strategy_recommendation(
    ticker: str,
    current_price: float,
    iv_rank: float = 50,
    hv_20: float = 0.25,
    price_change_20d: float = 0,
    vix: float = 20,
    days_to_expiry: int = 30,
    risk_tolerance: str = "moderate"
) -> Dict:
    """API endpoint for strategy recommendations"""
    recommender = get_recommender()
    return recommender.recommend(
        ticker=ticker,
        current_price=current_price,
        iv_rank=iv_rank,
        iv_percentile=iv_rank,  # Use same for simplicity
        hv_20=hv_20,
        price_change_5d=price_change_20d / 4,  # Estimate
        price_change_20d=price_change_20d,
        vix=vix,
        days_to_expiry=days_to_expiry,
        risk_tolerance=risk_tolerance
    )
