"""
Alpaca API Service
Wrapper for all Alpaca API interactions
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Load environment variables from keys.env
load_dotenv("/home/aarav/Tradingview/keys.env")

ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID", "")
ALPACA_API_SECRET = os.getenv("APCA_API_SECRET_KEY", "")
ALPACA_ENDPOINT = os.getenv("APCA_ENDPOINT", "https://paper-api.alpaca.markets")


class AlpacaService:
    """Async-ready Alpaca API wrapper"""
    
    def __init__(self):
        self.api_key = ALPACA_API_KEY
        self.api_secret = ALPACA_API_SECRET
        self.base_url = ALPACA_ENDPOINT
        self.data_url = "https://data.alpaca.markets"
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret
        }
    
    async def get_current_price(self, ticker: str) -> Optional[Dict]:
        """Fetch current stock price"""
        try:
            url = f"{self.data_url}/v2/stocks/{ticker}/quotes/latest"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                quote = data.get("quote", {})
                bid = quote.get("bp", 0)
                ask = quote.get("ap", 0)
                
                price = (bid + ask) / 2 if bid and ask else await self._get_last_trade(ticker)
                
                return {
                    "ticker": ticker,
                    "price": price,
                    "bid": bid,
                    "ask": ask,
                    "timestamp": datetime.now().isoformat()
                }
            return None
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None
    
    async def _get_last_trade(self, ticker: str) -> Optional[float]:
        """Fallback to last trade price"""
        try:
            url = f"{self.data_url}/v2/stocks/{ticker}/trades/latest"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json().get("trade", {}).get("p")
            return None
        except:
            return None
    
    async def get_historical_bars(self, ticker: str, timeframe: str = "1Day", 
                                   limit: int = 100) -> List[Dict]:
        """Fetch historical OHLCV bars"""
        try:
            end = datetime.now()
            
            if timeframe == "1Day":
                start = end - timedelta(days=limit * 2)
            elif timeframe == "1Hour":
                start = end - timedelta(hours=limit * 2)
            else:
                start = end - timedelta(minutes=limit * 5)
            
            url = f"{self.data_url}/v2/stocks/{ticker}/bars"
            
            # Request more data to ensure we reach the end date
            # Then slice the last 'limit' bars
            request_limit = min(limit * 2, 10000) 
            
            params = {
                "timeframe": timeframe,
                "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "limit": request_limit, 
                "feed": "sip"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                bars = data.get("bars", [])
                
                # Return the LATEST 'limit' bars
                if len(bars) > limit:
                    bars = bars[-limit:]
                    
                return [
                    {
                        "timestamp": bar.get("t", ""),
                        "open": bar.get("o", 0),
                        "high": bar.get("h", 0),
                        "low": bar.get("l", 0),
                        "close": bar.get("c", 0),
                        "volume": bar.get("v", 0)
                    }
                    for bar in bars
                ]
            return []
        except Exception as e:
            print(f"Error fetching bars: {e}")
            return []
    
    async def get_options_chain(self, ticker: str, expiration: Optional[str] = None) -> Dict:
        """Fetch options chain"""
        try:
            url = f"{self.data_url}/v1beta1/options/snapshots/{ticker}"
            params = {"feed": "indicative"}
            
            if expiration:
                params["expiration_date"] = expiration
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                calls = []
                puts = []
                
                for symbol, snapshot in data.get("snapshots", {}).items():
                    option = self._parse_option(symbol, snapshot)
                    if option:
                        if option["type"] == "call":
                            calls.append(option)
                        else:
                            puts.append(option)
                
                calls.sort(key=lambda x: x["strike"])
                puts.sort(key=lambda x: x["strike"])
                
                return {"calls": calls, "puts": puts}
            return {"calls": [], "puts": []}
        except Exception as e:
            print(f"Error fetching options: {e}")
            return {"calls": [], "puts": []}
    
    def _parse_option(self, symbol: str, snapshot: Dict) -> Optional[Dict]:
        """Parse OCC option symbol"""
        try:
            quote = snapshot.get("latestQuote", {})
            greeks = snapshot.get("greeks", {})
            
            # Parse symbol: UNDERLYING + YYMMDD + C/P + Strike*1000
            base = symbol[:6].rstrip('0123456789')
            rest = symbol[len(base):]
            
            if len(rest) >= 15:
                date_part = rest[:6]
                option_type = "call" if rest[6] == "C" else "put"
                strike = int(rest[7:15]) / 1000
                
                year = 2000 + int(date_part[:2])
                month = int(date_part[2:4])
                day = int(date_part[4:6])
                expiration = f"{year}-{month:02d}-{day:02d}"
                
                bid = quote.get("bp", 0) or 0
                ask = quote.get("ap", 0) or 0
                
                return {
                    "symbol": symbol,
                    "strike": strike,
                    "type": option_type,
                    "expiration": expiration,
                    "bid": bid,
                    "ask": ask,
                    "iv": greeks.get("impliedVolatility", 0.30),
                    "delta": greeks.get("delta", 0),
                    "gamma": greeks.get("gamma", 0),
                    "theta": greeks.get("theta", 0),
                    "vega": greeks.get("vega", 0)
                }
            return None
        except:
            return None
    
    async def get_available_expirations(self, ticker: str) -> List[str]:
        """Get next 8 weekly expirations"""
        expirations = []
        today = datetime.now()
        
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0 and today.hour >= 16:
            days_until_friday = 7
        
        next_friday = today + timedelta(days=days_until_friday)
        
        for i in range(8):
            exp_date = next_friday + timedelta(weeks=i)
            expirations.append(exp_date.strftime("%Y-%m-%d"))
        
        return expirations
    
    async def get_implied_volatility(self, ticker: str, current_price: float) -> float:
        """Calculate average IV from ATM options"""
        try:
            options = await self.get_options_chain(ticker)
            all_options = options["calls"] + options["puts"]
            
            if not all_options:
                return 0.30
            
            atm = sorted(all_options, key=lambda x: abs(x["strike"] - current_price))[:4]
            ivs = [opt["iv"] for opt in atm if opt["iv"] > 0]
            
            return sum(ivs) / len(ivs) if ivs else 0.30
        except:
            return 0.30
    
    async def submit_order(self, symbol: str, qty: int, side: str,
                           order_type: str = "market", 
                           time_in_force: str = "day") -> Dict:
        """Submit order to Alpaca"""
        try:
            url = f"{self.base_url}/v2/orders"
            payload = {
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": order_type,
                "time_in_force": time_in_force
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as e:
            return {"error": str(e)}
