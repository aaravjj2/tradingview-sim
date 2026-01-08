
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.alpaca import AlpacaService
from services.regime_detector import get_regime_detector
from routers.autopilot import get_current_regime

async def test_alpaca():
    print("\n--- Testing Alpaca Connection ---")
    alpaca = AlpacaService()
    print(f"Endpoint: {alpaca.base_url}")
    print(f"Key ID Length: {len(alpaca.api_key)}")
    print(f"Secret Key Length: {len(alpaca.api_secret)}")
    
    price = await alpaca.get_current_price("SPY")
    if price:
        print(f"✅ Connection Successful. SPY Price: {price['price']}")
    else:
        print("❌ Connection Failed. Could not fetch SPY price.")

async def test_regime():
    print("\n--- Testing Regime Detection ---")
    try:
        data = await get_current_regime()
        print(f"Result Type: {type(data)}")
        print(f"Regime: {data.get('regime')}")
        print(f"Full Data: {data}")
    except Exception as e:
        print(f"❌ Regime Detection Failed: {e}")

async def test_oi():
    print("\n--- Testing Open Interest (Alpaca/YFinance) ---")
    from routers.market import get_open_interest
    try:
        oi_data = await get_open_interest("SPY")
        print(f"OI Profile Length: {len(oi_data.get('profile', []))}")
        print(f"Max OI Strike: {oi_data.get('max_oi_strike')}")
        if oi_data.get('profile'):
            print(f"Sample Strike Data: {oi_data['profile'][0]}")
    except Exception as e:
        print(f"❌ OI Fetch Failed: {e}")

async def test_forecast():
    print("\n--- Testing Forecast (Redis Cache Check) ---")
    from services.ensemble_forecaster import get_ensemble_forecaster
    import time
    
    forecaster = get_ensemble_forecaster()
    start = time.time()
    try:
        # Mock forecast generation usually involves monte carlo which is slow
        # But if cached, it should be fast
        import numpy as np
        historical = [690.0 * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(60)]
        # forecast is synchronous, ran in thread pool by API usually. Here runs directly.
        fc = forecaster.forecast(690.0, historical, 30)
        elapsed = time.time() - start
        print(f"Forecast Time: {elapsed:.2f}s")
        print(f"Forecast Keys: {fc.keys()}")
    except Exception as e:
        print(f"❌ Forecast Failed: {e}")

async def main():
    await test_alpaca()
    await test_regime()
    await test_oi()
    await test_forecast()

if __name__ == "__main__":
    asyncio.run(main())
