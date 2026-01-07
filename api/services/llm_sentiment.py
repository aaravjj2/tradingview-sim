"""
LLM Sentiment Analysis Agent
Uses local LLM to analyze news headlines for trading signals
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import json
import random


class LLMSentimentAgent:
    """
    LLM-based Sentiment Analysis Agent
    
    Analyzes news headlines and returns sentiment scores that can be used
    for trading decisions.
    
    In production, connects to local Ollama instance or other LLM provider.
    """
    
    def __init__(
        self,
        model: str = "llama3",
        ollama_url: str = "http://localhost:11434",
        timeout: int = 30
    ):
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.connected = False
        
        # Analysis history for tracking
        self.analysis_history: List[Dict] = []
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """
        Call the LLM with a prompt
        
        In production, use aiohttp to call Ollama API
        """
        try:
            # Production implementation:
            # async with aiohttp.ClientSession() as session:
            #     async with session.post(
            #         f"{self.ollama_url}/api/generate",
            #         json={"model": self.model, "prompt": prompt},
            #         timeout=self.timeout
            #     ) as response:
            #         result = await response.json()
            #         return result.get("response", "")
            
            # Simulated response for demo
            return self._simulate_llm_response(prompt)
            
        except Exception as e:
            print(f"LLM call failed: {e}")
            return None
    
    def _simulate_llm_response(self, prompt: str) -> str:
        """Simulate LLM response for demo purposes"""
        # Extract key sentiment indicators from the prompt
        positive_words = ["beat", "surge", "growth", "profit", "upgrade", "bullish", "rally", "strong"]
        negative_words = ["miss", "decline", "loss", "downgrade", "bearish", "crash", "weak", "concern"]
        
        prompt_lower = prompt.lower()
        
        pos_count = sum(1 for w in positive_words if w in prompt_lower)
        neg_count = sum(1 for w in negative_words if w in prompt_lower)
        
        # Determine sentiment based on word counts
        if pos_count > neg_count:
            sentiment = "positive"
            score = min(1.0, 0.5 + pos_count * 0.15)
            confidence = min(0.95, 0.7 + pos_count * 0.08)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = max(-1.0, -0.5 - neg_count * 0.15)
            confidence = min(0.95, 0.7 + neg_count * 0.08)
        else:
            sentiment = "neutral"
            score = random.uniform(-0.2, 0.2)
            confidence = 0.5
        
        # Simulate structured response
        response = {
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "reasoning": f"Analysis based on {pos_count} positive and {neg_count} negative indicators"
        }
        
        return json.dumps(response)
    
    async def analyze_headlines(
        self,
        headlines: List[str],
        ticker: str
    ) -> Dict:
        """
        Analyze a list of headlines for sentiment
        
        Returns aggregate sentiment score and individual analyses
        """
        prompt = f"""Analyze the following news headlines related to {ticker} stock.
For each headline, provide a sentiment score from -1 (very bearish) to +1 (very bullish).

Headlines:
{chr(10).join(f'{i+1}. {h}' for i, h in enumerate(headlines))}

