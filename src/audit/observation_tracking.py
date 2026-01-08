"""
Observation Tracking

Daily pretrade/posttrade audit logging for extended observation period.
Supports 14+ day evidence collection required for micro-live deployment.
"""

import os
import sys
import json
import sqlite3
from datetime import date, datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class AuditStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PretradeAudit:
    """Pretrade audit entry for a trading day."""
    audit_date: str
    symbol: str
    regime: str
    signal: int
    confidence: float
    exposure: float
    vix_level: float
    time_in_market_pct: float  # Running metric
    snapshot_hash: str
    audit_timestamp: str
    status: str = "pending"
    notes: str = ""


@dataclass
class PosttradeAudit:
    """Posttrade audit entry for reconciliation."""
    audit_date: str
    symbol: str
    expected_shares: int
    actual_shares: int
    expected_price: float
    fill_price: float
    slippage_bps: float
    within_tolerance: bool
    reconciliation_status: str
    audit_timestamp: str
    notes: str = ""


@dataclass
class ObservationMetrics:
    """Daily observation metrics."""
    date: str
    trading_day_number: int
    time_in_market_pct: float
    regime_flips: int
    avg_slippage_bps: float
    trades_count: int
    kill_switch_triggers: int
    manual_overrides: int
    pretrade_status: str
    posttrade_status: str


