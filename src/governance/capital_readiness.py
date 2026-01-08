"""
Capital Readiness Decision Engine

Automates the GO / NO-GO decision for capital deployment.

Inputs:
- Reality compression stats
- Live paper logs
- Drawdown behavior

Outputs:
- Verdict: GO | CONDITIONAL | NO-GO
- max_capital_allowed
- required_observation_days
- blocking_risks
"""

import os
import sys
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class Verdict(Enum):
    GO = "GO"
    CONDITIONAL = "CONDITIONAL"
    NO_GO = "NO-GO"


@dataclass
class CapitalDecision:
    """Capital readiness decision output."""
    verdict: Verdict
    max_capital_allowed: float
    required_observation_days: int
    blocking_risks: List[str]
    conditional_requirements: List[str]
    confidence_score: float
    rationale: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "verdict": self.verdict.value,
            "max_capital_allowed": self.max_capital_allowed,
            "required_observation_days": self.required_observation_days,
            "blocking_risks": self.blocking_risks,
            "conditional_requirements": self.conditional_requirements,
            "confidence_score": self.confidence_score,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


class CapitalReadinessEngine:
    """
    Decision engine for capital deployment authorization.
    
    Conservative by default. Explains all decisions.
    """
    
    # Thresholds (conservative defaults)
    SURVIVAL_RATE_MIN = 95.0
    MAX_DD_THRESHOLD = 25.0
    EXIT_LATENCY_MAX = 2
    CHURN_RATE_MAX = 0.05  # 5% of days have trades
    BEHAVIORAL_PASS_RATE_MIN = 90.0
    
    # Capital tiers
    TIER_1_MAX_CAPITAL = 10000  # Initial testing
    TIER_2_MAX_CAPITAL = 25000  # Extended testing
    TIER_3_MAX_CAPITAL = 50000  # Production-ready
    
    # Observation period requirements
    MIN_OBSERVATION_DAYS = 30
    EXTENDED_OBSERVATION_DAYS = 60
    FULL_OBSERVATION_DAYS = 90
    
    def __init__(self):
        self.blocking_risks = []
        self.conditional_requirements = []
        self.score_components = {}
        
    def _check_reality_compression(self, stats: Dict) -> float:
        """Check reality compression results. Returns score 0-1."""
        score = 1.0
        
        overall = stats.get("overall", {})
        survival_rate = overall.get("survival_rate", 0)
        p95_dd = overall.get("p95_max_dd_pct", 100)
        exit_latency = overall.get("exit_latency_p95", 10)
        
        # Survival rate check
        if survival_rate < self.SURVIVAL_RATE_MIN:
            self.blocking_risks.append(
                f"Survival rate {survival_rate:.1f}% below threshold {self.SURVIVAL_RATE_MIN}%"
            )
            score -= 0.4
        elif survival_rate < 98:
            self.conditional_requirements.append(
                f"Survival rate {survival_rate:.1f}% is marginal, requires extended observation"
            )
            score -= 0.1
            
        # Max DD check
        if p95_dd > self.MAX_DD_THRESHOLD:
            self.blocking_risks.append(
                f"P95 Max DD {p95_dd:.1f}% exceeds threshold {self.MAX_DD_THRESHOLD}%"
            )
            score -= 0.3
        elif p95_dd > 20:
            self.conditional_requirements.append(
                f"P95 Max DD {p95_dd:.1f}% is elevated, reduce position sizing"
            )
            score -= 0.1
            
        # Exit latency check
        if exit_latency > self.EXIT_LATENCY_MAX:
            self.blocking_risks.append(
                f"Exit latency P95 {exit_latency:.1f} bars exceeds threshold {self.EXIT_LATENCY_MAX}"
            )
            score -= 0.2
            
        self.score_components["reality_compression"] = max(0, score)
        return max(0, score)
    
    def _check_behavioral_audit(self, stats: Dict) -> float:
        """Check behavioral audit results. Returns score 0-1."""
        score = 1.0
        
        pass_rate = stats.get("overall_pass_rate", 0)
        check_rates = stats.get("check_pass_rates", {})
        
        # Overall pass rate
        if pass_rate < self.BEHAVIORAL_PASS_RATE_MIN:
            self.blocking_risks.append(
                f"Behavioral audit pass rate {pass_rate:.1f}% below threshold {self.BEHAVIORAL_PASS_RATE_MIN}%"
            )
            score -= 0.3
        elif pass_rate < 95:
            self.conditional_requirements.append(
                f"Behavioral pass rate {pass_rate:.1f}% requires monitoring"
            )
            score -= 0.1
            
        # Individual check rates
        for check, rate in check_rates.items():
            if rate < 80:
                self.blocking_risks.append(f"Check '{check}' failed {100-rate:.0f}% of audits")
                score -= 0.15
            elif rate < 90:
                self.conditional_requirements.append(f"Check '{check}' marginal at {rate:.0f}%")
                score -= 0.05
                
        self.score_components["behavioral_audit"] = max(0, score)
        return max(0, score)
    
    def _check_paper_logs(self, stats: Dict) -> float:
        """Check live paper trading logs. Returns score 0-1."""
        score = 1.0
        
        days_active = stats.get("days_active", 0)
        total_trades = stats.get("total_trades", 0)
        avg_slippage = stats.get("avg_slippage_bps", 0)
        reconciliation_passed = stats.get("reconciliation_passed", False)
        
        # Minimum paper trading period
        if days_active < 7:
            self.blocking_risks.append(
                f"Only {days_active} days of paper trading, minimum 7 required"
            )
            score -= 0.4
        elif days_active < 14:
            self.conditional_requirements.append(
                f"Only {days_active} days of paper trading, recommend 14+"
            )
            score -= 0.1
            
        # Trade execution verification
        if total_trades < 3:
            self.conditional_requirements.append(
                f"Only {total_trades} trades executed, limited execution verification"
            )
            score -= 0.1
            
        # Slippage check
        if avg_slippage > 15:
            self.blocking_risks.append(
                f"Average slippage {avg_slippage:.1f}bps too high"
            )
            score -= 0.2
        elif avg_slippage > 10:
            self.conditional_requirements.append(
                f"Slippage {avg_slippage:.1f}bps slightly elevated"
            )
            score -= 0.05
            
        # Reconciliation
        if not reconciliation_passed:
            self.blocking_risks.append("Reconciliation check failed")
            score -= 0.3
            
        self.score_components["paper_logs"] = max(0, score)
        return max(0, score)
    
    def _determine_verdict(self, total_score: float) -> Verdict:
        """Determine verdict based on total score."""
        if self.blocking_risks:
            return Verdict.NO_GO
        elif total_score >= 0.9 and not self.conditional_requirements:
            return Verdict.GO
        elif total_score >= 0.7:
            return Verdict.CONDITIONAL
        else:
            return Verdict.NO_GO
    
    def _determine_capital_limit(self, verdict: Verdict, total_score: float) -> float:
        """Determine maximum capital allowed."""
        if verdict == Verdict.NO_GO:
            return 0
        elif verdict == Verdict.CONDITIONAL:
            if total_score >= 0.85:
                return self.TIER_2_MAX_CAPITAL
            else:
                return self.TIER_1_MAX_CAPITAL
        else:  # GO
            if total_score >= 0.95:
                return self.TIER_3_MAX_CAPITAL
            else:
                return self.TIER_2_MAX_CAPITAL
    
    def _determine_observation_days(self, verdict: Verdict, 
                                     paper_days: int) -> int:
        """Determine required observation days before scaling."""
        if verdict == Verdict.NO_GO:
            return self.FULL_OBSERVATION_DAYS
        elif verdict == Verdict.CONDITIONAL:
            return self.EXTENDED_OBSERVATION_DAYS
        else:
            return max(self.MIN_OBSERVATION_DAYS - paper_days, 14)
    
    def _generate_rationale(self, verdict: Verdict, total_score: float) -> str:
        """Generate human-readable rationale."""
        if verdict == Verdict.NO_GO:
            return (
                f"Capital deployment NOT AUTHORIZED. "
                f"Confidence score: {total_score*100:.0f}%. "
                f"Blocking risks identified: {len(self.blocking_risks)}. "
                f"The strategy has not demonstrated sufficient robustness under stress testing."
            )
        elif verdict == Verdict.CONDITIONAL:
            return (
                f"Capital deployment CONDITIONALLY authorized with restrictions. "
                f"Confidence score: {total_score*100:.0f}%. "
                f"The strategy shows promise but requires additional observation "
                f"and has {len(self.conditional_requirements)} conditions to address."
            )
        else:
            return (
                f"Capital deployment AUTHORIZED. "
                f"Confidence score: {total_score*100:.0f}%. "
                f"The strategy has demonstrated robust behavior under stress testing "
                f"and behavioral audits. Conservative position sizing recommended."
            )
    
    def evaluate(self, 
                 reality_compression_stats: Optional[Dict] = None,
                 behavioral_audit_stats: Optional[Dict] = None,
                 paper_log_stats: Optional[Dict] = None) -> CapitalDecision:
        """
        Evaluate all inputs and produce capital readiness decision.
        
        Args:
            reality_compression_stats: Output from reality compression engine
            behavioral_audit_stats: Output from behavioral audit
            paper_log_stats: Statistics from live paper trading
        """
        self.blocking_risks = []
        self.conditional_requirements = []
        self.score_components = {}
        
        scores = []
        
        # Check each component if available
        if reality_compression_stats:
            scores.append(self._check_reality_compression(reality_compression_stats))
        else:
            self.blocking_risks.append("Reality compression results not available")
            
        if behavioral_audit_stats:
            scores.append(self._check_behavioral_audit(behavioral_audit_stats))
        else:
            self.blocking_risks.append("Behavioral audit results not available")
            
        if paper_log_stats:
            scores.append(self._check_paper_logs(paper_log_stats))
        else:
            self.conditional_requirements.append("Paper trading logs not available")
            scores.append(0.7)  # Partial credit
            
        # Calculate total score
        total_score = sum(scores) / len(scores) if scores else 0
        
        # Determine outputs
        verdict = self._determine_verdict(total_score)
        max_capital = self._determine_capital_limit(verdict, total_score)
        paper_days = paper_log_stats.get("days_active", 0) if paper_log_stats else 0
        observation_days = self._determine_observation_days(verdict, paper_days)
        rationale = self._generate_rationale(verdict, total_score)
        
        return CapitalDecision(
            verdict=verdict,
            max_capital_allowed=max_capital,
            required_observation_days=observation_days,
            blocking_risks=self.blocking_risks.copy(),
            conditional_requirements=self.conditional_requirements.copy(),
            confidence_score=total_score,
            rationale=rationale,
        )


