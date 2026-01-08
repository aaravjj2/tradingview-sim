"""
Sentiment Engine (FinBERT)
Analyzes news headlines using HuggingFace FinBERT model for financial sentiment.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
import os
import json

# Try to import transformers, fall back to mock if not available
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    FINBERT_AVAILABLE = True
except ImportError:
    FINBERT_AVAILABLE = False
    print("⚠️ transformers/torch not installed. Sentiment Engine will use mock mode.")


class SentimentLabel(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class HeadlineSentiment:
    """Sentiment analysis result for a single headline."""
    headline: str
    label: SentimentLabel
    score: float  # Confidence score
    weighted_score: float  # -1 to +1 (negative = bearish, positive = bullish)
    source: str = ""
    published_at: Optional[datetime] = None


@dataclass
class TickerSentiment:
    """Aggregated sentiment for a ticker."""
    ticker: str
    overall_score: float  # -1 to +1
    headline_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    headlines: List[HeadlineSentiment]
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def sentiment_label(self) -> str:
        if self.overall_score >= 0.3:
            return "BULLISH"
        elif self.overall_score <= -0.3:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "overall_score": round(self.overall_score, 3),
            "sentiment_label": self.sentiment_label,
            "headline_count": self.headline_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "analyzed_at": self.analyzed_at.isoformat(),
            "top_headlines": [
                {
                    "headline": h.headline[:100],
                    "sentiment": h.label.value,
                    "score": round(h.weighted_score, 2)
                }
                for h in sorted(self.headlines, key=lambda x: abs(x.weighted_score), reverse=True)[:5]
            ]
        }


class SentimentEngine:
    """
    FinBERT-powered sentiment analysis for financial news.
    
    Uses ProsusAI/finbert model for financial domain sentiment.
    Falls back to mock mode if transformers is not installed.
    """
    
    def __init__(self, use_gpu: bool = True):
        self.model_name = "ProsusAI/finbert"
        self.pipeline = None
        
        # Determine device
        self.device = -1
        if FINBERT_AVAILABLE:
            if use_gpu and torch.cuda.is_available():
                self.device = 0  # GPU index 0
                print(f"[Sentiment] Using GPU: {torch.cuda.get_device_name(0)}")
            else:
                self.device = -1 # CPU
                print("[Sentiment] Using CPU (GPU not available or disabled)")
        
        self.cache: Dict[str, TickerSentiment] = {}
        self.cache_ttl_seconds = 300  # 5 minute cache
        
        if FINBERT_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load FinBERT model (lazy loading)."""
        try:
            print(f"Loading FinBERT model: {self.model_name}...")
            # Explicitly move to device if using GPU
            device_arg = self.device
            
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                device=device_arg,
                max_length=512,
                truncation=True
            )
            print("✅ FinBERT model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load FinBERT: {e}")
            self.pipeline = None
    
    async def get_sentiment(self, ticker: str, force_refresh: bool = False) -> TickerSentiment:
        """
        Get sentiment analysis for a ticker.
        
        Args:
            ticker: Stock symbol
            force_refresh: Bypass cache
            
        Returns:
            TickerSentiment with aggregated scores
        """
        # Check cache
        if not force_refresh and ticker in self.cache:
            cached = self.cache[ticker]
            age = (datetime.now() - cached.analyzed_at).seconds
            if age < self.cache_ttl_seconds:
                return cached
        
        # Fetch headlines
        headlines = await self._fetch_headlines(ticker)
        
        if not headlines:
            return TickerSentiment(
                ticker=ticker,
                overall_score=0.0,
                headline_count=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                headlines=[]
            )
        
        # Analyze sentiment
        analyzed = await self._analyze_headlines(headlines)
        
        # Aggregate scores
        positive_count = sum(1 for h in analyzed if h.label == SentimentLabel.POSITIVE)
        negative_count = sum(1 for h in analyzed if h.label == SentimentLabel.NEGATIVE)
        neutral_count = sum(1 for h in analyzed if h.label == SentimentLabel.NEUTRAL)
        
        # Calculate weighted average
        total_weight = sum(h.score for h in analyzed)
        if total_weight > 0:
            overall_score = sum(h.weighted_score * h.score for h in analyzed) / total_weight
        else:
            overall_score = 0.0
        
        result = TickerSentiment(
            ticker=ticker,
            overall_score=overall_score,
            headline_count=len(analyzed),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            headlines=analyzed
        )
        
        # Cache result
        self.cache[ticker] = result
        
        return result
    
    async def _fetch_headlines(self, ticker: str) -> List[Dict]:
        """
        Fetch recent news headlines for a ticker.
        
        In production, this would call Alpaca News API or RSS feeds.
        For now, we use mock headlines.
        """
        # TODO: Integrate with real news API
        # For now, return mock headlines based on ticker
        
        mock_headlines = self._get_mock_headlines(ticker)
        return mock_headlines
    
    def _get_mock_headlines(self, ticker: str) -> List[Dict]:
        """Generate realistic mock headlines for testing."""
        templates = {
            "positive": [
                f"{ticker} Reports Record Revenue, Beats Analyst Expectations",
                f"Analysts Upgrade {ticker} to Buy on Strong Growth Outlook",
                f"{ticker} Announces Major Partnership with Tech Giant",
                f"{ticker} CEO: 'We're Just Getting Started' on AI Revenue",
                f"Institutional Investors Increase {ticker} Holdings",
            ],
            "negative": [
                f"{ticker} Misses Earnings Estimates, Shares Decline",
                f"Analysts Downgrade {ticker} Citing Competitive Pressures",
                f"{ticker} Faces Regulatory Scrutiny Over Business Practices",
                f"{ticker} CFO Unexpectedly Resigns Amid Accounting Concerns",
                f"Short Sellers Target {ticker} on Valuation Concerns",
            ],
            "neutral": [
                f"{ticker} Trading Near 52-Week Average",
                f"{ticker} Announces Leadership Changes in Marketing Division",
                f"{ticker} to Present at Upcoming Industry Conference",
                f"Options Activity Picks Up in {ticker} Ahead of Earnings",
                f"{ticker} Board Approves Standard Dividend Payment",
            ]
        }
        
        # Generate a mix of headlines
        import random
        all_headlines = []
        
        # Add 2-3 positive
        for h in random.sample(templates["positive"], min(3, len(templates["positive"]))):
            all_headlines.append({"headline": h, "source": "MockNews"})
        
        # Add 1-2 negative
        for h in random.sample(templates["negative"], min(2, len(templates["negative"]))):
            all_headlines.append({"headline": h, "source": "MockNews"})
        
        # Add 2-3 neutral
        for h in random.sample(templates["neutral"], min(3, len(templates["neutral"]))):
            all_headlines.append({"headline": h, "source": "MockNews"})
        
        return all_headlines
    
    async def _analyze_headlines(self, headlines: List[Dict]) -> List[HeadlineSentiment]:
        """Analyze sentiment of headlines using FinBERT or mock."""
        results = []
        
        for item in headlines:
            text = item["headline"]
            source = item.get("source", "")
            
            if self.pipeline:
                # Real FinBERT analysis
                try:
                    prediction = self.pipeline(text)[0]
                    label_str = prediction["label"].lower()
                    confidence = prediction["score"]
                    
                    label = SentimentLabel(label_str)
                    
                    # Convert to weighted score (-1 to +1)
                    if label == SentimentLabel.POSITIVE:
                        weighted = confidence
                    elif label == SentimentLabel.NEGATIVE:
                        weighted = -confidence
                    else:
                        weighted = 0.0
                    
                except Exception as e:
                    print(f"FinBERT error: {e}")
                    label = SentimentLabel.NEUTRAL
                    confidence = 0.5
                    weighted = 0.0
            else:
                # Mock analysis based on keywords
                label, confidence, weighted = self._mock_analyze(text)
            
            results.append(HeadlineSentiment(
                headline=text,
                label=label,
                score=confidence,
                weighted_score=weighted,
                source=source
            ))
        
        return results
    
    def _mock_analyze(self, text: str) -> Tuple[SentimentLabel, float, float]:
        """Simple keyword-based mock sentiment analysis."""
        text_lower = text.lower()
        
        positive_keywords = ["beat", "surge", "upgrade", "record", "growth", "partnership", "buy", "bullish"]
        negative_keywords = ["miss", "decline", "downgrade", "concern", "resign", "short", "regulatory", "bearish"]
        
        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        if pos_count > neg_count:
            confidence = min(0.7 + pos_count * 0.1, 0.95)
            return SentimentLabel.POSITIVE, confidence, confidence
        elif neg_count > pos_count:
            confidence = min(0.7 + neg_count * 0.1, 0.95)
            return SentimentLabel.NEGATIVE, confidence, -confidence
        else:
            return SentimentLabel.NEUTRAL, 0.6, 0.0
    
    async def get_global_sentiment(self, tickers: Optional[List[str]] = None) -> Dict:
        """
        Get aggregated market sentiment across multiple tickers.
        
        Useful for the Circuit Breaker to detect market-wide panic.
        """
        if tickers is None:
            tickers = ["SPY", "QQQ", "IWM", "DIA"]  # Major indices
        
        results = await asyncio.gather(
            *[self.get_sentiment(t) for t in tickers],
            return_exceptions=True
        )
        
        valid_results = [r for r in results if isinstance(r, TickerSentiment)]
        
        if not valid_results:
            return {"global_score": 0.0, "status": "NEUTRAL", "ticker_count": 0}
        
        avg_score = sum(r.overall_score for r in valid_results) / len(valid_results)
        
        if avg_score <= -0.8:
            status = "PANIC"
        elif avg_score <= -0.5:
            status = "BEARISH"
        elif avg_score >= 0.5:
            status = "EUPHORIC"
        elif avg_score >= 0.3:
            status = "BULLISH"
        else:
            status = "NEUTRAL"
        
        return {
            "global_score": round(avg_score, 3),
            "status": status,
            "ticker_count": len(valid_results),
            "tickers": [r.to_dict() for r in valid_results]
        }


# Singleton instance
_sentiment_engine: Optional[SentimentEngine] = None

def get_sentiment_engine() -> SentimentEngine:
    """Get or create the global sentiment engine instance."""
    global _sentiment_engine
    if _sentiment_engine is None:
        _sentiment_engine = SentimentEngine()
    return _sentiment_engine
