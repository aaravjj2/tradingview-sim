"""
Ollama Reasoning Service
Generates human-readable explanations for trade decisions using local LLM.
"""

import asyncio
import aiohttp
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, List


@dataclass
class ReasoningResult:
    """Result of a reasoning request."""
    explanation: str
    model: str
    tokens_used: int
    generation_time_ms: float
    timestamp: datetime


class OllamaReasoner:
    """
    Ollama-powered trade reasoning engine.
    
    Generates 1-2 sentence explanations for why the AI Council
    made a particular trading decision.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3"  # or "mistral", "phi3", etc.
        self.timeout = 30
        self.available = False
        
        # Cache recent explanations
        self.cache: Dict[str, ReasoningResult] = {}
        self.max_cache_size = 100
    
    async def check_availability(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        self.available = any(self.model in m for m in models)
                        return self.available
        except Exception as e:
            print(f"[Ollama] Not available: {e}")
            self.available = False
        return False
    
    async def generate_explanation(
        self,
        ticker: str,
        decision: str,  # "APPROVED" or "REJECTED"
        strategy: str,
        technician_reason: str,
        fundamentalist_reason: str,
        risk_manager_reason: str
    ) -> ReasoningResult:
        """
        Generate a human-readable explanation for a trade decision.
        
        Returns a 1-2 sentence explanation combining all agent inputs.
        """
        # Check cache first
        cache_key = f"{ticker}_{decision}_{strategy}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Build prompt
        prompt = f"""You are a trading analyst explaining an AI-driven trade decision. 
Generate a single, concise sentence explaining why this trade was {decision}.

Trade Details:
- Ticker: {ticker}
- Strategy: {strategy}
- Decision: {decision}

Agent Opinions:
1. Technical Analyst: {technician_reason}
2. Fundamental Analyst: {fundamentalist_reason}
3. Risk Manager: {risk_manager_reason}

Write ONE sentence explaining the decision. Be specific and reference the key factors.
Example: "Buying NVDA Call Spread because RSI shows oversold conditions and sentiment is bullish (+0.8), despite elevated VIX."

Your explanation:"""

        start_time = datetime.now()
        
        # Try Ollama first, fallback to template if not available
        if self.available:
            try:
                explanation = await self._call_ollama(prompt)
            except Exception as e:
                print(f"[Ollama] Generation failed: {e}")
                explanation = self._generate_fallback(ticker, decision, strategy, technician_reason, fundamentalist_reason)
        else:
            explanation = self._generate_fallback(ticker, decision, strategy, technician_reason, fundamentalist_reason)
        
        generation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = ReasoningResult(
            explanation=explanation,
            model=self.model if self.available else "fallback",
            tokens_used=len(explanation.split()),
            generation_time_ms=generation_time,
            timestamp=datetime.now()
        )
        
        # Cache result
        self.cache[cache_key] = result
        if len(self.cache) > self.max_cache_size:
            # Remove oldest entries
            oldest = list(self.cache.keys())[0]
            del self.cache[oldest]
        
        return result
    
    async def _call_ollama(self, prompt: str) -> str:
        """Make request to Ollama API."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100  # Keep it short
                }
            }
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "").strip()
                else:
                    raise Exception(f"Ollama returned {resp.status}")
    
    def _generate_fallback(
        self,
        ticker: str,
        decision: str,
        strategy: str,
        tech_reason: str,
        fund_reason: str
    ) -> str:
        """Generate template-based explanation when Ollama unavailable."""
        if decision == "APPROVED":
            return f"{decision}: Opening {strategy} on {ticker} - {tech_reason[:50]}; {fund_reason[:50]}."
        else:
            return f"{decision}: Passing on {ticker} - Risk factors outweigh potential ({tech_reason[:40]})."
    
    async def explain_hedge(
        self,
        action: str,
        current_delta: float,
        contracts: int
    ) -> str:
        """Generate explanation for hedge action."""
        if not self.available:
            return f"Auto-hedge triggered: Portfolio delta at {current_delta:+.0f}, {action} {contracts} SPY contracts to neutralize."
        
        prompt = f"""Explain this hedging action in one sentence:
Action: {action}
Current Portfolio Delta: {current_delta:+.0f}
Contracts: {contracts}

Example: "Buying 3 SPY puts to reduce portfolio exposure after delta exceeded +500 threshold."

Your explanation:"""
        
        try:
            return await self._call_ollama(prompt)
        except:
            return f"Auto-hedge: {action} {contracts} contracts (delta was {current_delta:+.0f})"
    
    def get_status(self) -> Dict:
        """Get reasoner status."""
        return {
            "available": self.available,
            "model": self.model,
            "base_url": self.base_url,
            "cached_explanations": len(self.cache)
        }


# Singleton
_reasoner: Optional[OllamaReasoner] = None

async def get_reasoner() -> OllamaReasoner:
    global _reasoner
    if _reasoner is None:
        _reasoner = OllamaReasoner()
        await _reasoner.check_availability()
    return _reasoner
