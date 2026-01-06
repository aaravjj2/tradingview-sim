"""
Database Module for Options Supergraph Dashboard
SQLite storage for OHLCV candles and trading data
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import json

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "trading_data.db")


@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database with required tables"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # OHLCV Candles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                timeframe TEXT NOT NULL DEFAULT '1min',
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                UNIQUE(ticker, timestamp, timeframe)
            )
        """)
        
        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_candles_ticker_time 
            ON candles(ticker, timestamp DESC)
        """)
        
        # Paper trading positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                position_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                strike REAL,
                expiration TEXT,
                option_type TEXT,
                opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME,
                close_price REAL,
                pnl REAL
            )
        """)
        
        # Paper trading account balance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                balance REAL NOT NULL DEFAULT 100000.0,
                initial_balance REAL NOT NULL DEFAULT 100000.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize account if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO paper_account (id, balance, initial_balance)
            VALUES (1, 100000.0, 100000.0)
        """)
        
        # Trade history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                strategy_name TEXT,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Cached indicators table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                indicator_type TEXT NOT NULL,
                period INTEGER NOT NULL,
                value REAL NOT NULL,
                UNIQUE(ticker, timestamp, indicator_type, period)
            )
        """)
        
        conn.commit()
        print(f"Database initialized at {DB_PATH}")


def store_candles(ticker: str, candles: List[Dict], timeframe: str = "1min"):
    """
    Store OHLCV candle data
    
    Args:
        ticker: Stock symbol
        candles: List of dicts with keys: timestamp, open, high, low, close, volume
        timeframe: Candle timeframe (1min, 5min, 1hour, 1day)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        for candle in candles:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO candles 
                    (ticker, timestamp, timeframe, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker.upper(),
                    candle["timestamp"],
                    timeframe,
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle.get("volume", 0)
                ))
            except Exception as e:
                print(f"Error storing candle: {e}")
        
        conn.commit()


def get_candles(ticker: str, start: datetime = None, end: datetime = None,
                timeframe: str = "1min", limit: int = 500) -> List[Dict]:
    """
    Retrieve candle data for a ticker
    
    Args:
        ticker: Stock symbol
        start: Start datetime (optional)
        end: End datetime (optional)
        timeframe: Candle timeframe
        limit: Maximum number of candles to return
        
    Returns:
        List of candle dictionaries
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE ticker = ? AND timeframe = ?
        """
        params = [ticker.upper(), timeframe]
        
        if start:
            query += " AND timestamp >= ?"
            params.append(start.isoformat())
        
        if end:
            query += " AND timestamp <= ?"
            params.append(end.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        candles = []
        for row in reversed(rows):  # Reverse to get chronological order
            candles.append({
                "timestamp": row["timestamp"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"]
            })
        
        return candles


def get_latest_candle(ticker: str, timeframe: str = "1min") -> Optional[Dict]:
    """Get the most recent candle for a ticker"""
    candles = get_candles(ticker, timeframe=timeframe, limit=1)
    return candles[0] if candles else None


def store_indicator(ticker: str, timestamp: datetime, indicator_type: str,
                    period: int, value: float):
    """Store a computed indicator value"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO indicators
            (ticker, timestamp, indicator_type, period, value)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker.upper(), timestamp.isoformat(), indicator_type, period, value))
        conn.commit()


def get_indicator_values(ticker: str, indicator_type: str, period: int,
                         limit: int = 100) -> List[Tuple[str, float]]:
    """
    Get historical indicator values
    
    Returns:
        List of (timestamp, value) tuples
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, value FROM indicators
            WHERE ticker = ? AND indicator_type = ? AND period = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (ticker.upper(), indicator_type, period, limit))
        
        return [(row["timestamp"], row["value"]) for row in reversed(cursor.fetchall())]


def get_candle_count(ticker: str, timeframe: str = "1min") -> int:
    """Get the number of stored candles for a ticker"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM candles
            WHERE ticker = ? AND timeframe = ?
        """, (ticker.upper(), timeframe))
        return cursor.fetchone()["count"]


def cleanup_old_candles(days_to_keep: int = 30):
    """Remove candles older than specified days"""
    cutoff = datetime.now() - timedelta(days=days_to_keep)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM candles WHERE timestamp < ?
        """, (cutoff.isoformat(),))
        deleted = cursor.rowcount
        conn.commit()
        return deleted


# Initialize database on module import
init_db()