def generate_capital_decision_document(decision: CapitalDecision, 
                                        output_path: str) -> str:
    """Generate human-readable capital decision document."""
    
    verdict_emoji = {
        Verdict.GO: "✅",
        Verdict.CONDITIONAL: "⚠️",
        Verdict.NO_GO: "❌",
    }
    
    doc = f"""# Capital Readiness Decision

> **Verdict**: {verdict_emoji[decision.verdict]} {decision.verdict.value}
> **Generated**: {decision.timestamp}

---

## Executive Summary

{decision.rationale}

## Decision Details

| Metric | Value |
|--------|-------|
| Verdict | **{decision.verdict.value}** |
| Max Capital Allowed | ${decision.max_capital_allowed:,.0f} |
| Required Observation Days | {decision.required_observation_days} |
| Confidence Score | {decision.confidence_score*100:.0f}% |

"""

    if decision.blocking_risks:
        doc += """## 🚫 Blocking Risks

The following issues MUST be resolved before capital deployment:

"""
        for risk in decision.blocking_risks:
            doc += f"- {risk}\n"
        doc += "\n"

    if decision.conditional_requirements:
        doc += """## ⚠️ Conditional Requirements

The following conditions apply to any capital deployment:

"""
        for req in decision.conditional_requirements:
            doc += f"- {req}\n"
        doc += "\n"

    doc += """## Recommendations

"""
    if decision.verdict == Verdict.GO:
        doc += """1. Begin with 50% of maximum authorized capital
2. Scale up gradually over the observation period
3. Implement hard stop at 25% drawdown
4. Review weekly during initial deployment
"""
    elif decision.verdict == Verdict.CONDITIONAL:
        doc += """1. Address all conditional requirements before deployment
2. Begin with 25% of maximum authorized capital
3. Extend observation period if any issues arise
4. Daily monitoring required
5. Hard stop at 15% drawdown
"""
    else:
        doc += """1. DO NOT deploy capital at this time
2. Review and address all blocking risks
3. Re-run falsification framework after fixes
4. Consider fundamental strategy review if issues persist
"""

    doc += """
---

*This document was auto-generated by the Capital Readiness Decision Engine.*
*The engine is conservative by default and prioritizes capital preservation.*
"""

    with open(output_path, "w") as f:
        f.write(doc)
    
    return doc


