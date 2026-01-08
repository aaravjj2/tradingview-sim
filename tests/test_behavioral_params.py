"""
Test Behavioral Parameters

Tests for hysteresis, cooldown, and phased re-entry logic.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.signals.behavioral_state import (
    BehavioralStateMachine,
    BehavioralConfig,
    MarketState,
    reset_state_machine,
)


class TestHysteresis:
    """Tests for entry/exit hysteresis logic."""
    
    def test_entry_requires_confirmation(self):
        """Entry should require M consecutive days of signal."""
        config = BehavioralConfig(M_reentry_confirm=3, enable_hysteresis=True)
        sm = BehavioralStateMachine(config)
        
        # First entry signal - should not trigger
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        assert signal == 0
        assert sm.state == MarketState.OUT
        
        # Second entry signal
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-02")
        assert signal == 0
        assert sm.state == MarketState.OUT
        
        # Third entry signal - should trigger
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-03")
        assert signal == 1
        assert sm.state in [MarketState.ENTERING, MarketState.IN]
    
    def test_exit_requires_confirmation(self):
        """Exit should require N consecutive days of signal."""
        config = BehavioralConfig(N_exit_confirm=3, M_reentry_confirm=1, 
                                  enable_hysteresis=True, enable_phased_reentry=False)
        sm = BehavioralStateMachine(config)
        
        # Enter market immediately (M=1)
        sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        assert sm.state == MarketState.IN
        
        # First exit signal - should start confirmation
        signal, exp = sm.process_signal(-1, 0.4, 0.15, "2026-01-02")
        assert signal == 1  # Still in market
        assert sm.state == MarketState.EXITING
        
        # Second exit signal
        signal, exp = sm.process_signal(-1, 0.4, 0.15, "2026-01-03")
        assert signal == 1  # Still in market
        
        # Third exit signal - should trigger exit
        signal, exp = sm.process_signal(-1, 0.4, 0.15, "2026-01-04")
        assert signal == -1
        assert sm.state in [MarketState.OUT, MarketState.COOLDOWN]
    
    def test_entry_confirmation_resets_on_no_signal(self):
        """Entry confirmation should reset if signal disappears."""
        config = BehavioralConfig(M_reentry_confirm=3, enable_hysteresis=True)
        sm = BehavioralStateMachine(config)
        
        # Two entry signals
        sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        sm.process_signal(1, 0.6, 0.12, "2026-01-02")
        
        # No signal - resets count
        sm.process_signal(0, 0.5, 0.12, "2026-01-03")
        assert sm.entry_confirm_count == 0
        
        # Need 3 more signals now
        sm.process_signal(1, 0.6, 0.12, "2026-01-04")
        assert sm.entry_confirm_count == 1


class TestCooldown:
    """Tests for post-exit cooldown period."""
    
    def test_cooldown_prevents_reentry(self):
        """Cooldown should prevent immediate re-entry."""
        config = BehavioralConfig(
            N_exit_confirm=1, M_reentry_confirm=1, 
            cooldown_days=5, enable_cooldown=True,
            enable_hysteresis=False, enable_phased_reentry=False
        )
        sm = BehavioralStateMachine(config)
        
        # Enter and exit
        sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        assert sm.state == MarketState.IN
        
        sm.process_signal(-1, 0.4, 0.15, "2026-01-02")
        assert sm.state == MarketState.COOLDOWN
        assert sm.cooldown_remaining == 5
        
        # Try to re-enter during cooldown
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-03")
        assert signal == 0  # Blocked by cooldown
        assert sm.state == MarketState.COOLDOWN
    
    def test_cooldown_expires(self):
        """Re-entry should be allowed after cooldown expires."""
        config = BehavioralConfig(
            N_exit_confirm=1, M_reentry_confirm=1, 
            cooldown_days=3, enable_cooldown=True,
            enable_hysteresis=False, enable_phased_reentry=False
        )
        sm = BehavioralStateMachine(config)
        
        # Enter and exit
        sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        sm.process_signal(-1, 0.4, 0.15, "2026-01-02")
        assert sm.cooldown_remaining == 3
        
        # Wait out cooldown
        sm.process_signal(0, 0.5, 0.12, "2026-01-03")  # 2 remaining
        sm.process_signal(0, 0.5, 0.12, "2026-01-04")  # 1 remaining
        sm.process_signal(0, 0.5, 0.12, "2026-01-05")  # 0 remaining
        
        # Should now be able to re-enter
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-06")
        assert signal == 1
        assert sm.state == MarketState.IN


class TestPhasedReentry:
    """Tests for phased re-entry exposure ramp."""
    
    def test_phased_entry_ramps_exposure(self):
        """Phased entry should ramp exposure through steps after confirmation."""
        config = BehavioralConfig(
            M_reentry_confirm=2,  # Require confirmation first
            phased_reentry_steps=[0.25, 0.5, 1.0],
            enable_hysteresis=True, enable_phased_reentry=True
        )
        sm = BehavioralStateMachine(config)
        
        # Day 1: First entry signal (pending confirmation)
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        assert signal == 0  # Not confirmed yet
        
        # Day 2: Second entry signal - confirms entry, starts phased at 25%
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-02")
        assert signal == 1
        assert exp == pytest.approx(0.3 * 0.25, rel=0.01)
        assert sm.state == MarketState.ENTERING
        
        # Day 3: Continue - 50% exposure
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-03")
        assert signal == 1
        assert exp == pytest.approx(0.3 * 0.5, rel=0.01)
        
        # Day 4: Complete - 100% exposure
        signal, exp = sm.process_signal(1, 0.6, 0.12, "2026-01-04")
        assert signal == 1
        assert exp == pytest.approx(0.3 * 1.0, rel=0.01)
        assert sm.state == MarketState.IN
    
    def test_phased_entry_aborts_on_exit_signal(self):
        """Phased entry should abort if exit signal received during ramp."""
        config = BehavioralConfig(
            M_reentry_confirm=2,  # Require confirmation
            phased_reentry_steps=[0.25, 0.5, 1.0],
            enable_hysteresis=True, enable_phased_reentry=True,
            enable_cooldown=False
        )
        sm = BehavioralStateMachine(config)
        
        # Confirm entry
        sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        sm.process_signal(1, 0.6, 0.12, "2026-01-02")
        assert sm.state == MarketState.ENTERING
        
        # Exit signal aborts
        signal, exp = sm.process_signal(-1, 0.4, 0.15, "2026-01-03")
        assert signal == -1
        assert sm.state == MarketState.OUT


class TestIntegration:
    """Integration tests combining hysteresis, cooldown, and phased re-entry."""
    
    def test_full_cycle(self):
        """Test a complete entry -> hold -> exit -> cooldown -> re-enter cycle."""
        config = BehavioralConfig(
            N_exit_confirm=2, M_reentry_confirm=2, 
            cooldown_days=2, phased_reentry_steps=[0.5, 1.0],
            enable_hysteresis=True, enable_cooldown=True,
            enable_phased_reentry=True
        )
        sm = BehavioralStateMachine(config)
        
        # Initial state
        assert sm.state == MarketState.OUT
        
        # Day 1-2: Confirm entry
        sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        signal, _ = sm.process_signal(1, 0.6, 0.12, "2026-01-02")
        assert signal == 1
        assert sm.state == MarketState.ENTERING
        
        # Day 3: Complete phased entry
        signal, _ = sm.process_signal(1, 0.6, 0.12, "2026-01-03")
        assert signal == 1
        assert sm.state == MarketState.IN
        
        # Day 4-5: Confirm exit
        sm.process_signal(-1, 0.4, 0.15, "2026-01-04")
        signal, _ = sm.process_signal(-1, 0.4, 0.15, "2026-01-05")
        assert signal == -1
        assert sm.state == MarketState.COOLDOWN
        
        # Day 6-7: Cooldown
        sm.process_signal(1, 0.6, 0.12, "2026-01-06")  # Blocked
        sm.process_signal(1, 0.6, 0.12, "2026-01-07")  # Cooldown ends
        
        # Day 8-9: Re-entry with confirmation
        sm.process_signal(1, 0.6, 0.12, "2026-01-08")
        signal, _ = sm.process_signal(1, 0.6, 0.12, "2026-01-09")
        assert signal == 1
    
    def test_decision_logging(self):
        """Decision log should record all decisions."""
        config = BehavioralConfig(M_reentry_confirm=2, enable_hysteresis=True)
        sm = BehavioralStateMachine(config)
        
        sm.process_signal(1, 0.6, 0.12, "2026-01-01")
        sm.process_signal(1, 0.6, 0.12, "2026-01-02")
        
        assert len(sm.decision_log) == 2
        assert sm.decision_log[0].raw_signal == 1
        assert "pending" in sm.decision_log[0].reason.lower()
        assert "confirmed" in sm.decision_log[1].reason.lower()


class TestConfig:
    """Tests for configuration loading."""
    
    def test_default_config(self):
        """Default config should have sensible defaults."""
        config = BehavioralConfig()
        
        assert config.N_exit_confirm >= 1
        assert config.M_reentry_confirm >= 1
        assert config.cooldown_days >= 0
        assert len(config.phased_reentry_steps) >= 1
    
    def test_config_from_yaml(self):
        """Config should load from YAML file."""
        import tempfile
        import yaml
        
        yaml_content = {
            "behavioral": {
                "N_exit_confirm": 5,
                "M_reentry_confirm": 3,
                "cooldown_days": 10,
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = f.name
        
        try:
            config = BehavioralConfig.from_yaml(temp_path)
            assert config.N_exit_confirm == 5
            assert config.M_reentry_confirm == 3
            assert config.cooldown_days == 10
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
