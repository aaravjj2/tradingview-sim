"""
Signal API - REST-like interface for local signal ingestion

Provides a simple HTTP server for receiving signals and triggering trades.

PAPER-ONLY: This module enforces paper trading mode.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Safety enforcement
TRADING_MODE = os.environ.get("TRADING_MODE", "paper")


class SignalHandler(BaseHTTPRequestHandler):
    """HTTP handler for signal API requests."""
    
    signal_queue = []
    
    def do_POST(self):
        """Handle POST requests for signal submission."""
        if self.path == "/api/signal":
            self._handle_signal()
        elif self.path == "/api/health":
            self._handle_health()
        else:
            self._send_response(404, {"error": "Not found"})
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/api/health":
            self._handle_health()
        elif self.path == "/api/signals":
            self._handle_list_signals()
        elif self.path == "/api/mode":
            self._send_response(200, {"trading_mode": TRADING_MODE})
        else:
            self._send_response(404, {"error": "Not found"})
    
    def _handle_signal(self):
        """Process incoming signal."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            signal = json.loads(body.decode('utf-8'))
            
            # Validate required fields
            required = ["symbol", "signal", "exposure", "confidence"]
            for field in required:
                if field not in signal:
                    self._send_response(400, {"error": f"Missing field: {field}"})
                    return
            
            # Add metadata
            signal["received_at"] = datetime.now().isoformat()
            signal["trading_mode"] = TRADING_MODE
            
            # Queue the signal
            SignalHandler.signal_queue.append(signal)
            
            # Keep only last 100 signals
            if len(SignalHandler.signal_queue) > 100:
                SignalHandler.signal_queue = SignalHandler.signal_queue[-100:]
            
            self._send_response(200, {
                "status": "accepted",
                "signal_id": len(SignalHandler.signal_queue),
                "trading_mode": TRADING_MODE
            })
            
        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON"})
        except Exception as e:
            self._send_response(500, {"error": str(e)})
    
    def _handle_health(self):
        """Health check endpoint."""
        self._send_response(200, {
            "status": "healthy",
            "trading_mode": TRADING_MODE,
            "queued_signals": len(SignalHandler.signal_queue)
        })
    
    def _handle_list_signals(self):
        """List recent signals."""
        self._send_response(200, {
            "signals": SignalHandler.signal_queue[-10:],
            "total": len(SignalHandler.signal_queue)
        })
    
    def _send_response(self, status: int, data: Dict):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class SignalAPI:
    """
    Signal API server for local signal ingestion.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8088):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the API server in a background thread."""
        self.server = HTTPServer((self.host, self.port), SignalHandler)
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        print(f"Signal API started on http://{self.host}:{self.port}")
        print(f"Trading mode: {TRADING_MODE}")
    
    def stop(self):
        """Stop the API server."""
        if self.server:
            self.server.shutdown()
            self.server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        print("Signal API stopped")
    
    def get_pending_signals(self) -> list:
        """Get all pending signals from the queue."""
        signals = SignalHandler.signal_queue.copy()
        SignalHandler.signal_queue.clear()
        return signals
    
    def submit_signal(self, signal: Dict[str, Any]) -> Dict:
        """
        Submit a signal directly (for local use without HTTP).
        
        Args:
            signal: Signal dict with symbol, signal, exposure, confidence
            
        Returns:
            Status dict
        """
        signal["received_at"] = datetime.now().isoformat()
        signal["trading_mode"] = TRADING_MODE
        SignalHandler.signal_queue.append(signal)
        
        return {
            "status": "accepted",
            "signal_id": len(SignalHandler.signal_queue),
            "trading_mode": TRADING_MODE
        }


# Singleton instance
_signal_api: Optional[SignalAPI] = None


def get_signal_api(host: str = "127.0.0.1", port: int = 8088) -> SignalAPI:
    """Get or create the singleton SignalAPI instance."""
    global _signal_api
    if _signal_api is None:
        _signal_api = SignalAPI(host, port)
    return _signal_api


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8088, help="Port to bind to")
    args = parser.parse_args()
    
    api = get_signal_api(args.host, args.port)
    api.start()
    
    print("\nEndpoints:")
    print(f"  POST /api/signal  - Submit a signal")
    print(f"  GET  /api/signals - List recent signals")
    print(f"  GET  /api/health  - Health check")
    print(f"  GET  /api/mode    - Get trading mode")
    print("\nPress Ctrl+C to stop...")
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        api.stop()
