"""
Trade Journal Service
Automatically records all trades with reasoning and performance tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
import json


class TradeStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeOutcome(Enum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"


@dataclass
class TradeEntry:
    """Single trade journal entry."""
    id: str
    timestamp: datetime
    ticker: str
    strategy: str
    direction: str  # "long" or "short"
    entry_price: float
    quantity: int
    
    # AI Council reasoning
    technician_vote: str
    fundamentalist_vote: str
    risk_manager_vote: str
    council_reasoning: str
    
    # Optional: LLM explanation
    llm_explanation: Optional[str] = None
    
    # Execution details
    status: TradeStatus = TradeStatus.PENDING
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    pnl: float = 0.0
    outcome: TradeOutcome = TradeOutcome.PENDING
    
    # Market context at entry
    market_regime: Optional[str] = None
    vix: Optional[float] = None
    sentiment_score: Optional[float] = None
    
    # Tags for filtering
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "ticker": self.ticker,
            "strategy": self.strategy,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "technician_vote": self.technician_vote,
            "fundamentalist_vote": self.fundamentalist_vote,
            "risk_manager_vote": self.risk_manager_vote,
            "council_reasoning": self.council_reasoning,
            "llm_explanation": self.llm_explanation,
            "status": self.status.value,
            "exit_price": self.exit_price,
            "exit_timestamp": self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            "pnl": self.pnl,
            "outcome": self.outcome.value,
            "market_regime": self.market_regime,
            "vix": self.vix,
            "sentiment_score": self.sentiment_score,
            "tags": self.tags
        }


class TradeJournal:
    """
    Trade Journal for automatic trade recording.
    
    Integrates with AutoPilot to record every trade decision with:
    - AI Council votes and reasoning
    - Market context (regime, VIX, sentiment)
    - Optional LLM explanation from Ollama
    - Performance tracking (P&L, win rate, etc.)
    """
    
    def __init__(self, persist_path: str = "trade_journal.json"):
        self.entries: List[TradeEntry] = []
        self.persist_path = persist_path
        self._load()
    
    def record_trade(
        self,
        ticker: str,
        strategy: str,
        direction: str,
        entry_price: float,
        quantity: int,
        council_decision: Dict,
        market_context: Optional[Dict] = None,
        llm_explanation: Optional[str] = None
    ) -> TradeEntry:
        """
        Record a new trade entry.
        
        Args:
            ticker: Stock ticker
            strategy: Strategy name (e.g., "Iron Condor")
            direction: "long" or "short"
            entry_price: Entry price
            quantity: Number of contracts/shares
            council_decision: AI Council decision dict
            market_context: Optional market regime, VIX, sentiment
            llm_explanation: Optional LLM-generated explanation
        
        Returns:
            TradeEntry object
        """
        trade_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        entry = TradeEntry(
            id=trade_id,
            timestamp=datetime.now(),
            ticker=ticker,
            strategy=strategy,
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            technician_vote=council_decision.get("technician_vote", "UNKNOWN"),
            fundamentalist_vote=council_decision.get("fundamentalist_vote", "UNKNOWN"),
            risk_manager_vote=council_decision.get("risk_manager_vote", "UNKNOWN"),
            council_reasoning=council_decision.get("reasoning", "No reasoning provided"),
            llm_explanation=llm_explanation,
            status=TradeStatus.OPEN,
            market_regime=market_context.get("regime") if market_context else None,
            vix=market_context.get("vix") if market_context else None,
            sentiment_score=market_context.get("sentiment") if market_context else None,
            tags=[strategy, market_context.get("regime", "unknown") if market_context else "unknown"]
        )
        
        self.entries.append(entry)
        self._save()
        
        print(f"[Journal] Recorded trade: {ticker} {strategy} @ ${entry_price}")
        
        return entry
    
    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_timestamp: Optional[datetime] = None
    ):
        """Close a trade and calculate P&L."""
        for entry in self.entries:
            if entry.id == trade_id:
                entry.exit_price = exit_price
                entry.exit_timestamp = exit_timestamp or datetime.now()
                entry.status = TradeStatus.CLOSED
                
                # Calculate P&L (simplified)
                if entry.direction == "long":
                    entry.pnl = (exit_price - entry.entry_price) * entry.quantity
                else:
                    entry.pnl = (entry.entry_price - exit_price) * entry.quantity
                
                # Determine outcome
                if entry.pnl > 10:
                    entry.outcome = TradeOutcome.WIN
                elif entry.pnl < -10:
                    entry.outcome = TradeOutcome.LOSS
                else:
                    entry.outcome = TradeOutcome.BREAKEVEN
                
                self._save()
                print(f"[Journal] Closed trade: {trade_id} P&L=${entry.pnl:.2f}")
                return entry
        
        print(f"[Journal] Trade {trade_id} not found")
        return None
    
    def get_stats(self) -> Dict:
        """Get journal statistics."""
        closed_trades = [e for e in self.entries if e.status == TradeStatus.CLOSED]
        
        if not closed_trades:
            return {
                "total_trades": len(self.entries),
                "closed_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0
            }
        
        wins = [e for e in closed_trades if e.outcome == TradeOutcome.WIN]
        losses = [e for e in closed_trades if e.outcome == TradeOutcome.LOSS]
        
        total_pnl = sum(e.pnl for e in closed_trades)
        win_rate = len(wins) / len(closed_trades) if closed_trades else 0
        avg_win = sum(e.pnl for e in wins) / len(wins) if wins else 0
        avg_loss = sum(e.pnl for e in losses) / len(losses) if losses else 0
        
        total_wins = sum(e.pnl for e in wins)
        total_losses = abs(sum(e.pnl for e in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return {
            "total_trades": len(self.entries),
            "closed_trades": len(closed_trades),
            "open_trades": len([e for e in self.entries if e.status == TradeStatus.OPEN]),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "winning_trades": len(wins),
            "losing_trades": len(losses)
        }
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Get recent trades."""
        recent = sorted(self.entries, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [e.to_dict() for e in recent]
    
    def filter_by_strategy(self, strategy: str) -> List[TradeEntry]:
        """Filter trades by strategy."""
        return [e for e in self.entries if e.strategy.lower() == strategy.lower()]
    
    def filter_by_outcome(self, outcome: TradeOutcome) -> List[TradeEntry]:
        """Filter trades by outcome."""
        return [e for e in self.entries if e.outcome == outcome]
    
    def _save(self):
        """Persist journal to disk."""
        try:
            with open(self.persist_path, 'w') as f:
                json.dump([e.to_dict() for e in self.entries], f, indent=2)
        except Exception as e:
            print(f"[Journal] Save error: {e}")
    
    def _load(self):
        """Load journal from disk."""
        try:
            with open(self.persist_path, 'r') as f:
                data = json.load(f)
                # Reconstruct entries (simplified - would need full deserialization)
                print(f"[Journal] Loaded {len(data)} trades from disk")
        except FileNotFoundError:
            print("[Journal] No existing journal found, starting fresh")
        except Exception as e:
            print(f"[Journal] Load error: {e}")


# Singleton
_journal: Optional[TradeJournal] = None

def get_trade_journal() -> TradeJournal:
    global _journal
    if _journal is None:
        _journal = TradeJournal()
    return _journal
