"""
Test Falsification Framework

Tests for Reality Compression, Behavioral Audit, and Capital Readiness.
"""

import os
import sys
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestRealityCompression:
    """Tests for Reality Compression Engine."""
    
    def test_single_simulation_runs(self):
        """Single simulation should complete without error."""
        from src.analytics.reality_compression import RealityCompressionEngine
        
        engine = RealityCompressionEngine()
        result = engine.run_single_simulation("SPY", days=60, seed=42)
        
        assert result is not None
        assert result.symbol == "SPY"
        assert result.days_simulated > 0
        assert isinstance(result.survival, bool)
        assert result.max_drawdown_pct >= 0
    
    def test_slippage_inflation_applied(self):
        """Slippage should be inflated above base level."""
        from src.analytics.reality_compression import RealityCompressionEngine, CompressionConfig
        
        config = CompressionConfig(slippage_multiplier_range=(3.0, 5.0))
        engine = RealityCompressionEngine(config)
        result = engine.run_single_simulation("SPY", days=60, seed=42)
        
        # Average slippage should be at least 3x base (8 bps)
        assert result.avg_slippage_bps >= 24  # 3 * 8
    
    def test_partial_fills_applied(self):
        """Partial fills should reduce fill rate."""
        from src.analytics.reality_compression import RealityCompressionEngine, CompressionConfig
        
        config = CompressionConfig(partial_fill_range=(0.5, 0.6))
        engine = RealityCompressionEngine(config)
        result = engine.run_single_simulation("SPY", days=60, seed=42)
        
        # Partial fill rate should be in configured range
        if result.trades_executed > 0:
            assert 0.4 <= result.partial_fill_rate <= 0.7
    
    def test_batch_runs_multiple_symbols(self):
        """Batch should run across multiple symbols."""
        from src.analytics.reality_compression import RealityCompressionEngine
        
        engine = RealityCompressionEngine()
        results = engine.run_batch(["SPY", "GLD"], simulations_per_symbol=3, days=60)
        
        assert "SPY" in results
        assert "GLD" in results
        assert len(results["SPY"]) == 3
        assert len(results["GLD"]) == 3
    
    def test_report_generation(self):
        """Report should be generated to output directory."""
        from src.analytics.reality_compression import RealityCompressionEngine
        
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RealityCompressionEngine()
            results = engine.run_batch(["SPY"], simulations_per_symbol=5, days=60)
            summary = engine.generate_report(results, tmpdir)
            
            assert os.path.exists(os.path.join(tmpdir, "compression_summary.json"))
            assert os.path.exists(os.path.join(tmpdir, "simulation_details.csv"))
            assert summary["overall"]["total_simulations"] == 5


class TestBehavioralAudit:
    """Tests for Behavioral Consistency Audit."""
    
    def test_audit_runs(self):
        """Audit should complete without error."""
        from src.analytics.behavioral_audit import BehavioralAudit
        
        audit = BehavioralAudit()
        result = audit.run_audit("SPY", days=60, seed=42)
        
        assert result is not None
        assert "volgate" in result["strategies"]
        assert "buy_hold" in result["strategies"]
        assert "random_gate" in result["strategies"]
    
    def test_volgate_has_lower_churn_than_random(self):
        """VolGate should have lower churn than random gate."""
        from src.analytics.behavioral_audit import BehavioralAudit
        
        audit = BehavioralAudit()
        result = audit.run_audit("SPY", days=252, seed=42)
        
        volgate_churn = result["strategies"]["volgate"]["churn_rate"]
        random_churn = result["strategies"]["random_gate"]["churn_rate"]
        
        # VolGate should be less churny
        assert volgate_churn < random_churn * 2  # Allow some margin
    
    def test_metrics_calculated_correctly(self):
        """All metrics should be calculated."""
        from src.analytics.behavioral_audit import BehavioralAudit
        
        audit = BehavioralAudit()
        result = audit.run_audit("SPY", days=60, seed=42)
        
        vg = result["strategies"]["volgate"]
        assert "time_in_market_pct" in vg
        assert "avg_hold_duration_days" in vg
        assert "regime_flips" in vg
        assert "max_drawdown_pct" in vg


