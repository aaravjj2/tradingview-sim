"""
AI Council (Decision Engine)
3-Agent voting system for trade approval.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum
from abc import ABC, abstractmethod

from services.scanner import get_scanner, ActiveCandidate, SignalType
from services.sentiment import get_sentiment_engine, TickerSentiment
from services.regime_detector import get_regime_detector, MarketRegime
from services.alpaca import AlpacaService


class Vote(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class StrategyRecommendation(Enum):
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    CALL_SPREAD = "call_spread"
    PUT_SPREAD = "put_spread"
    IRON_CONDOR = "iron_condor"
    STRADDLE = "straddle"
    NO_TRADE = "no_trade"


@dataclass
class AgentVote:
    """Individual agent's vote and reasoning."""
    agent_name: str
    vote: Vote
    confidence: float  # 0-1
    reasoning: str
    factors: Dict[str, float]  # Key metrics that influenced the vote
    
    def to_dict(self) -> Dict:
        return {
            "agent": self.agent_name,
            "vote": self.vote.value,
            "confidence": round(self.confidence, 2),
            "reasoning": self.reasoning,
            "factors": {k: round(v, 2) if isinstance(v, float) else v for k, v in self.factors.items()}
        }


@dataclass
class CouncilDecision:
    """Aggregated decision from all agents."""
    ticker: str
    approved: bool
    yes_count: int
    no_count: int
    abstain_count: int
    strategy: StrategyRecommendation
    votes: List[AgentVote]
    reasoning_summary: str
    decided_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "approved": self.approved,
            "decision": "APPROVED" if self.approved else "REJECTED",
            "yes_count": self.yes_count,
            "no_count": self.no_count,
            "abstain_count": self.abstain_count,
            "strategy": self.strategy.value,
            "reasoning_summary": self.reasoning_summary,
            "votes": [v.to_dict() for v in self.votes],
            "decided_at": self.decided_at.isoformat()
        }


