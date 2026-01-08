"""
Test Observation Tracking and Extended Observation

Tests for observation tracking, pretrade/posttrade audits,
and acceptance criteria validation.
"""

import os
import sys
import pytest
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestObservationTracking:
    """Tests for observation tracking database."""
    
    def setup_method(self):
        """Create temp database for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
    
    def teardown_method(self):
        """Clean up temp database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_pretrade_audit_recording(self):
        """Should record pretrade audits."""
        from src.audit.observation_tracking import (
            ObservationTracker, PretradeAudit
        )
        
        tracker = ObservationTracker(self.db_path)
        
        audit = PretradeAudit(
            audit_date="2026-01-15",
            symbol="SPY",
            regime="trending",
            signal=1,
            confidence=0.65,
            exposure=0.3,
            vix_level=15.5,
            time_in_market_pct=85.0,
            snapshot_hash="abc123",
            audit_timestamp="2026-01-15T16:00:00",
            status="passed",
            notes="Test audit"
        )
        
        result = tracker.record_pretrade_audit(audit)
        assert result is True
        
        audits = tracker.get_pretrade_audits()
        assert len(audits) == 1
        assert audits[0]["symbol"] == "SPY"
    
    def test_posttrade_audit_recording(self):
        """Should record posttrade audits."""
        from src.audit.observation_tracking import (
            ObservationTracker, PosttradeAudit
        )
        
        tracker = ObservationTracker(self.db_path)
        
        audit = PosttradeAudit(
            audit_date="2026-01-15",
            symbol="SPY",
            expected_shares=100,
            actual_shares=100,
            expected_price=590.0,
            fill_price=590.47,
            slippage_bps=8.0,
            within_tolerance=True,
            reconciliation_status="passed",
            audit_timestamp="2026-01-15T16:30:00",
            notes="Full fill"
        )
        
        result = tracker.record_posttrade_audit(audit)
        assert result is True
        
        audits = tracker.get_posttrade_audits()
        assert len(audits) == 1
        assert audits[0]["within_tolerance"] == 1
    
    def test_observation_day_count(self):
        """Should count observation days correctly."""
        from src.audit.observation_tracking import (
            ObservationTracker, ObservationMetrics
        )
        
        tracker = ObservationTracker(self.db_path)
        
        # Record 5 days
        base_date = date(2026, 1, 15)
        for i in range(5):
            current_date = base_date + timedelta(days=i)
            metrics = ObservationMetrics(
                date=current_date.isoformat(),
                trading_day_number=i + 1,
                time_in_market_pct=80.0,
                regime_flips=0,
                avg_slippage_bps=8.0,
                trades_count=1,
                kill_switch_triggers=0,
                manual_overrides=0,
                pretrade_status="passed",
                posttrade_status="passed"
            )
            tracker.record_daily_metrics(metrics)
        
        assert tracker.get_observation_days() == 5
    
    def test_acceptance_criteria_insufficient_days(self):
        """Should fail acceptance if insufficient days."""
        from src.audit.observation_tracking import ObservationTracker
        
        tracker = ObservationTracker(self.db_path)
        
        # No days recorded
        acceptance = tracker.check_acceptance_criteria()
        
        assert acceptance["all_passed"] is False
        assert acceptance["checks"]["sufficient_days"] is False


class TestAutoRollback:
    """Tests for auto-rollback system."""
    
    def test_slippage_breach_detection(self):
        """Should detect slippage breach."""
        from src.execution.auto_rollback import AutoRollback
        
        rollback = AutoRollback({"slippage_breach_bps": 50})
        
        # Within tolerance
        assert rollback.check_slippage_breach(590, 590.20) is False
        
        # Breach (> 50 bps)
        assert rollback.check_slippage_breach(590, 593) is True
    
    def test_daily_loss_limit_detection(self):
        """Should detect daily loss limit."""
        from src.execution.auto_rollback import AutoRollback
        
        rollback = AutoRollback({"daily_loss_pct": 1.0})
        
        # Within limit
        assert rollback.check_daily_loss_limit(-20, 2500) is False
        
        # Breach (> 1%)
        assert rollback.check_daily_loss_limit(-30, 2500) is True
    
    def test_api_error_accumulation(self):
        """Should trigger on consecutive API errors."""
        from src.execution.auto_rollback import AutoRollback
        
        rollback = AutoRollback({"max_consecutive_api_errors": 3})
        
        assert rollback.record_api_error() is False
        assert rollback.record_api_error() is False
        assert rollback.record_api_error() is True  # Third triggers
    
    def test_rollback_execution(self):
        """Should execute rollback correctly."""
        from src.execution.auto_rollback import AutoRollback, RollbackReason
        
        rollback = AutoRollback()
        
        # Add test data
        rollback.add_position({"symbol": "SPY", "shares": 10, "current_price": 590, "unrealized_pnl": -15})
        rollback.add_pending_order({"id": "TEST-001", "symbol": "SPY", "side": "buy"})
        
        # Execute rollback
        event = rollback.execute_rollback(RollbackReason.MANUAL, "Test", "pytest")
        
        assert event is not None
        assert rollback.is_rolled_back is True
        assert len(rollback.positions) == 0
        assert len(rollback.pending_orders) == 0


class TestIncidentPlaybooks:
    """Tests for incident playbook scripts."""
    
    def test_playbook_scripts_exist(self):
        """Playbook scripts should exist."""
        project_dir = os.path.dirname(os.path.dirname(__file__))
        
        assert os.path.exists(os.path.join(project_dir, "runbook/on_slippage_breach.sh"))
        assert os.path.exists(os.path.join(project_dir, "runbook/on_kill_switch.sh"))
    
    def test_playbook_scripts_executable(self):
        """Playbook scripts should be executable."""
        project_dir = os.path.dirname(os.path.dirname(__file__))
        
        slippage_script = os.path.join(project_dir, "runbook/on_slippage_breach.sh")
        killswitch_script = os.path.join(project_dir, "runbook/on_kill_switch.sh")
        
        assert os.access(slippage_script, os.X_OK)
        assert os.access(killswitch_script, os.X_OK)


class TestObservationDailyScript:
    """Tests for daily observation script."""
    
    def test_script_exists(self):
        """Daily observation script should exist."""
        project_dir = os.path.dirname(os.path.dirname(__file__))
        script_path = os.path.join(project_dir, "scripts/daily_observation.py")
        
        assert os.path.exists(script_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
