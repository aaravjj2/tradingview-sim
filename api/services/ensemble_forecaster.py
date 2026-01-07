"""
Hybrid Ensemble Forecaster
Combines Monte Carlo, GARCH, and simplified ML for price forecasting
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


class EnsembleForecaster:
    """
    Hybrid forecaster combining:
    - Model A: Monte Carlo (Geometric Brownian Motion)
    - Model B: GARCH(1,1) for volatility clustering
    - Model C: Simple trend-following (replaces LSTM for speed)
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            'monte_carlo': 0.4,
            'garch': 0.35,
            'trend': 0.25
        }
        self.event_shocks: Dict[str, Dict] = {}
    
    def add_event_shock(self, date: str, event_type: str, iv_spike: float = 0.40):
        """
        Register an event (earnings, FOMC, CPI) for shock injection
        
        Args:
            date: ISO date string (YYYY-MM-DD)
            event_type: 'earnings', 'fomc', 'cpi'
            iv_spike: IV increase on event day (default 40%)
        """
        self.event_shocks[date] = {
            'type': event_type,
            'iv_spike': iv_spike,
            'iv_crush': 0.30  # Post-event IV crush
        }
    
    def _monte_carlo_paths(
        self, 
        current_price: float, 
        volatility: float, 
        days: int, 
        n_simulations: int = 1000,
        drift: float = 0.0
    ) -> np.ndarray:
        """Generate Monte Carlo price paths using GBM"""
        dt = 1 / 252  # Daily time step
        paths = np.zeros((n_simulations, days + 1))
        paths[:, 0] = current_price
        
        for t in range(1, days + 1):
            # Check for event shock on this day
            future_date = (datetime.now() + timedelta(days=t)).strftime('%Y-%m-%d')
            vol = volatility
            
            if future_date in self.event_shocks:
                shock = self.event_shocks[future_date]
                vol *= (1 + shock['iv_spike'])
            
            # GBM: dS = μSdt + σSdW
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
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fit GARCH(1,1) and forecast volatility
        Returns forecasted volatilities and simulated paths
        """
        if not HAS_ARCH or len(returns) < 30:
            # Fallback to simple historical vol
            hvol = np.std(returns) * np.sqrt(252)
            return np.full(days, hvol), np.zeros((n_simulations, days))
        
        try:
            # Fit GARCH(1,1)
            model = arch_model(returns * 100, vol='Garch', p=1, q=1, rescale=False)
            res = model.fit(disp='off', show_warning=False)
            
            # Forecast variance
            forecast = res.forecast(horizon=days)
            vol_forecast = np.sqrt(forecast.variance.values[-1, :]) / 100 * np.sqrt(252)
            
            return vol_forecast, res
        except Exception:
            hvol = np.std(returns) * np.sqrt(252)
            return np.full(days, hvol), None
    
    def _trend_forecast(
        self, 
        prices: np.ndarray, 
        days: int
    ) -> np.ndarray:
        """
        Simple trend-following forecast using EMA momentum
        Replaces LSTM for speed and simplicity
        """
        if len(prices) < 20:
            return np.full(days, prices[-1])
        
        # Calculate momentum
        ema_fast = self._ema(prices, 12)
        ema_slow = self._ema(prices, 26)
        
        # Momentum signal
        momentum = (ema_fast[-1] - ema_slow[-1]) / ema_slow[-1]
        
        # Project trend
        current = prices[-1]
        daily_drift = momentum / 20  # Spread momentum over ~20 days
        
        forecast = np.zeros(days + 1)
        forecast[0] = current
        
        for t in range(1, days + 1):
            # Decay momentum over time
            decay = np.exp(-t / 30)
            forecast[t] = forecast[t-1] * (1 + daily_drift * decay)
        
        return forecast[1:]
    
    def _ema(self, data: np.ndarray, span: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
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
        n_simulations: int = 1000
    ) -> Dict:
        """
        Generate ensemble forecast combining all models
        
        Args:
            current_price: Current asset price
            historical_prices: List of historical closing prices
            days: Forecast horizon
            base_iv: Base implied volatility
            n_simulations: Number of Monte Carlo paths
        
        Returns:
            Dict with percentile forecasts and confidence bands
        """
        prices = np.array(historical_prices)
        returns = np.diff(np.log(prices))
        
        # Model A: Monte Carlo paths
        mc_paths = self._monte_carlo_paths(
            current_price, base_iv, days, n_simulations
        )
        
        # Model B: GARCH volatility forecast
        garch_vols, _ = self._garch_forecast(returns, days, n_simulations)
        
        # Generate GARCH-adjusted paths
        garch_paths = self._monte_carlo_paths(
            current_price, 
            np.mean(garch_vols) if len(garch_vols) > 0 else base_iv,
            days, 
            n_simulations
        )
        
        # Model C: Trend forecast
        trend_forecast = self._trend_forecast(prices, days)
        
        # Ensemble: weighted combination
        ensemble_paths = (
            self.weights['monte_carlo'] * mc_paths +
            self.weights['garch'] * garch_paths +
            self.weights['trend'] * np.tile(trend_forecast, (n_simulations, 1))[:, :days+1]
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
            'p10': p10.tolist(),
            'p25': p25.tolist(),
            'p50': p50.tolist(),
            'p75': p75.tolist(),
            'p90': p90.tolist(),
            'trend_forecast': trend_forecast.tolist(),
            'garch_volatility': garch_vols.tolist() if isinstance(garch_vols, np.ndarray) else [base_iv] * days,
            'event_dates': list(self.event_shocks.keys())
        }
    
    def probability_above(
        self,
        current_price: float,
        target_price: float,
        historical_prices: List[float],
        days: int = 30,
        base_iv: float = 0.25
    ) -> float:
        """Calculate probability of price exceeding target"""
        forecast = self.forecast(current_price, historical_prices, days, base_iv, 5000)
        final_prices = np.array(forecast['p50'])  # Use median path
        
        # More accurate: run new simulation and count
        paths = self._monte_carlo_paths(current_price, base_iv, days, 5000)
        prob = np.mean(paths[:, -1] > target_price)
        
        return float(prob)
