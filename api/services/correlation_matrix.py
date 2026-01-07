"""
Correlation Trading Matrix
Analyze correlations between assets for pairs trading and hedging
"""

from typing import Dict, List, Tuple
import math
import random
from datetime import datetime, timedelta


def calculate_returns(prices: List[float]) -> List[float]:
    """Calculate log returns from price series"""
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] > 0:
            returns.append(math.log(prices[i] / prices[i-1]))
        else:
            returns.append(0)
    return returns


def calculate_correlation(returns1: List[float], returns2: List[float]) -> float:
    """Calculate Pearson correlation coefficient"""
    n = min(len(returns1), len(returns2))
    if n < 2:
        return 0
    
    mean1 = sum(returns1[:n]) / n
    mean2 = sum(returns2[:n]) / n
    
    numerator = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(n))
    
    var1 = sum((r - mean1) ** 2 for r in returns1[:n])
    var2 = sum((r - mean2) ** 2 for r in returns2[:n])
    
    denominator = math.sqrt(var1 * var2)
    
    if denominator == 0:
        return 0
    
    return numerator / denominator


def calculate_beta(asset_returns: List[float], market_returns: List[float]) -> float:
    """Calculate beta of asset relative to market"""
    correlation = calculate_correlation(asset_returns, market_returns)
    
    n = len(market_returns)
    if n < 2:
        return 1.0
    
    mean_market = sum(market_returns) / n
    var_market = sum((r - mean_market) ** 2 for r in market_returns) / n
    
    mean_asset = sum(asset_returns) / n
    std_asset = math.sqrt(sum((r - mean_asset) ** 2 for r in asset_returns) / n)
    std_market = math.sqrt(var_market)
    
    if std_market == 0:
        return 1.0
    
    return correlation * std_asset / std_market