Respond in JSON format with:
- overall_sentiment: "positive", "negative", or "neutral"
- overall_score: number from -1 to 1
- confidence: number from 0 to 1
- headlines: array of {{headline, score, reasoning}}
"""
        
        response = await self._call_llm(prompt)
        
        if not response:
            return {
                "error": "LLM unavailable",
                "ticker": ticker,
                "score": 0,
                "confidence": 0
            }
        
        try:
            # Parse LLM response
            result = json.loads(response)
            
            analysis = {
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "num_headlines": len(headlines),
                "overall_sentiment": result.get("sentiment", "neutral"),
                "score": result.get("score", 0),
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", ""),
                "model": self.model
            }
            
            self.analysis_history.append(analysis)
            
            return analysis
            
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse LLM response",
                "ticker": ticker,
                "raw_response": response[:200]
            }
    
    async def get_trading_signal(
        self,
        ticker: str,
        headlines: List[str],
        threshold: float = 0.3
    ) -> Dict:
        """
        Get a trading signal based on sentiment analysis
        
        Returns: buy, sell, or hold signal with confidence
        """
        analysis = await self.analyze_headlines(headlines, ticker)
        
        if "error" in analysis:
            return {
                "signal": "hold",
                "reason": "Analysis unavailable",
                "error": analysis.get("error")
            }
        
        score = analysis.get("score", 0)
        confidence = analysis.get("confidence", 0)
        
        # Determine signal
        if score > threshold and confidence > 0.6:
            signal = "buy"
            strength = "strong" if score > 0.6 else "moderate"
        elif score < -threshold and confidence > 0.6:
            signal = "sell"
            strength = "strong" if score < -0.6 else "moderate"
        else:
            signal = "hold"
            strength = "neutral"
        
        return {
            "signal": signal,
            "strength": strength,
            "score": score,
            "confidence": confidence,
            "reasoning": analysis.get("reasoning", ""),
            "ticker": ticker,
            "timestamp": datetime.now().isoformat()
        }
    
    async def analyze_single_headline(
        self,
        headline: str,
        ticker: str
    ) -> Dict:
        """Analyze a single headline quickly"""
        prompt = f"""Rate the sentiment of this news headline for {ticker}:
"{headline}"

Respond in JSON: {{"sentiment": "positive/negative/neutral", "score": -1 to 1, "confidence": 0 to 1}}"""
        
        response = await self._call_llm(prompt)
        
        try:
            result = json.loads(response) if response else {}
            return {
                "headline": headline,
                "ticker": ticker,
                "sentiment": result.get("sentiment", "neutral"),
                "score": result.get("score", 0),
                "confidence": result.get("confidence", 0.5)
            }
        except:
            return {
                "headline": headline,
                "ticker": ticker,
                "sentiment": "neutral",
                "score": 0,
                "confidence": 0
            }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent analysis history"""
        return self.analysis_history[-limit:]


# Global agent instance
_sentiment_agent: Optional[LLMSentimentAgent] = None


def get_sentiment_agent() -> LLMSentimentAgent:
    """Get or create the sentiment agent"""
    global _sentiment_agent
    if _sentiment_agent is None:
        _sentiment_agent = LLMSentimentAgent()
    return _sentiment_agent


async def analyze_sentiment(
    ticker: str,
    headlines: List[str]
) -> Dict:
    """API helper for sentiment analysis"""
    agent = get_sentiment_agent()
    return await agent.analyze_headlines(headlines, ticker)


async def get_sentiment_signal(
    ticker: str,
    headlines: List[str],
    threshold: float = 0.3
) -> Dict:
    """API helper for getting trading signal"""
    agent = get_sentiment_agent()
    return await agent.get_trading_signal(ticker, headlines, threshold)


# Sample headlines for testing
SAMPLE_HEADLINES = {
    "SPY": [
        "Markets rally on strong jobs report, S&P 500 hits new highs",
        "Fed signals potential rate cuts in 2024",
        "Tech stocks lead market gains amid AI boom",
        "Consumer confidence rises to 2-year high"
    ],
    "NVDA": [
        "NVIDIA beats earnings expectations, AI demand surges",
        "Data center revenue doubles year-over-year",
        "NVIDIA announces new AI chip lineup",
        "Analysts upgrade price targets on strong guidance"
    ],
    "TSLA": [
        "Tesla deliveries miss expectations",
        "EV competition intensifies from Chinese manufacturers",
        "Tesla announces price cuts amid demand concerns",
        "Elon Musk faces criticism over social media posts"
    ]
}


async def demo_sentiment_analysis(ticker: str) -> Dict:
    """Demo sentiment analysis with sample headlines"""
    headlines = SAMPLE_HEADLINES.get(ticker, SAMPLE_HEADLINES["SPY"])
    return await analyze_sentiment(ticker, headlines)
