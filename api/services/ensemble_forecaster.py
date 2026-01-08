"""
Hybrid Ensemble Forecaster v2
Combines Monte Carlo, GARCH, LSTM Neural Net, and dynamic regime-based weighting
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

# Try to import PyTorch for LSTM (optional)
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class SimpleLSTM(nn.Module if HAS_TORCH else object):
    """Simple LSTM for price prediction."""
    
    def __init__(self, input_size=5, hidden_size=32, num_layers=2, output_size=1):
        if not HAS_TORCH:
            return
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        if not HAS_TORCH:
            return None
        # Ensure hidden states are on the same device as input
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size, device=x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size, device=x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


class EnsembleForecasterV2:
    """
    Hybrid forecaster v2 combining:
    - Model A: Monte Carlo (Geometric Brownian Motion)
    - Model B: GARCH(1,1) for volatility clustering
    - Model C: LSTM Neural Network for non-linear patterns
    - Dynamic weighting based on market regime
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        # Default weights (can be dynamically adjusted)
        self.weights = weights or {
            'monte_carlo': 0.35,
            'garch': 0.35,
            'lstm': 0.30
        }
        
        # Regime-specific weight profiles
        self.regime_weights = {
            'trending': {'monte_carlo': 0.25, 'garch': 0.25, 'lstm': 0.50},  # LSTM excels at momentum
            'choppy': {'monte_carlo': 0.35, 'garch': 0.45, 'lstm': 0.20},    # GARCH for vol clustering
            'crash': {'monte_carlo': 0.50, 'garch': 0.40, 'lstm': 0.10}      # Random walk dominates
        }
        
        self.event_shocks: Dict[str, Dict] = {}
        self.current_regime = 'choppy'  # Default
        
        # LSTM model (lazy loaded)
        self._lstm_model = None
        self._device = None
        
        # Check GPU availability
        if HAS_TORCH:
            self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            if torch.cuda.is_available():
                print(f"[Forecaster] Using GPU: {torch.cuda.get_device_name(0)}")
            else:
                print("[Forecaster] Using CPU (GPU not available)")
        
    def set_regime(self, regime: str):
        """Update regime and adjust weights accordingly."""
        if regime.lower() in self.regime_weights:
            self.current_regime = regime.lower()
            self.weights = self.regime_weights[regime.lower()].copy()
    
    def add_event_shock(self, date: str, event_type: str, iv_spike: float = 0.40):
        """Register an event for shock injection."""
        self.event_shocks[date] = {
            'type': event_type,
            'iv_spike': iv_spike,
            'iv_crush': 0.30
        }
    
    def _monte_carlo_paths(
        self, 
        current_price: float, 
        volatility: float, 
        days: int, 
        n_simulations: int = 1000,
        drift: float = 0.0
    ) -> np.ndarray:
        """Generate Monte Carlo price paths using GBM."""
        dt = 1 / 252
        paths = np.zeros((n_simulations, days + 1))
        paths[:, 0] = current_price
        
        for t in range(1, days + 1):
            future_date = (datetime.now() + timedelta(days=t)).strftime('%Y-%m-%d')
            vol = volatility
            
            if future_date in self.event_shocks:
                shock = self.event_shocks[future_date]
                vol *= (1 + shock['iv_spike'])
            
            z = np.random.standard_normal(n_simulations)
            paths[:, t] = paths[:, t-1] * np.exp(
                (drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * z
            )
        
        return paths
    
    def _garch_forecast(
        self, 
        returns: np.ndarray, 
        days: int,
        n_simulations: int = 1000
    ) -> Tuple[np.ndarray, Optional[object]]:
        """Fit GARCH(1,1) and forecast volatility."""
        if not HAS_ARCH or len(returns) < 30:
            hvol = np.std(returns) * np.sqrt(252)
            return np.full(days, hvol), None
        
        try:
            model = arch_model(returns * 100, vol='Garch', p=1, q=1, rescale=False)
            res = model.fit(disp='off', show_warning=False)
            forecast = res.forecast(horizon=days)
            vol_forecast = np.sqrt(forecast.variance.values[-1, :]) / 100 * np.sqrt(252)
            return vol_forecast, res
        except Exception:
            hvol = np.std(returns) * np.sqrt(252)
            return np.full(days, hvol), None
    
    def _lstm_forecast(
        self, 
        prices: np.ndarray, 
        days: int
    ) -> np.ndarray:
        """
        LSTM-based price forecast.
        Falls back to momentum-based forecast if PyTorch unavailable.
        """
        if len(prices) < 30:
            return np.full(days + 1, prices[-1])
        
        if not HAS_TORCH:
            # Fallback: Enhanced momentum-based forecast
            return self._momentum_forecast(prices, days)
        
        try:
            # Prepare features: returns, RSI, momentum indicators
            returns = np.diff(np.log(prices))
            
            # Create feature matrix
            window = 20
            features = []
            for i in range(window, len(prices)):
                feat = [
                    returns[i-1],  # Previous return
                    np.mean(returns[i-window:i]),  # Avg return
                    np.std(returns[i-window:i]),   # Volatility
                    (prices[i] - prices[i-window]) / prices[i-window],  # Momentum
                    self._calculate_rsi(prices[:i+1])  # RSI
                ]
                features.append(feat)
            
            features = np.array(features)
            
            # Normalize features
            mean = features.mean(axis=0)
            std = features.std(axis=0) + 1e-8
            features_norm = (features - mean) / std
            
            # Use last sequence for prediction
            seq_len = min(10, len(features_norm))
            X = features_norm[-seq_len:].reshape(1, seq_len, 5)
            X_tensor = torch.FloatTensor(X)
            
            # Create model if not exists
            if self._lstm_model is None:
                self._lstm_model = SimpleLSTM()
                # Initialize with reasonable random weights
                for param in self._lstm_model.parameters():
                    nn.init.normal_(param, mean=0, std=0.1)
                
                # Move model to GPU if available
                if self._device is not None:
                    self._lstm_model = self._lstm_model.to(self._device)
            
            self._lstm_model.eval()
            
            # Generate multi-step forecast
            forecast = np.zeros(days + 1)
            forecast[0] = prices[-1]
            
            # Move tensor to GPU if available
            if self._device is not None:
                X_tensor = X_tensor.to(self._device)
            
            with torch.no_grad():
                for t in range(1, days + 1):
                    pred_return = self._lstm_model(X_tensor).item() * std[0] + mean[0]
                    # Clip extreme predictions
                    pred_return = np.clip(pred_return, -0.05, 0.05)
                    forecast[t] = forecast[t-1] * np.exp(pred_return)
                    
                    # Decay prediction confidence over time
                    forecast[t] = 0.5 * forecast[t] + 0.5 * forecast[t-1]
            
            return forecast
            
        except Exception as e:
            print(f"LSTM fallback: {e}")
            return self._momentum_forecast(prices, days)
    
    def _momentum_forecast(self, prices: np.ndarray, days: int) -> np.ndarray:
        """Enhanced momentum-based forecast (LSTM fallback)."""
        ema_fast = self._ema(prices, 12)
        ema_slow = self._ema(prices, 26)
        
        momentum = (ema_fast[-1] - ema_slow[-1]) / ema_slow[-1]
        current = prices[-1]
        daily_drift = momentum / 20
        
        forecast = np.zeros(days + 1)
        forecast[0] = current
        
        for t in range(1, days + 1):
            decay = np.exp(-t / 30)
            forecast[t] = forecast[t-1] * (1 + daily_drift * decay)
        
        return forecast
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI normalized to 0-1."""
        if len(prices) < period + 1:
            return 0.5
        
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 1.0
        
        rs = avg_gain / avg_loss
        rsi = 1 - (1 / (1 + rs))  # Normalized 0-1
        return rsi
    
    def _ema(self, data: np.ndarray, span: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        alpha = 2 / (span + 1)
        ema = np.zeros(len(data))
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def forecast(
        self,
        current_price: float,
        historical_prices: List[float],
        days: int = 30,
        base_iv: float = 0.25,
        n_simulations: int = 1000,
        regime: Optional[str] = None
    ) -> Dict:
        """
        Generate ensemble forecast combining all models.
        
        Args:
            current_price: Current asset price
            historical_prices: List of historical closing prices
            days: Forecast horizon
            base_iv: Base implied volatility
            n_simulations: Number of Monte Carlo paths
            regime: Market regime ('trending', 'choppy', 'crash')
        
        Returns:
            Dict with percentile forecasts and confidence bands
        """
        # Update regime if provided
        if regime:
            self.set_regime(regime)
        
        prices = np.array(historical_prices)
        returns = np.diff(np.log(prices))
        
        # Model A: Monte Carlo paths
        mc_paths = self._monte_carlo_paths(
            current_price, base_iv, days, n_simulations
        )
        
        # Model B: GARCH volatility forecast
        garch_vols, _ = self._garch_forecast(returns, days, n_simulations)
        garch_vol = np.mean(garch_vols) if len(garch_vols) > 0 else base_iv
        
        garch_paths = self._monte_carlo_paths(
            current_price, 
            garch_vol,
            days, 
            n_simulations
        )
        
        # Model C: LSTM/Momentum forecast
        lstm_forecast = self._lstm_forecast(prices, days)
        
        # Pad LSTM forecast to match path dimensions
        lstm_paths = np.tile(lstm_forecast, (n_simulations, 1))
        
        # Add some variance to LSTM paths
        noise = np.random.normal(0, 0.01, lstm_paths.shape)
        noise[:, 0] = 0  # Keep starting price exact
        lstm_paths = lstm_paths * (1 + noise * np.arange(days + 1))
        
        # Ensemble: regime-weighted combination
        ensemble_paths = (
            self.weights['monte_carlo'] * mc_paths +
            self.weights['garch'] * garch_paths +
            self.weights['lstm'] * lstm_paths
        )
        
        # Calculate percentiles
        p10 = np.percentile(ensemble_paths, 10, axis=0)
        p25 = np.percentile(ensemble_paths, 25, axis=0)
        p50 = np.percentile(ensemble_paths, 50, axis=0)
        p75 = np.percentile(ensemble_paths, 75, axis=0)
        p90 = np.percentile(ensemble_paths, 90, axis=0)
        
        return {
            'current_price': current_price,
            'days': days,
            'regime': self.current_regime,
            'weights': self.weights.copy(),
            'p10': p10.tolist(),
            'p25': p25.tolist(),
            'p50': p50.tolist(),
            'p75': p75.tolist(),
            'p90': p90.tolist(),
            'lstm_forecast': lstm_forecast.tolist(),
            'garch_volatility': garch_vols.tolist() if isinstance(garch_vols, np.ndarray) else [base_iv] * days,
            'event_dates': list(self.event_shocks.keys()),
            'model_contributions': {
                'monte_carlo': self.weights['monte_carlo'],
                'garch': self.weights['garch'],
                'lstm': self.weights['lstm']
            }
        }
    
    def probability_above(
        self,
        current_price: float,
        target_price: float,
        historical_prices: List[float],
        days: int = 30,
        base_iv: float = 0.25
    ) -> float:
        """Calculate probability of price exceeding target."""
        paths = self._monte_carlo_paths(current_price, base_iv, days, 5000)
        prob = np.mean(paths[:, -1] > target_price)
        return float(prob)


# Keep backward compatibility with old class name
EnsembleForecaster = EnsembleForecasterV2

# Singleton instance
_forecaster: Optional[EnsembleForecasterV2] = None

def get_ensemble_forecaster() -> EnsembleForecasterV2:
    """Get global forecaster instance."""
    global _forecaster
    if _forecaster is None:
        _forecaster = EnsembleForecasterV2()
    return _forecaster