class CorrelationMatrix:
    """
    Multi-asset Correlation Matrix
    
    Features:
    - Rolling correlation windows
    - Correlation breakdown detection
    - Pairs trading opportunities
    - Hedge ratio calculation
    """
    
    def __init__(self):
        self.price_data: Dict[str, List[float]] = {}
        self.returns_data: Dict[str, List[float]] = {}
    
    def add_price_series(self, ticker: str, prices: List[float]):
        """Add price data for an asset"""
        self.price_data[ticker] = prices
        self.returns_data[ticker] = calculate_returns(prices)
    
    def generate_sample_data(self, tickers: List[str], days: int = 252):
        """Generate correlated sample data for testing"""
        # Base market factor
        market_returns = [random.gauss(0.0005, 0.015) for _ in range(days)]
        
        correlations = {
            "SPY": 1.0,
            "QQQ": 0.92,
            "IWM": 0.85,
            "GLD": -0.15,
            "TLT": -0.35,
            "VXX": -0.75,
            "AAPL": 0.78,
            "NVDA": 0.72,
            "XLE": 0.55,
            "XLF": 0.80
        }
        
        for ticker in tickers:
            corr = correlations.get(ticker, 0.5)
            idio_weight = math.sqrt(1 - corr ** 2)
            
            # Generate correlated returns
            ticker_returns = []
            for mr in market_returns:
                idio_return = random.gauss(0, 0.02)
                combined = corr * mr + idio_weight * idio_return
                ticker_returns.append(combined)
            
            # Convert to prices
            price = 100
            prices = [price]
            for r in ticker_returns:
                price *= math.exp(r)
                prices.append(price)
            
            self.add_price_series(ticker, prices)
    
    def get_correlation_matrix(self, lookback: int = None) -> Dict:
        """Calculate full correlation matrix"""
        tickers = list(self.returns_data.keys())
        n = len(tickers)
        
        matrix = {}
        
        for i, ticker1 in enumerate(tickers):
            matrix[ticker1] = {}
            returns1 = self.returns_data[ticker1]
            if lookback:
                returns1 = returns1[-lookback:]
            
            for j, ticker2 in enumerate(tickers):
                returns2 = self.returns_data[ticker2]
                if lookback:
                    returns2 = returns2[-lookback:]
                
                corr = calculate_correlation(returns1, returns2)
                matrix[ticker1][ticker2] = round(corr, 3)
        
        return matrix
    
    def find_pairs_opportunities(
        self,
        min_correlation: float = 0.7,
        lookback: int = 60
    ) -> List[Dict]:
        """Find potential pairs trading opportunities"""
        tickers = list(self.returns_data.keys())
        opportunities = []
        
        for i, ticker1 in enumerate(tickers):
            for j, ticker2 in enumerate(tickers):
                if i >= j:
                    continue
                
                returns1 = self.returns_data[ticker1][-lookback:]
                returns2 = self.returns_data[ticker2][-lookback:]
                
                corr = calculate_correlation(returns1, returns2)
                
                if abs(corr) >= min_correlation:
                    # Calculate spread statistics
                    prices1 = self.price_data[ticker1][-lookback:]
                    prices2 = self.price_data[ticker2][-lookback:]
                    
                    # Simple ratio spread
                    if prices2[0] > 0:
                        ratio = prices1[0] / prices2[0]
                        spread = [p1 - ratio * p2 for p1, p2 in zip(prices1, prices2)]
                        
                        mean_spread = sum(spread) / len(spread)
                        std_spread = math.sqrt(sum((s - mean_spread) ** 2 for s in spread) / len(spread))
                        current_spread = spread[-1]
                        z_score = (current_spread - mean_spread) / std_spread if std_spread > 0 else 0
                        
                        opportunities.append({
                            "pair": f"{ticker1}/{ticker2}",
                            "ticker1": ticker1,
                            "ticker2": ticker2,
                            "correlation": round(corr, 3),
                            "hedge_ratio": round(ratio, 4),
                            "z_score": round(z_score, 2),
                            "mean_spread": round(mean_spread, 2),
                            "current_spread": round(current_spread, 2),
                            "signal": "short_spread" if z_score > 2 else "long_spread" if z_score < -2 else "neutral"
                        })
        
        # Sort by absolute z-score
        opportunities.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        
        return opportunities
    
    def detect_correlation_breakdown(
        self,
        ticker1: str,
        ticker2: str,
        short_window: int = 20,
        long_window: int = 60
    ) -> Dict:
        """Detect if correlation is breaking down"""
        returns1 = self.returns_data.get(ticker1, [])
        returns2 = self.returns_data.get(ticker2, [])
        
        if len(returns1) < long_window or len(returns2) < long_window:
            return {"error": "Insufficient data"}
        
        short_corr = calculate_correlation(returns1[-short_window:], returns2[-short_window:])
        long_corr = calculate_correlation(returns1[-long_window:], returns2[-long_window:])
        
        correlation_change = short_corr - long_corr
        
        return {
            "pair": f"{ticker1}/{ticker2}",
            "short_term_correlation": round(short_corr, 3),
            "long_term_correlation": round(long_corr, 3),
            "correlation_change": round(correlation_change, 3),
            "breakdown_detected": abs(correlation_change) > 0.2,
            "direction": "strengthening" if correlation_change > 0 else "weakening"
        }


# Global instance
_correlation_matrix: CorrelationMatrix = None


def get_correlation_matrix() -> CorrelationMatrix:
    global _correlation_matrix
    if _correlation_matrix is None:
        _correlation_matrix = CorrelationMatrix()
    return _correlation_matrix


async def analyze_correlations(
    tickers: List[str],
    lookback: int = 60
) -> Dict:
    """API helper for correlation analysis"""
    matrix = get_correlation_matrix()
    
    # Generate sample data if empty
    if not matrix.price_data:
        matrix.generate_sample_data(tickers, days=252)
    
    return {
        "tickers": tickers,
        "lookback_days": lookback,
        "correlation_matrix": matrix.get_correlation_matrix(lookback),
        "pairs_opportunities": matrix.find_pairs_opportunities(0.6, lookback),
        "timestamp": datetime.now().isoformat()
    }


async def get_pairs_signals(min_correlation: float = 0.7) -> List[Dict]:
    """Get current pairs trading signals"""
    matrix = get_correlation_matrix()
    
    if not matrix.price_data:
        default_tickers = ["SPY", "QQQ", "IWM", "GLD", "TLT", "AAPL", "NVDA"]
        matrix.generate_sample_data(default_tickers)
    
    return matrix.find_pairs_opportunities(min_correlation)
