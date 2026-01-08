import asyncio
import logging
from unittest.mock import MagicMock
from services.scanner import ActiveCandidate, SignalType
from services.sentiment import TickerSentiment

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_execution_flow():
    print("\n--- Testing AutoPilot Execution Flow ---")
    
    # 1. Initialize AutoPilot
    # We import inside function to avoid premature initialization if script is imported
    from routers.autopilot import get_autopilot, AutoPilotState
    
    autopilot = get_autopilot()
    
    # Check Initial State
    print(f"Initial State: {autopilot.status.state}")
    
    # 2. Mock Scanner to return SPY
    # We want to force a scan hit
    print("MOCK: Injecting SPY candidate into Scanner...")
    
    mock_candidate = ActiveCandidate(
        ticker="SPY",
        current_price=590.0,
        iv_rank=85.0,
        volume_ratio=2.5,
        signal_type=SignalType.VOLUME_SPIKE,
        bid_ask_spread_pct=0.01,
        score=90.0
    )
    
    # Mock scanner.scan()
    async def mock_scan():
        return [mock_candidate]
    
    autopilot.scanner.scan = mock_scan
    
    # 3. Trigger Manual Scan (which triggers analyze -> execute if running loop, or we call manually)
    # The _run_loop is hard to test directly without waiting. 
    # Let's call the components in sequence to verify logic.
    
    print("STEP 1: Scan")
    candidates = await autopilot._scan()
    print(f"Scan Result: {[c.ticker for c in candidates]}")
    assert len(candidates) > 0 and candidates[0].ticker == "SPY"
    
    print("\nSTEP 2: Analyze (Council Vote)")
    # This calls real Council (Technician, Fundamentalist, RiskManager)
    # They might need data...
    # Ensure they don't block.
    approved_trades = await autopilot._analyze(candidates)
    print(f"Analysis Result: {approved_trades}")
    
    if not approved_trades:
        print("NOTE: Council rejected SPY (expected if data suggests NO trade).")
        print("FORCING APPROVAL for Execution Test...")
        approved_trades = [{
            "ticker": "SPY",
            "strategy": "iron_condor", # Force a strategy
            "decision": {"mock": True}
        }]
    
    print("\nSTEP 3: Execute (SmartLegger)")
    # This is the critical part I just added
    await autopilot._execute(approved_trades)
    
    # Check Logs
    print("\n--- Execution Logs ---")
    found_exec_log = False
    for entry in autopilot.get_activity_log(20):
        if entry["source"] == "executor":
            print(f"[{entry['level'].upper()}] {entry['message']}")
            if "Generated 4 legs" in entry["message"] or "Created Execution Plan" in entry["message"] or "Would execute" in entry["message"]:
                found_exec_log = True
                
    if found_exec_log:
        print("\n✅ Execution Logic Verified!")
    else:
        print("\n❌ Execution Logic Failed (No logs found)")

if __name__ == "__main__":
    try:
        asyncio.run(test_execution_flow())
    except Exception as e:
        print(f"CRASH: {e}")
