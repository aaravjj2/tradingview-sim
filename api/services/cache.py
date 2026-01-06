"""
Cache Service
SQLite-based caching for candle data and trade history
"""

import aiosqlite
import os
from typing import List, Dict, Optional
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cache.db")


async def init_database():
    """Initialize SQLite database with required tables"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Candles table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, timeframe, timestamp)
            )
        """)
        
        # Trade journal table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trade_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                strategy TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity INTEGER,
                side TEXT,
                pnl REAL,
                notes TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Backtest results table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                strategy_rule TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                total_return REAL,
                sharpe_ratio REAL,
                win_rate REAL,
                max_drawdown REAL,
                signals TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()
        print("Database initialized successfully")


async def get_cached_candles(ticker: str, timeframe: str, limit: int) -> Optional[List[Dict]]:
    """Get cached candles if available and fresh (within 1 hour)"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Check cache freshness - only use if updated within last hour
            cursor = await db.execute("""
                SELECT MAX(created_at) as latest FROM candles
                WHERE ticker = ? AND timeframe = ?
            """, (ticker, timeframe))
            row = await cursor.fetchone()
            
            if row and row["latest"]:
                try:
                    latest = datetime.fromisoformat(row["latest"].replace('Z', '+00:00'))
                    age = (datetime.now() - latest.replace(tzinfo=None)).total_seconds()
                    if age > 3600:  # 1 hour expiration
                        return None  # Force refresh
                except:
                    pass
            
            cursor = await db.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE ticker = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (ticker, timeframe, limit))
            
            rows = await cursor.fetchall()
            
            if len(rows) >= limit * 0.8:  # Return if we have 80% of requested data
                return [
                    {
                        "timestamp": row["timestamp"],
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["volume"]
                    }
                    for row in reversed(rows)
                ]
            return None
    except:
        return None


async def store_candles(ticker: str, timeframe: str, candles: List[Dict]):
    """Store candles in cache"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            for candle in candles:
                await db.execute("""
                    INSERT OR REPLACE INTO candles 
                    (ticker, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker,
                    timeframe,
                    candle["timestamp"],
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle["volume"]
                ))
            await db.commit()
    except Exception as e:
        print(f"Error storing candles: {e}")


async def add_journal_entry(trade_id: str, ticker: str, notes: str, 
                            tags: str = "", **kwargs) -> bool:
    """Add a journal entry for a trade"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO trade_journal 
                (trade_id, ticker, strategy, entry_price, exit_price, 
                 quantity, side, pnl, notes, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                ticker,
                kwargs.get("strategy", ""),
                kwargs.get("entry_price", 0),
                kwargs.get("exit_price", 0),
                kwargs.get("quantity", 0),
                kwargs.get("side", ""),
                kwargs.get("pnl", 0),
                notes,
                tags
            ))
            await db.commit()
            return True
    except:
        return False


async def get_journal_entries(ticker: Optional[str] = None, 
                               limit: int = 50) -> List[Dict]:
    """Get journal entries"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            if ticker:
                cursor = await db.execute("""
                    SELECT * FROM trade_journal
                    WHERE ticker = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (ticker, limit))
            else:
                cursor = await db.execute("""
                    SELECT * FROM trade_journal
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except:
        return []
