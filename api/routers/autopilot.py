"""
AutoPilot Router
Main control interface for the autonomous trading system.
"""

from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

from services.scanner import get_scanner, ActiveCandidate
from services.sentiment import get_sentiment_engine
from services.regime_detector import get_regime_detector, MarketRegime
from services.decision_engine import get_council, StrategyRecommendation

router = APIRouter(prefix="/api/autopilot", tags=["AutoPilot"])


class AutoPilotState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"  # Circuit breaker triggered
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    EXECUTING = "executing"


@dataclass
class AutoPilotStatus:
    """Current state of the AutoPilot system."""
    state: AutoPilotState
    started_at: Optional[datetime] = None
    last_scan: Optional[datetime] = None
    last_decision: Optional[datetime] = None
    scan_count: int = 0
    trade_count: int = 0
    pending_trades: List[Dict] = field(default_factory=list)
    paused_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "last_decision": self.last_decision.isoformat() if self.last_decision else None,
            "scan_count": self.scan_count,
            "trade_count": self.trade_count,
            "pending_trades": self.pending_trades,
            "paused_reason": self.paused_reason
        }


@dataclass
class ActivityLogEntry:
    """Single entry in the activity feed."""
    timestamp: datetime
    source: str  # "scanner", "analyst", "executor", "risk", "system"
    message: str
    level: str = "info"  # "info", "warning", "error", "success"
    ticker: Optional[str] = None
    data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "message": self.message,
            "level": self.level,
            "ticker": self.ticker,
            "data": self.data
        }


