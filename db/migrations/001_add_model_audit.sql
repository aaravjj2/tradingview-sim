-- Migration 001: Add Model Audit Tables
-- 
-- Creates tables for auditing model runs, pre-trade analysis, and post-trade results.
-- These tables support the 3-loop QA cycle and reconciliation process.

-- Model Runs Audit Table
-- Tracks every model prediction for audit and replay purposes
CREATE TABLE IF NOT EXISTS model_runs (
    model_run_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    decision_time TEXT NOT NULL,
    model_version TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    signal INTEGER NOT NULL,      -- 0 or 1
    exposure REAL NOT NULL,       -- 0.0 to 1.0
    confidence REAL NOT NULL,     -- 0.0 to 1.0
    reason TEXT,
    trading_mode TEXT DEFAULT 'paper',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_model_runs_symbol_time 
ON model_runs(symbol, decision_time);

CREATE INDEX IF NOT EXISTS idx_model_runs_snapshot 
ON model_runs(snapshot_hash);

-- Pre-Trade Audit Table
-- Records expected execution parameters before order submission
CREATE TABLE IF NOT EXISTS pretrade_audit (
    pretrade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_plan_id TEXT NOT NULL,
    model_run_id TEXT,
    symbol TEXT NOT NULL,
    expected_price REAL NOT NULL,
    estimated_slippage REAL,      -- Expected slippage in bps
    adv_estimate REAL,            -- 20-day ADV
    target_shares INTEGER,
    order_side TEXT,              -- 'buy' or 'sell'
    scheduled_execution TEXT,     -- 'OPEN_T+1' etc.
    client_order_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (model_run_id) REFERENCES model_runs(model_run_id)
);

CREATE INDEX IF NOT EXISTS idx_pretrade_plan 
ON pretrade_audit(trade_plan_id);

CREATE INDEX IF NOT EXISTS idx_pretrade_client_order 
ON pretrade_audit(client_order_id);

-- Post-Trade Audit Table
-- Records actual execution results for reconciliation
CREATE TABLE IF NOT EXISTS posttrade_audit (
    posttrade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,          -- Internal order ID
    broker_order_id TEXT,            -- Broker's order ID
    trade_plan_id TEXT NOT NULL,
    pretrade_id INTEGER,
    symbol TEXT NOT NULL,
    fill_price REAL NOT NULL,
    fill_qty INTEGER NOT NULL,
    slippage REAL,                   -- Actual slippage in bps
    slippage_vs_expected REAL,       -- Difference from estimated
    status TEXT NOT NULL,            -- 'filled', 'partial', 'cancelled', 'rejected'
    execution_time TEXT,
    trading_mode TEXT DEFAULT 'paper',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (pretrade_id) REFERENCES pretrade_audit(pretrade_id)
);

CREATE INDEX IF NOT EXISTS idx_posttrade_order 
ON posttrade_audit(order_id);

CREATE INDEX IF NOT EXISTS idx_posttrade_plan 
ON posttrade_audit(trade_plan_id);

-- Reconciliation Summary Table
-- Aggregated daily reconciliation results
CREATE TABLE IF NOT EXISTS reconciliation_summary (
    reconciliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reconciliation_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    total_trades INTEGER,
    successful_fills INTEGER,
    failed_orders INTEGER,
    avg_slippage REAL,
    slippage_std REAL,
    slippage_within_tolerance INTEGER,  -- 1 if within model tolerance
    modeled_slippage_mean REAL,
    modeled_slippage_std REAL,
    total_pnl REAL,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(reconciliation_date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_date 
ON reconciliation_summary(reconciliation_date);