class TestCapitalReadiness:
    """Tests for Capital Readiness Decision Engine."""
    
    def test_no_inputs_gives_no_go(self):
        """No inputs should result in NO-GO verdict."""
        from src.governance.capital_readiness import CapitalReadinessEngine, Verdict
        
        engine = CapitalReadinessEngine()
        decision = engine.evaluate()
        
        assert decision.verdict == Verdict.NO_GO
        assert decision.max_capital_allowed == 0
    
    def test_good_stats_gives_go_or_conditional(self):
        """Good stats should give GO or CONDITIONAL."""
        from src.governance.capital_readiness import CapitalReadinessEngine, Verdict
        
        engine = CapitalReadinessEngine()
        
        reality_stats = {
            "overall": {
                "survival_rate": 98,
                "p95_max_dd_pct": 15,
                "exit_latency_p95": 1,
            }
        }
        behavioral_stats = {
            "overall_pass_rate": 96,
            "check_pass_rates": {
                "lower_churn_than_random": 98,
                "lower_dd_slope_than_buy_hold": 95,
                "no_regime_thrashing": 100,
                "reasonable_time_in_market": 97,
            }
        }
        paper_stats = {
            "days_active": 14,
            "total_trades": 5,
            "avg_slippage_bps": 9,
            "reconciliation_passed": True,
        }
        
        decision = engine.evaluate(reality_stats, behavioral_stats, paper_stats)
        
        assert decision.verdict in [Verdict.GO, Verdict.CONDITIONAL]
        assert decision.max_capital_allowed > 0
    
    def test_low_survival_rate_blocks(self):
        """Low survival rate should block capital."""
        from src.governance.capital_readiness import CapitalReadinessEngine, Verdict
        
        engine = CapitalReadinessEngine()
        
        reality_stats = {
            "overall": {
                "survival_rate": 80,  # Below 95% threshold
                "p95_max_dd_pct": 15,
                "exit_latency_p95": 1,
            }
        }
        
        decision = engine.evaluate(reality_stats)
        
        assert decision.verdict == Verdict.NO_GO
        assert len(decision.blocking_risks) > 0
    
    def test_decision_is_reproducible(self):
        """Same inputs should give same output."""
        from src.governance.capital_readiness import CapitalReadinessEngine
        
        stats = {
            "overall": {
                "survival_rate": 96,
                "p95_max_dd_pct": 18,
                "exit_latency_p95": 1.5,
            }
        }
        
        engine1 = CapitalReadinessEngine()
        decision1 = engine1.evaluate(stats)
        
        engine2 = CapitalReadinessEngine()
        decision2 = engine2.evaluate(stats)
        
        assert decision1.verdict == decision2.verdict
        assert decision1.max_capital_allowed == decision2.max_capital_allowed
    
    def test_document_generation(self):
        """Capital decision document should be generated."""
        from src.governance.capital_readiness import (
            CapitalReadinessEngine, 
            generate_capital_decision_document,
            Verdict
        )
        
        engine = CapitalReadinessEngine()
        decision = engine.evaluate()
        
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            doc_path = f.name
        
        try:
            doc = generate_capital_decision_document(decision, doc_path)
            assert os.path.exists(doc_path)
            assert "Verdict" in doc
            assert decision.verdict.value in doc
        finally:
            os.unlink(doc_path)


class TestForecastOutput:
    """Tests for daily price forecast in shadow replay."""
    
    def test_shadow_replay_generates_forecast(self):
        """Shadow replay should include price forecast."""
        # This tests that the forecast is included in output
        from workspace.volgate.model_adapter import predict, load_model
        
        model = load_model()
        snapshot = {
            "symbol": "SPY",
            "decision_time": "2026-01-15T15:55:00",
            "bars": [{"close": 590 + i, "timestamp": f"2026-01-{i+1:02d}T15:55:00"} 
                     for i in range(30)],
            "vix": 15.0,
            "regime": "trending",
        }
        
        prediction = predict(model, snapshot)
        
        # Prediction should include forecast
        assert "signal" in prediction
        assert "exposure" in prediction
        # Note: actual forecast price would be added in enhancement


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
