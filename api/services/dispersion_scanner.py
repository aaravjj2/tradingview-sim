"""
Dispersion Trading Scanner
Find opportunities where index IV differs significantly from component IVs
"""

from typing import Dict, List
import math
import random
from datetime import datetime


class DispersionScanner:
    """
    Dispersion Trading Scanner
    
    Dispersion = Long index straddle + Short component straddles
    (or vice versa)
    
    Profitable when:
    - Implied correlation is mispriced
    - Index IV vs component IV relationship breaks down
    """
    
    # Major index compositions (simplified)
    INDEX_COMPONENTS = {
        "SPY": {
            "weights": {
                "AAPL": 0.07, "MSFT": 0.07, "AMZN": 0.03, "NVDA": 0.03,
                "GOOGL": 0.02, "META": 0.02, "TSLA": 0.02, "BRK.B": 0.02,
                "UNH": 0.01, "JNJ": 0.01
            },
            "top_10_weight": 0.30
        },
        "QQQ": {
            "weights": {
                "AAPL": 0.12, "MSFT": 0.10, "AMZN": 0.06, "NVDA": 0.05,
                "META": 0.04, "GOOGL": 0.04, "TSLA": 0.03, "AVGO": 0.03,
                "COST": 0.02, "PEP": 0.02
            },
            "top_10_weight": 0.51
        }
    }
    
    def __init__(self):
        self.iv_data: Dict[str, float] = {}
        self.last_scan: Dict = {}
    
    def set_iv_data(self, ticker: str, iv: float):
        """Set IV for a ticker"""
        self.iv_data[ticker] = iv
    
    def generate_sample_ivs(self, index: str = "SPY"):
        """Generate sample IV data for testing"""
        components = self.INDEX_COMPONENTS.get(index, self.INDEX_COMPONENTS["SPY"])
        
        # Index IV
        base_iv = 0.20 + random.uniform(-0.05, 0.05)
        self.iv_data[index] = base_iv
        
        # Component IVs (typically higher than index due to diversification)
        for ticker in components["weights"]:
            # Components have higher IV, with some variance
            component_iv = base_iv * (1.3 + random.uniform(0, 0.4))
            self.iv_data[ticker] = component_iv
    
    def calculate_implied_correlation(self, index: str) -> Dict:
        """
        Calculate implied correlation from IVs
        
        Index variance ≈ Σ w_i^2 * σ_i^2 + Σ Σ w_i * w_j * ρ_ij * σ_i * σ_j
        
        Simplified: ρ_implied ≈ (σ_index^2 - Σ w_i^2 * σ_i^2) / (2 * Σ' w_i * w_j * σ_i * σ_j)
        """
        if index not in self.INDEX_COMPONENTS:
            return {"error": f"Unknown index: {index}"}
        
        config = self.INDEX_COMPONENTS[index]
        weights = config["weights"]
        
        index_iv = self.iv_data.get(index)
        if not index_iv:
            return {"error": f"No IV data for {index}"}
        
        # Calculate weighted average component IV
        weighted_iv = 0
        total_weight = 0
        component_ivs = {}
        
        for ticker, weight in weights.items():
            iv = self.iv_data.get(ticker, index_iv * 1.5)
            component_ivs[ticker] = iv
            weighted_iv += weight * iv
            total_weight += weight
        
        if total_weight > 0:
            avg_component_iv = weighted_iv / total_weight
        else:
            avg_component_iv = index_iv * 1.3
        
        # Implied correlation estimate
        # ρ ≈ (σ_index / σ_avg_component)^2
        # This is a simplification; real calculation is more complex
        implied_correlation = min(1.0, (index_iv / avg_component_iv) ** 2)
        
        return {
            "index": index,
            "index_iv": round(index_iv * 100, 2),
            "avg_component_iv": round(avg_component_iv * 100, 2),
            "implied_correlation": round(implied_correlation, 3),
            "component_ivs": {k: round(v * 100, 2) for k, v in component_ivs.items()}
        }
    
    def scan_dispersion_opportunity(self, index: str) -> Dict:
        """
        Scan for dispersion trading opportunities
        """
        corr_data = self.calculate_implied_correlation(index)
        if "error" in corr_data:
            return corr_data
        
        implied_corr = corr_data["implied_correlation"]
        index_iv = corr_data["index_iv"]
        avg_comp_iv = corr_data["avg_component_iv"]
        
        # Historical average correlation (assumed)
        historical_corr = 0.55  # SPY components usually ~55% correlated
        
        # Dispersion ratio
        dispersion_ratio = avg_comp_iv / index_iv
        
        # Opportunity detection
        if implied_corr > historical_corr + 0.15:
            opportunity = "sell_dispersion"
            signal = "SELL index straddle, BUY component straddles"
            rationale = "Implied correlation is too high vs historical"
            strength = "strong" if implied_corr > historical_corr + 0.25 else "moderate"
        elif implied_corr < historical_corr - 0.15:
            opportunity = "buy_dispersion"
            signal = "BUY index straddle, SELL component straddles"
            rationale = "Implied correlation is too low vs historical"
            strength = "strong" if implied_corr < historical_corr - 0.25 else "moderate"
        else:
            opportunity = "neutral"
            signal = "No clear dispersion trade"
            rationale = "Implied correlation near historical average"
            strength = "none"
        
        # Calculate edge
        edge = abs(implied_corr - historical_corr) * avg_comp_iv * 100
        
        return {
            "index": index,
            "opportunity": opportunity,
            "signal": signal,
            "strength": strength,
            "rationale": rationale,
            "metrics": {
                "implied_correlation": implied_corr,
                "historical_correlation": historical_corr,
                "correlation_diff": round(implied_corr - historical_corr, 3),
                "dispersion_ratio": round(dispersion_ratio, 2),
                "estimated_edge_pct": round(edge, 2)
            },
            "iv_data": {
                "index_iv": index_iv,
                "avg_component_iv": avg_comp_iv,
                "iv_spread": round(avg_comp_iv - index_iv, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_component_rankings(self, index: str) -> List[Dict]:
        """
        Rank components by IV relative to index
        Useful for selecting which components to trade
        """
        if index not in self.INDEX_COMPONENTS:
            return []
        
        config = self.INDEX_COMPONENTS[index]
        weights = config["weights"]
        index_iv = self.iv_data.get(index, 0.20)
        
        rankings = []
        for ticker, weight in weights.items():
            comp_iv = self.iv_data.get(ticker, index_iv * 1.5)
            iv_ratio = comp_iv / index_iv if index_iv > 0 else 1
            
            rankings.append({
                "ticker": ticker,
                "weight": weight,
                "iv_pct": round(comp_iv * 100, 2),
                "iv_ratio": round(iv_ratio, 2),
                "relative_value": "cheap" if iv_ratio < 1.2 else "fair" if iv_ratio < 1.5 else "expensive"
            })
        
        # Sort by IV ratio (descending = most expensive first)
        rankings.sort(key=lambda x: x["iv_ratio"], reverse=True)
        
        return rankings


# Global scanner instance
_scanner: DispersionScanner = None


def get_scanner() -> DispersionScanner:
    global _scanner
    if _scanner is None:
        _scanner = DispersionScanner()
    return _scanner


async def scan_dispersion(index: str = "SPY") -> Dict:
    """API helper for dispersion scanning"""
    scanner = get_scanner()
    
    # Generate sample data if empty
    if index not in scanner.iv_data:
        scanner.generate_sample_ivs(index)
    
    return scanner.scan_dispersion_opportunity(index)


async def get_dispersion_rankings(index: str = "SPY") -> List[Dict]:
    """Get component IV rankings"""
    scanner = get_scanner()
    
    if index not in scanner.iv_data:
        scanner.generate_sample_ivs(index)
    
    return scanner.get_component_rankings(index)
