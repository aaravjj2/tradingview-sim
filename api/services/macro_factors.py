"""
Macro Factor Regressors
Fetches and integrates macro factors (Treasury Yields, Dollar Index) for correlation analysis
"""

import os
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests

try:
    from fredapi import Fred
    HAS_FRED = True
except ImportError:
    HAS_FRED = False


class MacroFactors:
    """
    Fetches macro data from FRED API and calculates correlations
    for use in price simulations
    """
    
    # FRED Series IDs
    SERIES = {
        'treasury_10y': 'DGS10',      # 10-Year Treasury Yield
        'treasury_2y': 'DGS2',        # 2-Year Treasury Yield
        'dollar_index': 'DTWEXBGS',   # Trade Weighted Dollar Index
        'vix': 'VIXCLS',              # VIX Index
        'fed_funds': 'FEDFUNDS',      # Federal Funds Rate
        'inflation': 'CPIAUCSL',      # CPI
    }
    
    # Asset correlations with macro factors (simplified estimates)
    SECTOR_CORRELATIONS = {
        'tech': {'treasury_10y': -0.35, 'dollar_index': -0.20, 'vix': -0.65},
        'finance': {'treasury_10y': 0.40, 'dollar_index': 0.15, 'vix': -0.45},
        'energy': {'treasury_10y': 0.10, 'dollar_index': -0.30, 'vix': -0.40},
        'healthcare': {'treasury_10y': -0.15, 'dollar_index': -0.10, 'vix': -0.50},
        'consumer': {'treasury_10y': -0.20, 'dollar_index': -0.15, 'vix': -0.55},
        'default': {'treasury_10y': -0.15, 'dollar_index': -0.10, 'vix': -0.50}
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('FRED_API_KEY', '')
        self.fred = Fred(api_key=self.api_key) if HAS_FRED and self.api_key else None
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 hour cache
    
    def fetch_series(
        self, 
        series_id: str, 
        days_back: int = 252
    ) -> Optional[Dict]:
        """
        Fetch a FRED data series
        
        Args:
            series_id: FRED series identifier
            days_back: Number of days of history
        
        Returns:
            Dict with 'dates' and 'values' arrays
        """
        cache_key = f"{series_id}_{days_back}"
        
        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now().timestamp() - cached['timestamp'] < self.cache_ttl:
                return cached['data']
        
        if not self.fred:
            return self._get_mock_data(series_id, days_back)
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            data = self.fred.get_series(
                series_id, 
                observation_start=start_date,
                observation_end=end_date
            )
            
            result = {
                'dates': [d.strftime('%Y-%m-%d') for d in data.index],
                'values': data.values.tolist()
            }
            
            self.cache[cache_key] = {
                'timestamp': datetime.now().timestamp(),
                'data': result
            }
            
            return result
            
        except Exception as e:
            print(f"FRED API error: {e}")
            return self._get_mock_data(series_id, days_back)
    
    def _get_mock_data(self, series_id: str, days_back: int) -> Dict:
        """Generate mock data when FRED API unavailable"""
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') 
                 for i in range(days_back)]
        dates.reverse()
        
        # Generate realistic mock values based on series
        if 'DGS' in series_id:
            # Treasury yields: random walk around 4%
            base = 4.0
            values = base + np.cumsum(np.random.normal(0, 0.02, days_back))
            values = np.clip(values, 1.0, 7.0)
        elif 'DTWEX' in series_id:
            # Dollar index: random walk around 100
            base = 100.0
            values = base + np.cumsum(np.random.normal(0, 0.3, days_back))
            values = np.clip(values, 80, 120)
        elif 'VIX' in series_id:
            # VIX: mean-reverting around 18
            values = 18 + np.random.exponential(5, days_back)
            values = np.clip(values, 10, 50)
        else:
            values = np.random.normal(0, 1, days_back)
        
        return {'dates': dates, 'values': values.tolist()}
    
    def get_current_factors(self) -> Dict[str, float]:
        """Get current values for all macro factors"""
        factors = {}
        
        for name, series_id in self.SERIES.items():
            data = self.fetch_series(series_id, 10)
            if data and data['values']:
                # Get most recent non-NaN value
                values = [v for v in data['values'] if v is not None and not np.isnan(v)]
                if values:
                    factors[name] = values[-1]
        
        return factors
    
    def calculate_drift_adjustment(
        self,
        ticker: str,
        sector: str = 'default',
        lookback_days: int = 30
    ) -> Tuple[float, Dict]:
        """
        Calculate drift adjustment based on macro factor changes
        
        Args:
            ticker: Asset ticker
            sector: Sector classification
            lookback_days: Days to look back for change calculation
        
        Returns:
            Tuple of (drift_adjustment, factor_impacts)
        """
        correlations = self.SECTOR_CORRELATIONS.get(sector, self.SECTOR_CORRELATIONS['default'])
        
        factor_impacts = {}
        total_adjustment = 0.0
        
        for factor_name, correlation in correlations.items():
            series_id = self.SERIES.get(factor_name)
            if not series_id:
                continue
            
            data = self.fetch_series(series_id, lookback_days + 10)
            if not data or len(data['values']) < 2:
                continue
            
            values = [v for v in data['values'] if v is not None and not np.isnan(v)]
            if len(values) < 2:
                continue
            
            # Calculate factor change (normalized)
            recent = np.mean(values[-5:]) if len(values) >= 5 else values[-1]
            past = np.mean(values[:5]) if len(values) >= 5 else values[0]
            
            if past == 0:
                continue
            
            pct_change = (recent - past) / abs(past)
            
            # Impact = correlation * factor_change
            impact = correlation * pct_change * 0.1  # Scale down
            
            factor_impacts[factor_name] = {
                'current': recent,
                'past': past,
                'change': pct_change,
                'correlation': correlation,
                'impact': impact
            }
            
            total_adjustment += impact
        
        return total_adjustment, factor_impacts
    
    def get_yield_curve_signal(self) -> Dict:
        """
        Analyze yield curve for recession signal
        
        Returns:
            Dict with curve shape and signal
        """
        y10 = self.fetch_series('DGS10', 10)
        y2 = self.fetch_series('DGS2', 10)
        
        if not y10 or not y2:
            return {'signal': 'neutral', 'spread': 0}
        
        # Get latest values
        y10_val = [v for v in y10['values'] if v and not np.isnan(v)][-1] if y10['values'] else 4.0
        y2_val = [v for v in y2['values'] if v and not np.isnan(v)][-1] if y2['values'] else 4.0
        
        spread = y10_val - y2_val
        
        if spread < -0.2:
            signal = 'inverted'  # Recession warning
        elif spread < 0.5:
            signal = 'flat'  # Slowing growth
        else:
            signal = 'normal'  # Healthy
        
        return {
            'signal': signal,
            'spread': spread,
            '10y': y10_val,
            '2y': y2_val
        }
