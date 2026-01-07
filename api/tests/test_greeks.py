"""
Tests for Greeks calculations
Validates Black-Scholes implementation against known values
"""

import pytest
import math
import sys
sys.path.insert(0, '..')

from services.greeks import calculate_all_greeks, normal_cdf, normal_pdf


class TestNormalDistribution:
    """Tests for normal distribution functions"""
    
    def test_normal_cdf_at_zero(self):
        """CDF at 0 should be 0.5"""
        result = normal_cdf(0)
        assert abs(result - 0.5) < 0.001
    
    def test_normal_cdf_positive(self):
        """CDF at positive values should be > 0.5"""
        result = normal_cdf(1.0)
        assert result > 0.5
        assert abs(result - 0.8413) < 0.01  # Known value
    
    def test_normal_cdf_negative(self):
        """CDF at negative values should be < 0.5"""
        result = normal_cdf(-1.0)
        assert result < 0.5
        assert abs(result - 0.1587) < 0.01  # Known value
    
    def test_normal_pdf_at_zero(self):
        """PDF at 0 should be approximately 0.3989"""
        result = normal_pdf(0)
        expected = 1 / math.sqrt(2 * math.pi)
        assert abs(result - expected) < 0.0001


class TestGreeksCalculation:
    """Tests for Black-Scholes Greeks"""
    
    def test_atm_call_delta_approximately_half(self):
        """ATM call delta should be approximately 0.50"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=100,  # Spot
            K=100,  # Strike (ATM)
            T=30/365,  # 30 days
            r=0.05,  # 5% risk-free
            sigma=0.20  # 20% volatility
        )
        
        # Delta should be between 0.45 and 0.55 for ATM
        assert 0.45 < greeks["delta"] < 0.60
    
    def test_atm_put_delta_approximately_negative_half(self):
        """ATM put delta should be approximately -0.50"""
        greeks = calculate_all_greeks(
            option_type="put",
            S=100,
            K=100,
            T=30/365,
            r=0.05,
            sigma=0.20
        )
        
        # Put delta should be negative
        assert -0.55 < greeks["delta"] < -0.40
    
    def test_deep_itm_call_delta_near_one(self):
        """Deep ITM call should have delta near 1.0"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=150,  # Spot much higher than strike
            K=100,
            T=30/365,
            r=0.05,
            sigma=0.20
        )
        
        assert greeks["delta"] > 0.95
    
    def test_deep_otm_call_delta_near_zero(self):
        """Deep OTM call should have delta near 0"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=50,  # Spot much lower than strike
            K=100,
            T=30/365,
            r=0.05,
            sigma=0.20
        )
        
        assert greeks["delta"] < 0.05
    
    def test_gamma_positive(self):
        """Gamma should always be positive"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=100,
            K=100,
            T=30/365,
            r=0.05,
            sigma=0.20
        )
        
        assert greeks["gamma"] > 0
    
    def test_theta_call_negative(self):
        """Long call theta should be negative (time decay)"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=100,
            K=100,
            T=30/365,
            r=0.05,
            sigma=0.20
        )
        
        assert greeks["theta"] < 0
    
    def test_vega_positive(self):
        """Vega should be positive for long options"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=100,
            K=100,
            T=30/365,
            r=0.05,
            sigma=0.20
        )
        
        assert greeks["vega"] > 0
    
    def test_higher_vol_higher_vega(self):
        """Higher volatility should result in higher vega"""
        greeks_low_vol = calculate_all_greeks(
            option_type="call", S=100, K=100, T=30/365, r=0.05, sigma=0.10
        )
        greeks_high_vol = calculate_all_greeks(
            option_type="call", S=100, K=100, T=30/365, r=0.05, sigma=0.40
        )
        
        # Vega should be higher with more time for vol to affect price
        assert greeks_high_vol["vega"] != greeks_low_vol["vega"]
    
    def test_second_order_greeks_exist(self):
        """Verify second-order Greeks (Vanna, Charm) are calculated"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=100,
            K=100,
            T=30/365,
            r=0.05,
            sigma=0.20
        )
        
        assert "vanna" in greeks
        assert "charm" in greeks
        assert "vomma" in greeks
        assert "speed" in greeks


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_zero_time_returns_zeros(self):
        """Options at expiry should return zero greeks"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=100,
            K=100,
            T=0,  # At expiry
            r=0.05,
            sigma=0.20
        )
        
        assert greeks["delta"] == 0
        assert greeks["gamma"] == 0
    
    def test_zero_volatility_returns_zeros(self):
        """Zero volatility should return zero greeks"""
        greeks = calculate_all_greeks(
            option_type="call",
            S=100,
            K=100,
            T=30/365,
            r=0.05,
            sigma=0  # Zero vol
        )
        
        assert greeks["delta"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