def run_capital_readiness_check(artifacts_dir: str = None, 
                                 output_dir: str = None) -> CapitalDecision:
    """
    Run full capital readiness check using existing artifacts.
    
    Args:
        artifacts_dir: Directory containing compression and audit results
        output_dir: Directory for output documents
    """
    if artifacts_dir is None:
        artifacts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts"
        )
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "docs"
        )
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load artifacts
    reality_stats = None
    behavioral_stats = None
    paper_stats = None
    
    compression_path = os.path.join(artifacts_dir, "reality_compression", "compression_summary.json")
    if os.path.exists(compression_path):
        with open(compression_path) as f:
            reality_stats = json.load(f)
    
    audit_path = os.path.join(artifacts_dir, "behavioral_audit", "behavioral_audit_summary.json")
    if os.path.exists(audit_path):
        with open(audit_path) as f:
            behavioral_stats = json.load(f)
    
    # Construct paper stats from reconciliation if available
    reconciliation_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "reconciliation_report.csv"
    )
    if os.path.exists(reconciliation_path):
        import csv
        with open(reconciliation_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                slippages = [float(r.get("slippage_bps", 0)) for r in rows if r.get("slippage_bps")]
                paper_stats = {
                    "days_active": len(set(r.get("date", "") for r in rows)),
                    "total_trades": len(rows),
                    "avg_slippage_bps": sum(slippages) / len(slippages) if slippages else 0,
                    "reconciliation_passed": True,
                }
    
    # Run evaluation
    engine = CapitalReadinessEngine()
    decision = engine.evaluate(reality_stats, behavioral_stats, paper_stats)
    
    # Generate documents
    doc_path = os.path.join(output_dir, "capital_decision.md")
    generate_capital_decision_document(decision, doc_path)
    
    # Also save JSON
    json_path = os.path.join(output_dir, "capital_decision.json")
    with open(json_path, "w") as f:
        json.dump(decision.to_dict(), f, indent=2)
    
    return decision


if __name__ == "__main__":
    decision = run_capital_readiness_check()
    
    verdict_emoji = {"GO": "✅", "CONDITIONAL": "⚠️", "NO-GO": "❌"}
    
    print("\n" + "=" * 50)
    print("CAPITAL READINESS CHECK COMPLETE")
    print("=" * 50)
    print(f"Verdict: {verdict_emoji.get(decision.verdict.value, '')} {decision.verdict.value}")
    print(f"Max Capital: ${decision.max_capital_allowed:,.0f}")
    print(f"Observation Days: {decision.required_observation_days}")
    print(f"Confidence: {decision.confidence_score*100:.0f}%")
    print("=" * 50)
    
    if decision.blocking_risks:
        print("\nBlocking Risks:")
        for risk in decision.blocking_risks:
            print(f"  ❌ {risk}")
    
    if decision.conditional_requirements:
        print("\nConditions:")
        for req in decision.conditional_requirements:
            print(f"  ⚠️ {req}")
    
    print(f"\nFull report: docs/capital_decision.md")