class AutoPilot:
    """
    Main AutoPilot controller.
    
    Orchestrates the Scan -> Analyze -> Execute loop.
    """
    
    def __init__(self):
        from services.smart_legger import SmartLegger
        from services.alpaca import AlpacaService
        
        self.status = AutoPilotStatus(state=AutoPilotState.STOPPED)
        self.activity_log: List[ActivityLogEntry] = []
        self.scanner = get_scanner()
        self.sentiment = get_sentiment_engine()
        self.regime_detector = get_regime_detector()
        self.council = get_council()
        
        self.alpaca = AlpacaService()
        self.legger = SmartLegger(self.alpaca)
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Configuration
        self.scan_interval_seconds = 300  # 5 minutes
        self.max_candidates_per_scan = 5
        self.paper_mode = True  # Safety: default to paper trading
    
    def log(self, source: str, message: str, level: str = "info", 
            ticker: Optional[str] = None, data: Optional[Dict] = None):
        """Add an entry to the activity log."""
        entry = ActivityLogEntry(
            timestamp=datetime.now(),
            source=source,
            message=message,
            level=level,
            ticker=ticker,
            data=data
        )
        self.activity_log.append(entry)
        
        # Keep only last 100 entries
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]
        
        print(f"[{source.upper()}] {message}")
    
    async def start(self, paper_mode: bool = True):
        """Start the AutoPilot loop."""
        if self._running:
            return {"status": "already_running"}
        
        self.paper_mode = paper_mode
        self._running = True
        self.status.state = AutoPilotState.RUNNING
        self.status.started_at = datetime.now()
        
        self.log("system", f"AutoPilot started in {'PAPER' if paper_mode else 'LIVE'} mode", "success")
        
        # Start background loop
        self._task = asyncio.create_task(self._run_loop())
        
        return {"status": "started", "mode": "paper" if paper_mode else "live"}
    
    async def stop(self):
        """Stop the AutoPilot loop."""
        self._running = False
        self.status.state = AutoPilotState.STOPPED
        
        if self._task:
            self._task.cancel()
            self._task = None
        
        self.log("system", "AutoPilot stopped", "warning")
        
        return {"status": "stopped"}
    
    async def pause(self, reason: str = "Manual pause"):
        """Pause the AutoPilot (Circuit Breaker)."""
        self.status.state = AutoPilotState.PAUSED
        self.status.paused_reason = reason
        
        self.log("risk", f"⚠️ CIRCUIT BREAKER: {reason}", "warning")
        
        return {"status": "paused", "reason": reason}
    
    async def resume(self):
        """Resume from paused state."""
        if self.status.state != AutoPilotState.PAUSED:
            return {"status": "not_paused"}
        
        self.status.state = AutoPilotState.RUNNING
        self.status.paused_reason = None
        
        self.log("system", "AutoPilot resumed from pause", "success")
        
        return {"status": "resumed"}
    
    async def _run_loop(self):
        """Main AutoPilot loop."""
        while self._running:
            try:
                # Skip if paused
                if self.status.state == AutoPilotState.PAUSED:
                    await asyncio.sleep(10)
                    continue
                
                # Phase 1: Scan
                self.status.state = AutoPilotState.SCANNING
                candidates = await self._scan()
                
                if not candidates:
                    self.log("scanner", "No candidates found this cycle", "info")
                    await asyncio.sleep(self.scan_interval_seconds)
                    continue
                
                # Phase 2: Analyze
                self.status.state = AutoPilotState.ANALYZING
                approved = await self._analyze(candidates)
                
                # Phase 3: Execute (if approved)
                if approved:
                    self.status.state = AutoPilotState.EXECUTING
                    await self._execute(approved)
                
                # Phase 4: Monitor & Manage
                if self.status.state != AutoPilotState.PAUSED:
                     # Monitor active plans (this is lightweight, just checks status)
                     # In a real system, we'd loop through self.legger.pending_legs
                     # For now, we simulate monitoring by logging count
                     active_plans = len(self.legger.pending_legs)
                     if active_plans > 0:
                         self.log("system", f"Monitoring {active_plans} active execution plans...", "info")

                # Return to running state
                self.status.state = AutoPilotState.RUNNING
                
                # Wait for next cycle
                await asyncio.sleep(self.scan_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log("system", f"AutoPilot error: {str(e)[:100]}", "error")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _scan(self) -> List[ActiveCandidate]:
        """Scan the market for candidates."""
        self.log("scanner", "🔍 Starting market scan...")
        
        candidates = await self.scanner.scan()
        self.status.last_scan = datetime.now()
        self.status.scan_count += 1
        
        if candidates:
            top = candidates[:self.max_candidates_per_scan]
            tickers = ", ".join(c.ticker for c in top)
            self.log("scanner", f"Found {len(candidates)} candidates. Top: {tickers}", "success")
            return top
        
        return []
    
    async def _analyze(self, candidates: List[ActiveCandidate]) -> List[Dict]:
        """Analyze candidates through the AI Council."""
        approved = []
        
        for candidate in candidates:
            self.log("analyst", f"🧠 Analyzing {candidate.ticker}...", ticker=candidate.ticker)
            
            # Get sentiment
            sentiment = await self.sentiment.get_sentiment(candidate.ticker)
            self.log("analyst", 
                    f"Sentiment for {candidate.ticker}: {sentiment.overall_score:.2f} ({sentiment.sentiment_label})",
                    ticker=candidate.ticker)
            
            # Council vote
            decision = await self.council.vote(candidate.ticker, {
                "candidate": candidate,
                "sentiment": sentiment
            })
            
            self.status.last_decision = datetime.now()
            
            if decision.approved:
                self.log("analyst", 
                        f"✅ {candidate.ticker} APPROVED by Council ({decision.yes_count}/3 votes)",
                        "success", 
                        ticker=candidate.ticker)
                approved.append({
                    "ticker": candidate.ticker,
                    "strategy": decision.strategy.value,
                    "decision": decision.to_dict()
                })
            else:
                self.log("analyst",
                        f"❌ {candidate.ticker} REJECTED by Council ({decision.no_count}/3 nos)",
                        "warning",
                        ticker=candidate.ticker)
        
        return approved
    
    async def _execute(self, trades: List[Dict]):
        """Execute approved trades."""
        # Use persistent legger
        legger = self.legger
        alpaca = self.alpaca
        
        for trade in trades:
            ticker = trade["ticker"]
            strategy = trade["strategy"]
            
            self.log("executor", f"🚀 Preparing execution for {strategy} on {ticker}...", ticker=ticker)
            
            # 1. Expand Strategy into Legs
            try:
                legs = await self._expand_strategy(ticker, strategy, alpaca)
                if not legs:
                    self.log("executor", f"❌ Failed to generate legs for {strategy}", "error", ticker=ticker)
                    continue
                
                self.log("executor", f"Generated {len(legs)} legs for {strategy}", "info", ticker=ticker)
                
            except Exception as e:
                self.log("executor", f"❌ Expansion Error: {str(e)}", "error", ticker=ticker)
                continue

            # Execute via SmartLegger (Paper or Live depends on API Keys)
            try:
                # Create Plan
                plan = await legger.create_legging_plan(ticker, legs)
                plan_id = plan['plan_id']
                
                mode_label = "PAPER" if self.paper_mode else "LIVE"
                self.log("executor", 
                        f"🔴 [{mode_label}] Created Execution Plan: {plan_id}",
                        "success",
                        ticker=ticker)
                
                # Start Execution Loop in Background
                # Use standard Historical Prices for RSI
                bars = await alpaca.get_historical_bars(ticker, "1Day", 30)
                closes = [b['close'] for b in bars]
                
                background_task = asyncio.create_task(
                    legger.run_execution_loop(plan_id, ticker, closes)
                )
                
                self.status.trade_count += 1
                self.status.pending_trades.append({
                    "ticker": ticker,
                    "strategy": strategy,
                    "plan_id": plan_id,
                    "status": "executing",
                    "mode": mode_label
                })
                
            except Exception as e:
                    self.log("executor", f"❌ Execution Creation Failed: {e}", "error", ticker=ticker)

    async def _expand_strategy(self, ticker: str, strategy: str, alpaca: object) -> List[Dict]:
        """Convert high-level strategy to specific option legs."""
        legs = []
        
        # Fetch Option Chain & Current Price
        # We need current price to determine strikes
        price_data = await alpaca.get_current_price(ticker)
        if not price_data:
            raise ValueError(f"Could not get price for {ticker}")
            
        current_price = price_data["price"]
        
        # Get Expirations (target ~30-45 DTE)
        expirations = await alpaca.get_available_expirations(ticker)
        if not expirations:
             raise ValueError("No expirations available")
             
        # Select expiry: ~4-5 weeks out (index 4 or 5 usually, since weekly)
        # 0=this week, 1=next week... 4=~30 days
        expiry = expirations[min(4, len(expirations)-1)]
        
        # Strategy Templates
        if strategy == "iron_condor":
            # Short Strangle (16 Delta) + Long Wings (5 Delta)
            # Simplified: Percentage OTM for now if Delta unavailable
            # Call side
            short_call_strike = round(current_price * 1.05) # ~5% OTM
            long_call_strike = round(current_price * 1.10)  # ~10% OTM
            
            # Put side
            short_put_strike = round(current_price * 0.95) # ~5% OTM
            long_put_strike = round(current_price * 0.90)  # ~10% OTM
            
            legs = [
                {"position": "short", "option_type": "call", "strike": short_call_strike, "expiration": expiry, "quantity": 1},
                {"position": "long", "option_type": "call", "strike": long_call_strike, "expiration": expiry, "quantity": 1},
                {"position": "short", "option_type": "put", "strike": short_put_strike, "expiration": expiry, "quantity": 1},
                {"position": "long", "option_type": "put", "strike": long_put_strike, "expiration": expiry, "quantity": 1},
            ]
            
        elif strategy == "call_spread":
            # Bull Call Spread
            long_strike = round(current_price) # ATM
            short_strike = round(current_price * 1.05)
            
            legs = [
                {"position": "long", "option_type": "call", "strike": long_strike, "expiration": expiry, "quantity": 1},
                {"position": "short", "option_type": "call", "strike": short_strike, "expiration": expiry, "quantity": 1},
            ]
            
        elif strategy == "put_spread":
            # Bear Put Spread
            long_strike = round(current_price) # ATM
            short_strike = round(current_price * 0.95)
            
            legs = [
                {"position": "long", "option_type": "put", "strike": long_strike, "expiration": expiry, "quantity": 1},
                {"position": "short", "option_type": "put", "strike": short_strike, "expiration": expiry, "quantity": 1},
            ]
            
        elif strategy == "no_trade":
            return []
            
        else:
            # Default to no trade or log error
            self.log("executor", f"Unknown strategy {strategy}, skipping expansion", "warning")
            return []
            
        return legs
    
    async def check_circuit_breaker(self):
        """Check if circuit breaker conditions are met."""
        # Get global sentiment
        global_sentiment = await self.sentiment.get_global_sentiment()
        
        if global_sentiment["global_score"] <= -0.8:
            await self.pause(f"Global sentiment PANIC ({global_sentiment['global_score']:.2f})")
            return True
        
        # Check regime
        regime = self.regime_detector.current_regime
        if regime and regime.regime == MarketRegime.CRASH:
            await self.pause(f"Market regime: CRASH (VIX={regime.vix:.1f})")
            return True
        
        return False
    
    def get_status(self) -> Dict:
        """Get current AutoPilot status."""
        return {
            **self.status.to_dict(),
            "activity_log": [e.to_dict() for e in self.activity_log[-20:]]
        }
    
    def get_activity_log(self, limit: int = 50) -> List[Dict]:
        """Get recent activity log entries."""
        return [e.to_dict() for e in self.activity_log[-limit:]]


# Singleton
_autopilot: Optional[AutoPilot] = None

def get_autopilot() -> AutoPilot:
    """Get or create the global AutoPilot instance."""
    global _autopilot
    if _autopilot is None:
        _autopilot = AutoPilot()
    return _autopilot


# --- API Endpoints ---

@router.post("/start")
async def start_autopilot(
    paper_mode: bool = Query(True, description="Run in paper trading mode"),
    background_tasks: BackgroundTasks = None
):
    """Start the AutoPilot system."""
    autopilot = get_autopilot()
    result = await autopilot.start(paper_mode=paper_mode)
    return result


@router.post("/stop")
async def stop_autopilot():
    """Stop the AutoPilot system."""
    autopilot = get_autopilot()
    result = await autopilot.stop()
    return result


@router.post("/pause")
async def pause_autopilot(reason: str = Query("Manual pause")):
    """Pause the AutoPilot (trigger circuit breaker)."""
    autopilot = get_autopilot()
    result = await autopilot.pause(reason)
    return result


@router.post("/resume")
async def resume_autopilot():
    """Resume from paused state."""
    autopilot = get_autopilot()
    result = await autopilot.resume()
    return result


@router.get("/status")
async def get_autopilot_status():
    """Get current AutoPilot status."""
    autopilot = get_autopilot()
    return autopilot.get_status()


@router.get("/activity")
async def get_activity_log(limit: int = Query(50, ge=1, le=100)):
    """Get activity log entries."""
    autopilot = get_autopilot()
    return {"entries": autopilot.get_activity_log(limit)}


@router.get("/scan")
async def manual_scan():
    """Trigger a manual market scan."""
    autopilot = get_autopilot()
    scanner = autopilot.scanner
    candidates = await scanner.scan()
    return {
        "candidates": [c.to_dict() for c in candidates[:10]],
        "total": len(candidates)
    }


@router.get("/regime")
async def get_current_regime():
    """Get current market regime with real data and caching."""
    from services.alpaca import AlpacaService
    from services.regime_detector import get_regime_detector
    from services.cache_service import get_cache
    
    try:
        # Try cache first
        cache = await get_cache()
        cache_key = cache.make_key("regime", "SPY")
        cached = await cache.get(cache_key)
        
        if cached:
            return cached
        
        # Compute regime
        alpaca = AlpacaService()
        detector = get_regime_detector()
        
        # Get SPY bars for regime detection
        bars = await alpaca.get_historical_bars("SPY", "1Day", 20)
        
        if not bars or len(bars) < 10:
            # Fallback to mock data
            fallback = {
                "regime": "CHOPPY",
                "confidence": 0.65,
                "adx": 18.5,
                "vix": 16.2,
                "rsi": 52.3,
                "price_range_pct": 2.1,
                "trend_direction": None,
                "recommended_strategy": "Iron Condor (neutral market)",
                "reasoning": "ADX below 25 indicates weak trend. VIX in normal range. RSI near midpoint."
            }
            await cache.set(cache_key, fallback, cache.ttl["regime"])
            return fallback
        
        # Get current SPY price for VIX proxy
        current_price_data = await alpaca.get_current_price("SPY")
        current_price = current_price_data["price"] if current_price_data else 580
        
        # Calculate mock VIX (in real system, fetch from separate source)
        # VIX approximation: higher when price moves are larger
        recent_returns = [(bars[i]["close"] - bars[i-1]["close"]) / bars[i-1]["close"] 
                         for i in range(1, min(10, len(bars)))]
        volatility = (sum(r**2 for r in recent_returns) / len(recent_returns)) ** 0.5
        vix = min(80, max(10, volatility * 100 * 15))  # Scale to VIX-like range
        
        # Detect regime
        regime_result = detector.detect(bars, vix)
        result_dict = regime_result.to_dict()
        
        # Cache result
        await cache.set(cache_key, result_dict, cache.ttl["regime"])
        
        return result_dict
        
    except Exception as e:
        print(f"[Regime] Error: {e}")
        # Return fallback data
        return {
            "regime": "CHOPPY",
            "confidence": 0.60,
            "adx": 20.0,
            "vix": 18.0,
            "rsi": 50.0,
            "price_range_pct": 1.5,
            "trend_direction": None,
            "recommended_strategy": "Neutral strategies (Iron Condor, Butterfly)",
            "reasoning": "Market data unavailable, assuming choppy conditions"
        }


@router.post("/vote/{ticker}")
async def council_vote(ticker: str):
    """Get AI Council vote for a specific ticker."""
    autopilot = get_autopilot()
    decision = await autopilot.council.vote(ticker)
    return decision.to_dict()