class BaseAgent(ABC):
    """Abstract base class for council agents."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    async def assess(self, ticker: str, context: Dict) -> AgentVote:
        """Assess a ticker and return a vote."""
        pass


class TechnicianAgent(BaseAgent):
    """
    Agent A: Technical Analysis
    Analyzes Price Action, RSI, Bollinger Bands, and trend indicators.
    """
    
    @property
    def name(self) -> str:
        return "Technician"
    
    def __init__(self):
        self.alpaca = AlpacaService()
    
    async def assess(self, ticker: str, context: Dict) -> AgentVote:
        """Assess based on technical indicators."""
        factors = {}
        reasons = []
        
        try:
            # Get historical data
            bars = await self.alpaca.get_historical_bars(ticker, "1Day", 30)
            if not bars or len(bars) < 14:
                return AgentVote(
                    agent_name=self.name,
                    vote=Vote.ABSTAIN,
                    confidence=0.3,
                    reasoning="Insufficient historical data",
                    factors={}
                )
            
            # Calculate RSI
            rsi = self._calculate_rsi(bars)
            factors["rsi"] = rsi
            
            # Calculate Bollinger Band position
            bb_position = self._calculate_bb_position(bars)
            factors["bb_position"] = bb_position
            
            # Calculate price momentum
            momentum = self._calculate_momentum(bars)
            factors["momentum_5d"] = momentum
            
            # Decision logic
            vote = Vote.ABSTAIN
            confidence = 0.5
            
            # Bullish signals
            bullish_signals = 0
            if rsi < 30:
                bullish_signals += 1
                reasons.append("RSI oversold (<30)")
            if bb_position < 0.2:
                bullish_signals += 1
                reasons.append("Price near lower Bollinger Band")
            if momentum > 0 and rsi > 50:
                bullish_signals += 1
                reasons.append("Positive momentum with RSI confirmation")
            
            # Bearish signals
            bearish_signals = 0
            if rsi > 70:
                bearish_signals += 1
                reasons.append("RSI overbought (>70)")
            if bb_position > 0.8:
                bearish_signals += 1
                reasons.append("Price near upper Bollinger Band")
            
            if bullish_signals >= 2:
                vote = Vote.YES
                confidence = 0.6 + bullish_signals * 0.1
                factors["signal_direction"] = "BULLISH"
            elif bearish_signals >= 2:
                vote = Vote.NO
                confidence = 0.6 + bearish_signals * 0.1
                factors["signal_direction"] = "BEARISH"
            else:
                reasons.append("No clear technical signal")
                factors["signal_direction"] = "NEUTRAL"
            
            return AgentVote(
                agent_name=self.name,
                vote=vote,
                confidence=min(confidence, 0.95),
                reasoning="; ".join(reasons) if reasons else "Mixed signals",
                factors=factors
            )
            
        except Exception as e:
            return AgentVote(
                agent_name=self.name,
                vote=Vote.ABSTAIN,
                confidence=0.2,
                reasoning=f"Technical analysis error: {str(e)[:50]}",
                factors={}
            )
    
    def _calculate_rsi(self, bars: List[Dict], period: int = 14) -> float:
        """Calculate RSI."""
        if len(bars) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(bars)):
            change = bars[i]["close"] - bars[i-1]["close"]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_bb_position(self, bars: List[Dict], period: int = 20) -> float:
        """Calculate where price is within Bollinger Bands (0 = lower, 1 = upper)."""
        if len(bars) < period:
            return 0.5
        
        closes = [b["close"] for b in bars[-period:]]
        current = closes[-1]
        
        sma = sum(closes) / period
        variance = sum((c - sma) ** 2 for c in closes) / period
        std = variance ** 0.5
        
        upper_band = sma + 2 * std
        lower_band = sma - 2 * std
        
        if upper_band == lower_band:
            return 0.5
        
        return (current - lower_band) / (upper_band - lower_band)
    
    def _calculate_momentum(self, bars: List[Dict], period: int = 5) -> float:
        """Calculate price momentum (% change over period)."""
        if len(bars) < period:
            return 0.0
        
        current = bars[-1]["close"]
        past = bars[-period]["close"]
        
        return ((current - past) / past) * 100 if past > 0 else 0.0


class FundamentalistAgent(BaseAgent):
    """
    Agent B: Fundamental Analysis
    Analyzes FinBERT News Sentiment and macro factors.
    """
    
    @property
    def name(self) -> str:
        return "Fundamentalist"
    
    def __init__(self):
        self.sentiment_engine = get_sentiment_engine()
    
    async def assess(self, ticker: str, context: Dict) -> AgentVote:
        """Assess based on sentiment and fundamentals."""
        factors = {}
        reasons = []
        
        try:
            # Get sentiment
            sentiment = await self.sentiment_engine.get_sentiment(ticker)
            factors["sentiment_score"] = sentiment.overall_score
            factors["headline_count"] = sentiment.headline_count
            factors["positive_ratio"] = sentiment.positive_count / max(sentiment.headline_count, 1)
            
            # Decision logic
            vote = Vote.ABSTAIN
            confidence = 0.5
            
            if sentiment.overall_score >= 0.5:
                vote = Vote.YES
                confidence = 0.6 + sentiment.overall_score * 0.3
                reasons.append(f"Strong bullish sentiment ({sentiment.overall_score:.2f})")
            elif sentiment.overall_score >= 0.2:
                vote = Vote.YES
                confidence = 0.55
                reasons.append(f"Moderately bullish sentiment ({sentiment.overall_score:.2f})")
            elif sentiment.overall_score <= -0.5:
                vote = Vote.NO
                confidence = 0.6 + abs(sentiment.overall_score) * 0.3
                reasons.append(f"Strong bearish sentiment ({sentiment.overall_score:.2f})")
            elif sentiment.overall_score <= -0.2:
                vote = Vote.NO
                confidence = 0.55
                reasons.append(f"Moderately bearish sentiment ({sentiment.overall_score:.2f})")
            else:
                reasons.append(f"Neutral sentiment ({sentiment.overall_score:.2f})")
            
            # Add headline context
            if sentiment.headline_count < 3:
                confidence *= 0.7
                reasons.append("Limited news coverage")
            
            return AgentVote(
                agent_name=self.name,
                vote=vote,
                confidence=min(confidence, 0.95),
                reasoning="; ".join(reasons),
                factors=factors
            )
            
        except Exception as e:
            return AgentVote(
                agent_name=self.name,
                vote=Vote.ABSTAIN,
                confidence=0.2,
                reasoning=f"Sentiment analysis error: {str(e)[:50]}",
                factors={}
            )


class RiskManagerAgent(BaseAgent):
    """
    Agent C: Risk Management
    Analyzes Portfolio Delta, VIX levels, and position sizing.
    """
    
    @property
    def name(self) -> str:
        return "RiskManager"
    
    def __init__(self):
        self.regime_detector = get_regime_detector()
        self.max_position_pct = 5.0  # Max 5% of portfolio per position
        self.max_daily_trades = 10
        self.daily_trade_count = 0
        self.daily_drawdown_limit = 2.0  # 2% max daily loss
    
    async def assess(self, ticker: str, context: Dict) -> AgentVote:
        """Assess risk factors before approving a trade."""
        factors = {}
        reasons = []
        
        try:
            # Check market regime
            regime = context.get("regime")
            if regime:
                factors["regime"] = regime.regime.value
                factors["vix"] = regime.vix
                
                if regime.regime == MarketRegime.CRASH:
                    return AgentVote(
                        agent_name=self.name,
                        vote=Vote.NO,
                        confidence=0.95,
                        reasoning="CRASH regime detected - all buying suspended",
                        factors=factors
                    )
                
                if regime.vix > 25:
                    reasons.append(f"Elevated VIX ({regime.vix:.1f})")
            
            # Check daily trade limit
            factors["daily_trades"] = self.daily_trade_count
            if self.daily_trade_count >= self.max_daily_trades:
                return AgentVote(
                    agent_name=self.name,
                    vote=Vote.NO,
                    confidence=0.9,
                    reasoning=f"Daily trade limit reached ({self.max_daily_trades})",
                    factors=factors
                )
            
            # Check portfolio concentration (would need real portfolio data)
            current_exposure = context.get("current_exposure_pct", 0)
            factors["current_exposure_pct"] = current_exposure
            
            if current_exposure > 80:
                return AgentVote(
                    agent_name=self.name,
                    vote=Vote.NO,
                    confidence=0.85,
                    reasoning="Portfolio near max exposure (>80%)",
                    factors=factors
                )
            
            # Check portfolio delta (would need real Greeks data)
            portfolio_delta = context.get("portfolio_delta", 0)
            factors["portfolio_delta"] = portfolio_delta
            
            if abs(portfolio_delta) > 500:
                reasons.append(f"High portfolio delta ({portfolio_delta:+.0f})")
            
            # Default: Approve with standard confidence
            vote = Vote.YES
            confidence = 0.7
            
            # Reduce confidence in elevated VIX
            if regime and regime.vix > 20:
                confidence -= 0.1
                reasons.append("Reduced confidence due to elevated volatility")
            
            if reasons:
                reasoning = "; ".join(reasons)
            else:
                reasoning = "Risk parameters within acceptable limits"
            
            return AgentVote(
                agent_name=self.name,
                vote=vote,
                confidence=confidence,
                reasoning=reasoning,
                factors=factors
            )
            
        except Exception as e:
            return AgentVote(
                agent_name=self.name,
                vote=Vote.ABSTAIN,
                confidence=0.2,
                reasoning=f"Risk assessment error: {str(e)[:50]}",
                factors={}
            )


class AICouncil:
    """
    The Council of Agents.
    
    Trade is approved if 2 out of 3 agents vote YES.
    """
    
    def __init__(self):
        self.technician = TechnicianAgent()
        self.fundamentalist = FundamentalistAgent()
        self.risk_manager = RiskManagerAgent()
        self.regime_detector = get_regime_detector()
        self.alpaca = AlpacaService()
        
        self.decision_history: List[CouncilDecision] = []
    
    async def vote(self, ticker: str, context: Optional[Dict] = None) -> CouncilDecision:
        """
        Convene the council to vote on a trade.
        
        Args:
            ticker: Stock symbol to evaluate
            context: Additional context (portfolio state, etc.)
            
        Returns:
            CouncilDecision with aggregated result
        """
        context = context or {}
        
        # Get current regime if not provided
        if "regime" not in context:
            try:
                bars = await self.alpaca.get_historical_bars("SPY", "1Day", 20)
                regime = self.regime_detector.detect(bars, vix=context.get("vix", 20))
                context["regime"] = regime
            except:
                context["regime"] = None
        
        # Gather votes from all agents
        votes = await asyncio.gather(
            self.technician.assess(ticker, context),
            self.fundamentalist.assess(ticker, context),
            self.risk_manager.assess(ticker, context)
        )
        
        # Count votes
        yes_count = sum(1 for v in votes if v.vote == Vote.YES)
        no_count = sum(1 for v in votes if v.vote == Vote.NO)
        abstain_count = sum(1 for v in votes if v.vote == Vote.ABSTAIN)
        
        # Decision: 2 of 3 must vote YES
        approved = yes_count >= 2
        
        # Determine strategy based on regime and signals
        strategy = self._recommend_strategy(votes, context)
        
        # Generate reasoning summary
        reasoning = self._generate_summary(votes, approved)
        
        decision = CouncilDecision(
            ticker=ticker,
            approved=approved,
            yes_count=yes_count,
            no_count=no_count,
            abstain_count=abstain_count,
            strategy=strategy,
            votes=votes,
            reasoning_summary=reasoning
        )
        
        self.decision_history.append(decision)
        
        # Keep only last 50 decisions
        if len(self.decision_history) > 50:
            self.decision_history = self.decision_history[-50:]
        
        return decision
    
    def _recommend_strategy(self, votes: List[AgentVote], context: Dict) -> StrategyRecommendation:
        """Recommend a strategy based on votes and regime."""
        regime = context.get("regime")
        
        # Check technician's signal direction
        tech_vote = next((v for v in votes if v.agent_name == "Technician"), None)
        signal_direction = tech_vote.factors.get("signal_direction", "NEUTRAL") if tech_vote else "NEUTRAL"
        
        if regime and regime.regime == MarketRegime.CRASH:
            return StrategyRecommendation.NO_TRADE
        
        if regime and regime.regime == MarketRegime.CHOPPY:
            return StrategyRecommendation.IRON_CONDOR
        
        if signal_direction == "BULLISH":
            return StrategyRecommendation.CALL_SPREAD
        elif signal_direction == "BEARISH":
            return StrategyRecommendation.PUT_SPREAD
        else:
            return StrategyRecommendation.IRON_CONDOR  # Default neutral strategy
    
    def _generate_summary(self, votes: List[AgentVote], approved: bool) -> str:
        """Generate a human-readable summary of the decision."""
        parts = []
        
        for vote in votes:
            status = "✅" if vote.vote == Vote.YES else "❌" if vote.vote == Vote.NO else "⏸️"
            parts.append(f"{status} {vote.agent_name}: {vote.reasoning[:50]}")
        
        result = "APPROVED" if approved else "REJECTED"
        return f"Decision: {result}. " + " | ".join(parts)
    
    def get_status(self) -> Dict:
        """Get council status summary."""
        return {
            "total_decisions": len(self.decision_history),
            "recent_decisions": [d.to_dict() for d in self.decision_history[-5:]],
            "approval_rate": sum(1 for d in self.decision_history if d.approved) / max(len(self.decision_history), 1)
        }


# Singleton
_council: Optional[AICouncil] = None

def get_council() -> AICouncil:
    """Get or create the global AI Council instance."""
    global _council
    if _council is None:
        _council = AICouncil()
    return _council