class ObservationTracker:
    """
    Tracks extended observation period metrics.
    
    Maintains daily pretrade/posttrade audits and aggregates
    for weekly reporting.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "observation_tracking.db"
            )
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize observation tracking database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pretrade_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                regime TEXT,
                signal INTEGER,
                confidence REAL,
                exposure REAL,
                vix_level REAL,
                time_in_market_pct REAL,
                snapshot_hash TEXT,
                audit_timestamp TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                UNIQUE(audit_date, symbol)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posttrade_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                expected_shares INTEGER,
                actual_shares INTEGER,
                expected_price REAL,
                fill_price REAL,
                slippage_bps REAL,
                within_tolerance INTEGER,
                reconciliation_status TEXT,
                audit_timestamp TEXT NOT NULL,
                notes TEXT,
                UNIQUE(audit_date, symbol)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                trading_day_number INTEGER,
                time_in_market_pct REAL,
                regime_flips INTEGER,
                avg_slippage_bps REAL,
                trades_count INTEGER,
                kill_switch_triggers INTEGER,
                manual_overrides INTEGER,
                pretrade_status TEXT,
                posttrade_status TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_pretrade_audit(self, audit: PretradeAudit) -> bool:
        """Record a pretrade audit entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO pretrade_audits 
                (audit_date, symbol, regime, signal, confidence, exposure, 
                 vix_level, time_in_market_pct, snapshot_hash, audit_timestamp, 
                 status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit.audit_date, audit.symbol, audit.regime, audit.signal,
                audit.confidence, audit.exposure, audit.vix_level,
                audit.time_in_market_pct, audit.snapshot_hash, 
                audit.audit_timestamp, audit.status, audit.notes
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error recording pretrade audit: {e}")
            return False
        finally:
            conn.close()
    
    def record_posttrade_audit(self, audit: PosttradeAudit) -> bool:
        """Record a posttrade audit entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO posttrade_audits
                (audit_date, symbol, expected_shares, actual_shares,
                 expected_price, fill_price, slippage_bps, within_tolerance,
                 reconciliation_status, audit_timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit.audit_date, audit.symbol, audit.expected_shares,
                audit.actual_shares, audit.expected_price, audit.fill_price,
                audit.slippage_bps, audit.within_tolerance, 
                audit.reconciliation_status, audit.audit_timestamp, audit.notes
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error recording posttrade audit: {e}")
            return False
        finally:
            conn.close()
    
    def record_daily_metrics(self, metrics: ObservationMetrics) -> bool:
        """Record daily observation metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO observation_metrics
                (date, trading_day_number, time_in_market_pct, regime_flips,
                 avg_slippage_bps, trades_count, kill_switch_triggers,
                 manual_overrides, pretrade_status, posttrade_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.date, metrics.trading_day_number, metrics.time_in_market_pct,
                metrics.regime_flips, metrics.avg_slippage_bps, metrics.trades_count,
                metrics.kill_switch_triggers, metrics.manual_overrides,
                metrics.pretrade_status, metrics.posttrade_status
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error recording daily metrics: {e}")
            return False
        finally:
            conn.close()
    
    def get_observation_days(self) -> int:
        """Get total number of observation days recorded."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT date) FROM observation_metrics")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_pretrade_audits(self, start_date: str = None, 
                           end_date: str = None) -> List[Dict]:
        """Get pretrade audits for date range."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM pretrade_audits 
                WHERE audit_date BETWEEN ? AND ?
                ORDER BY audit_date DESC
            """, (start_date, end_date))
        else:
            cursor.execute("SELECT * FROM pretrade_audits ORDER BY audit_date DESC")
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_posttrade_audits(self, start_date: str = None,
                            end_date: str = None) -> List[Dict]:
        """Get posttrade audits for date range."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM posttrade_audits
                WHERE audit_date BETWEEN ? AND ?
                ORDER BY audit_date DESC
            """, (start_date, end_date))
        else:
            cursor.execute("SELECT * FROM posttrade_audits ORDER BY audit_date DESC")
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_observation_summary(self) -> Dict:
        """Get summary of observation period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_days,
                AVG(time_in_market_pct) as avg_time_in_market,
                SUM(regime_flips) as total_regime_flips,
                AVG(avg_slippage_bps) as avg_slippage,
                SUM(trades_count) as total_trades,
                SUM(kill_switch_triggers) as total_kills,
                SUM(manual_overrides) as total_overrides
            FROM observation_metrics
        """)
        row = cursor.fetchone()
        
        # Get pass rates
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed
            FROM pretrade_audits
        """)
        pretrade = cursor.fetchone()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN within_tolerance = 1 THEN 1 ELSE 0 END) as passed
            FROM posttrade_audits
        """)
        posttrade = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_observation_days": row[0] or 0,
            "avg_time_in_market_pct": row[1] or 0,
            "total_regime_flips": row[2] or 0,
            "avg_slippage_bps": row[3] or 0,
            "total_trades": row[4] or 0,
            "total_kill_switch_triggers": row[5] or 0,
            "total_manual_overrides": row[6] or 0,
            "pretrade_audit_pass_rate": (pretrade[1] / pretrade[0] * 100) if pretrade[0] else 0,
            "posttrade_audit_pass_rate": (posttrade[1] / posttrade[0] * 100) if posttrade[0] else 0,
        }
    
    def check_acceptance_criteria(self, config: Dict = None) -> Dict:
        """Check if observation period meets acceptance criteria."""
        if config is None:
            config = {
                "min_observation_days": 14,
                "max_unexplained_regime_flips": 5,
                "max_manual_overrides": 2,
                "slippage_tolerance_bps": 15,
                "min_time_in_market_pct": 15,
                "max_time_in_market_pct": 90,
            }
        
        summary = self.get_observation_summary()
        
        checks = {
            "sufficient_days": summary["total_observation_days"] >= config["min_observation_days"],
            "regime_flips_acceptable": summary["total_regime_flips"] <= config["max_unexplained_regime_flips"],
            "no_excessive_overrides": summary["total_manual_overrides"] <= config["max_manual_overrides"],
            "slippage_within_tolerance": summary["avg_slippage_bps"] <= config["slippage_tolerance_bps"],
            "time_in_market_reasonable": (
                config["min_time_in_market_pct"] <= summary["avg_time_in_market_pct"] <= config["max_time_in_market_pct"]
            ),
        }
        
        return {
            "all_passed": all(checks.values()),
            "checks": checks,
            "summary": summary,
        }


def get_observation_tracker(db_path: str = None) -> ObservationTracker:
    """Get observation tracker instance."""
    return ObservationTracker(db_path)
