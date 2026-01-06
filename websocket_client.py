"""
WebSocket Client Module for Options Supergraph Dashboard
Real-time price streaming via Alpaca WebSocket
"""

import asyncio
import json
import threading
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass
import websockets

from config import ALPACA_API_KEY, ALPACA_API_SECRET


@dataclass
class PriceUpdate:
    """Represents a real-time price update"""
    ticker: str
    price: float
    bid: float
    ask: float
    timestamp: str
    volume: int = 0


class AlpacaWebSocket:
    """
    WebSocket client for real-time Alpaca data streaming.
    Runs in a separate thread to avoid blocking the main UI.
    """
    
    # Alpaca WebSocket endpoints
    STOCK_STREAM_URL = "wss://stream.data.alpaca.markets/v2/iex"
    OPTIONS_STREAM_URL = "wss://stream.data.alpaca.markets/v1beta1/options"
    
    def __init__(self, on_price_update: Optional[Callable[[PriceUpdate], None]] = None):
        """
        Initialize WebSocket client
        
        Args:
            on_price_update: Callback function for price updates
        """
        self.api_key = ALPACA_API_KEY
        self.api_secret = ALPACA_API_SECRET
        self.on_price_update = on_price_update
        
        self._ws = None
        self._loop = None
        self._thread = None
        self._running = False
        self._subscribed_tickers: List[str] = []
        
        # Latest prices cache
        self.latest_prices: Dict[str, PriceUpdate] = {}
    
    def start(self, tickers: List[str]):
        """
        Start WebSocket connection in background thread
        
        Args:
            tickers: List of stock symbols to subscribe to
        """
        if self._running:
            print("WebSocket already running")
            return
        
        self._subscribed_tickers = [t.upper() for t in tickers]
        self._running = True
        
        # Create new event loop for the thread
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        print(f"WebSocket started for tickers: {self._subscribed_tickers}")
    
    def stop(self):
        """Stop WebSocket connection"""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)
        print("WebSocket stopped")
    
    def _run_event_loop(self):
        """Run the async event loop in a separate thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._connect_and_stream())
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self._loop.close()
    
    async def _connect_and_stream(self):
        """Connect to WebSocket and handle messages"""
        while self._running:
            try:
                async with websockets.connect(self.STOCK_STREAM_URL) as ws:
                    self._ws = ws
                    
                    # Authenticate
                    auth_msg = {
                        "action": "auth",
                        "key": self.api_key,
                        "secret": self.api_secret
                    }
                    await ws.send(json.dumps(auth_msg))
                    
                    # Wait for auth response
                    auth_response = await ws.recv()
                    auth_data = json.loads(auth_response)
                    
                    if not self._check_auth(auth_data):
                        print(f"Authentication failed: {auth_data}")
                        return
                    
                    print("WebSocket authenticated successfully")
                    
                    # Subscribe to quotes
                    subscribe_msg = {
                        "action": "subscribe",
                        "quotes": self._subscribed_tickers
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    # Handle incoming messages
                    while self._running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=30)
                            self._handle_message(message)
                        except asyncio.TimeoutError:
                            # Send ping to keep connection alive
                            await ws.ping()
                            
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"WebSocket error: {e}")
                await asyncio.sleep(5)
    
    def _check_auth(self, data: Any) -> bool:
        """Check if authentication was successful"""
        if isinstance(data, list):
            for item in data:
                if item.get("T") == "success" and item.get("msg") == "authenticated":
                    return True
        return False
    
    def _handle_message(self, message: str):
        """Parse and handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            if isinstance(data, list):
                for item in data:
                    msg_type = item.get("T")
                    
                    if msg_type == "q":  # Quote update
                        update = PriceUpdate(
                            ticker=item.get("S", ""),
                            price=(item.get("bp", 0) + item.get("ap", 0)) / 2,
                            bid=item.get("bp", 0),
                            ask=item.get("ap", 0),
                            timestamp=item.get("t", ""),
                            volume=0
                        )
                        
                        # Cache latest price
                        self.latest_prices[update.ticker] = update
                        
                        # Call callback if provided
                        if self.on_price_update:
                            self.on_price_update(update)
                    
                    elif msg_type == "t":  # Trade update
                        ticker = item.get("S", "")
                        if ticker in self.latest_prices:
                            self.latest_prices[ticker].price = item.get("p", 0)
                            self.latest_prices[ticker].volume = item.get("s", 0)
                            
                            if self.on_price_update:
                                self.on_price_update(self.latest_prices[ticker])
                                
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error handling message: {e}")
    
    def subscribe(self, tickers: List[str]):
        """Subscribe to additional tickers"""
        new_tickers = [t.upper() for t in tickers if t.upper() not in self._subscribed_tickers]
        
        if new_tickers and self._ws:
            self._subscribed_tickers.extend(new_tickers)
            
            subscribe_msg = {
                "action": "subscribe",
                "quotes": new_tickers
            }
            
            if self._loop and self._running:
                asyncio.run_coroutine_threadsafe(
                    self._ws.send(json.dumps(subscribe_msg)),
                    self._loop
                )
    
    def unsubscribe(self, tickers: List[str]):
        """Unsubscribe from tickers"""
        remove_tickers = [t.upper() for t in tickers if t.upper() in self._subscribed_tickers]
        
        if remove_tickers and self._ws:
            for t in remove_tickers:
                self._subscribed_tickers.remove(t)
            
            unsubscribe_msg = {
                "action": "unsubscribe",
                "quotes": remove_tickers
            }
            
            if self._loop and self._running:
                asyncio.run_coroutine_threadsafe(
                    self._ws.send(json.dumps(unsubscribe_msg)),
                    self._loop
                )
    
    def get_latest_price(self, ticker: str) -> Optional[float]:
        """Get the latest cached price for a ticker"""
        update = self.latest_prices.get(ticker.upper())
        return update.price if update else None
    
    def get_latest_update(self, ticker: str) -> Optional[PriceUpdate]:
        """Get the latest price update for a ticker"""
        return self.latest_prices.get(ticker.upper())


class StreamingPriceManager:
    """
    Manages WebSocket streaming and provides a simple interface
    for the Streamlit app to access real-time prices.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._ws_client: Optional[AlpacaWebSocket] = None
        self._price_callbacks: List[Callable] = []
        self._initialized = True
    
    def start_streaming(self, tickers: List[str]):
        """Start streaming prices for given tickers"""
        if self._ws_client:
            self._ws_client.subscribe(tickers)
        else:
            self._ws_client = AlpacaWebSocket(on_price_update=self._on_price_update)
            self._ws_client.start(tickers)
    
    def stop_streaming(self):
        """Stop all streaming"""
        if self._ws_client:
            self._ws_client.stop()
            self._ws_client = None
    
    def _on_price_update(self, update: PriceUpdate):
        """Handle incoming price update"""
        for callback in self._price_callbacks:
            try:
                callback(update)
            except Exception as e:
                print(f"Error in price callback: {e}")
    
    def add_callback(self, callback: Callable[[PriceUpdate], None]):
        """Add a callback for price updates"""
        self._price_callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove a price callback"""
        if callback in self._price_callbacks:
            self._price_callbacks.remove(callback)
    
    def get_price(self, ticker: str) -> Optional[float]:
        """Get latest price for a ticker"""
        if self._ws_client:
            return self._ws_client.get_latest_price(ticker)
        return None
    
    def get_update(self, ticker: str) -> Optional[PriceUpdate]:
        """Get latest full update for a ticker"""
        if self._ws_client:
            return self._ws_client.get_latest_update(ticker)
        return None


# Singleton instance
streaming_manager = StreamingPriceManager()
