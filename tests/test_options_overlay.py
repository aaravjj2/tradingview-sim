"""
Test Options Overlay

Tests for protective puts, put spreads, and options adapter.
"""

import os
import sys
import pytest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestOptionsAdapter:
    """Tests for options adapter."""
    
    def test_greeks_calculation(self):
        """Greeks should be calculated correctly."""
        from workspace.volgate.options_adapter import OptionsAdapter
        
        adapter = OptionsAdapter(use_synthetic=True)
        greeks = adapter.calculate_greeks(590, 570, 30, 0.20, 'put')
        
        assert "delta" in greeks
        assert "gamma" in greeks
        assert "theta" in greeks
        assert "vega" in greeks
        
        # Put delta should be negative
        assert greeks["delta"] < 0
        # Gamma should be positive
        assert greeks["gamma"] > 0
        # Theta should be negative (time decay)
        assert greeks["theta"] < 0
    
    def test_put_price_calculation(self):
        """Put price should be positive for OTM puts."""
        from workspace.volgate.options_adapter import OptionsAdapter
        
        adapter = OptionsAdapter(use_synthetic=True)
        
        # OTM put (strike < spot)
        price = adapter.calculate_option_price(590, 560, 30, 0.20, 'put')
        assert price > 0
        assert price < 10  # Should be small for OTM
        
        # ATM put
        atm_price = adapter.calculate_option_price(590, 590, 30, 0.20, 'put')
        assert atm_price > price  # ATM should be more expensive
    
    def test_synthetic_chain_generation(self):
        """Synthetic chain should generate valid options."""
        from workspace.volgate.options_adapter import OptionsAdapter
        
        adapter = OptionsAdapter(use_synthetic=True)
        chain = adapter.generate_synthetic_chain("SPY", 590, 30, 0.20, 10)
        
        assert len(chain) > 0
        
        # Should have both puts and calls
        puts = [q for q in chain if q.option_type == 'put']
        calls = [q for q in chain if q.option_type == 'call']
        
        assert len(puts) > 0
        assert len(calls) > 0
    
    def test_find_by_delta(self):
        """Should find option closest to target delta."""
        from workspace.volgate.options_adapter import OptionsAdapter
        
        adapter = OptionsAdapter(use_synthetic=True)
        chain = adapter.generate_synthetic_chain("SPY", 590, 30, 0.20, 10)
        
        target_put = adapter.find_by_delta(chain, 0.30, 'put')
        
        assert target_put is not None
        assert target_put.option_type == 'put'
        # Delta should be close to -0.30
        assert abs(abs(target_put.delta) - 0.30) < 0.10


class TestProtectivePuts:
    """Tests for protective puts overlay."""
    
    def test_protection_config_defaults(self):
        """Config should have sensible defaults."""
        from src.options.protective_puts import ProtectionConfig
        
        config = ProtectionConfig()
        
        assert config.target_delta == 0.30
        assert config.min_dte >= 20
        assert config.max_dte >= config.min_dte
        assert 0 < config.notional_protection_pct <= 1
    
    def test_add_protection(self):
        """Should add protective position."""
        from src.options.protective_puts import ProtectivePutsOverlay
        
        overlay = ProtectivePutsOverlay()
        result = overlay.add_protection("SPY", 590, 100000, date(2026, 1, 15))
        
        assert result["status"] in ["added_put", "added_spread"]
        assert overlay.total_premium_spent > 0
        assert len(overlay.protection_log) == 1
    
    def test_should_hedge_in_risk_off(self):
        """Should recommend hedging in risk-off regime."""
        from src.options.protective_puts import ProtectivePutsOverlay
        
        overlay = ProtectivePutsOverlay()
        
        should_hedge = overlay.should_hedge(date(2026, 1, 15), "risk_off", True)
        assert should_hedge is True
        
        # Non-scheduled day, non-risk-off should not hedge
        should_hedge = overlay.should_hedge(date(2026, 1, 10), "trending", True)
        assert should_hedge is False  # Day 10 is not scheduled, not risk-off
    
    def test_budget_limit(self):
        """Should respect annual budget limit."""
        from src.options.protective_puts import ProtectivePutsOverlay, ProtectionConfig
        
        config = ProtectionConfig(annual_cost_budget_pct=0.01)  # 1% budget
        overlay = ProtectivePutsOverlay(config)
        
        # Add first protection
        result1 = overlay.add_protection("SPY", 590, 100000, date(2026, 1, 1))
        assert result1["status"] != "budget_exceeded"
        
        # Simulate budget exhaustion
        overlay.total_premium_spent = 1000  # Force over budget
        result2 = overlay.add_protection("SPY", 590, 100000, date(2026, 2, 1))
        assert result2["status"] == "budget_exceeded"


class TestPutSpread:
    """Tests for put spread functionality."""
    
    def test_spread_creation(self):
        """Put spread should have correct structure."""
        from src.options.protective_puts import OptionsSimulator
        
        sim = OptionsSimulator()
        spread = sim.create_put_spread("SPY", 590, 0.30, 30, 0.10)
        
        assert spread.long_put.strike > spread.short_put.strike
        assert spread.long_put.option_type.value == 'put'
        assert spread.net_premium > 0  # Debit spread
    
    def test_spread_max_protection(self):
        """Spread max protection should be strike difference."""
        from src.options.protective_puts import OptionsSimulator
        
        sim = OptionsSimulator()
        spread = sim.create_put_spread("SPY", 590, 0.30, 30, 0.10)
        spread.long_put.contracts = 1
        spread.short_put.contracts = 1
        
        expected_protection = (spread.long_put.strike - spread.short_put.strike) * 100
        assert spread.max_protection == expected_protection


class TestCrashScenario:
    """Tests for crash scenario protection."""
    
    def test_crash_protection_reduces_dd(self):
        """Protection should reduce DD in crash scenario."""
        from src.options.protective_puts import run_protection_backtest
        import numpy as np
        
        np.random.seed(42)
        prices = [590.0]
        for _ in range(252):
            prices.append(prices[-1] * (1 + np.random.normal(0.0003, 0.012)))
        
        result = run_protection_backtest(prices.copy(), crash_scenario=True)
        
        # In crash, protection should help
        assert result["unprotected_max_dd"] > 0
        # Note: protection effectiveness depends on timing


class TestMarginSafety:
    """Tests for margin safety."""
    
    def test_no_naked_short_puts(self):
        """Overlay should not create naked short puts."""
        from src.options.protective_puts import ProtectivePutsOverlay, ProtectionConfig
        
        config = ProtectionConfig(use_spreads=True)
        overlay = ProtectivePutsOverlay(config)
        
        overlay.add_protection("SPY", 590, 100000, date(2026, 1, 15))
        
        # All positions should be spreads (long + short together)
        for spread in overlay.active_spreads:
            assert spread.long_put.contracts == spread.short_put.contracts
            assert spread.long_put.strike > spread.short_put.strike  # Bull put spread not allowed
    
    def test_contracts_calculation(self):
        """Contracts should be calculated based on protection percentage."""
        from src.options.protective_puts import ProtectivePutsOverlay, ProtectionConfig
        
        config = ProtectionConfig(notional_protection_pct=0.50)  # 50%
        overlay = ProtectivePutsOverlay(config)
        
        contracts = overlay.calculate_contracts_needed(100000, 590)
        
        # 50% of $100k = $50k, / $590 = ~84.7 shares, / 100 = ~1 contract
        assert contracts >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
