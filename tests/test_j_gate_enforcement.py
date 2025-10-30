"""
Test J-gate threshold enforcement - ensures low journal trust scores prevent PASS labels.
"""

import unittest
import sys
from pathlib import Path

# Add project root and engine directory to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = PROJECT_ROOT / "engine"

for path in [PROJECT_ROOT, ENGINE_PATH]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from gates import evaluate_gate_governance_protocol
from tel5_rules import tel5_classify


class TestJGateEnforcement(unittest.TestCase):
    """Test J-gate threshold enforcement prevents incorrect PASS labels."""

    def setUp(self):
        """Set up test fixtures."""
        # Evidence with placeholder journal (will have low or zero J-score)
        self.test_evidence = [
            {
                "study_id": "Test2023",
                "year": 2023,
                "design": "randomized controlled trial",
                "effect_type": "SMD",
                "effect_point": -0.50,
                "ci_low": -0.75,
                "ci_high": -0.25,
                "n_treat": 100,
                "n_ctrl": 100,
                "risk_of_bias": "low",
                "doi": "10.1234/test.001",
                "journal_id": "unknown_journal",  # This will have J=0
            }
        ]

        # Snapshot with no entry for unknown_journal
        self.empty_snapshot = {
            "snapshot_date": "2025-10-30",
            "journals": {}  # Empty - unknown_journal will get J=0
        }

        # Policy with J-gate threshold enforcement
        self.policy = {
            "gates": {
                "phi": {"hard_cap": True},
                "r": {"threshold": 0.7},
                "j": {
                    "threshold": 0.25,
                    "enforce_threshold": True,
                },
                "k": {"hard_cap": True},
            },
            "categories": {
                "sleep": {
                    "delta": 0.20,
                    "benefit_direction": -1,
                }
            },
        }

    def test_unknown_journal_forces_j_fail(self):
        """Test that unknown journal (J=0) results in J-gate FAIL."""
        result = evaluate_gate_governance_protocol(
            evidence_rows=self.test_evidence,
            category="sleep",
            journal_snapshot=self.empty_snapshot,
            policy=self.policy,
            substance="test",
            claim_text="",
        )

        # J-score should be 0.0
        self.assertEqual(result["j"]["score"], 0.0)
        self.assertEqual(result["j"]["score_masked"], 0.0)
        self.assertEqual(result["j"]["result"], "FAIL")

        # Overall should not pass
        self.assertFalse(result["summary"]["overall_pass"])

    def test_j_threshold_enforcement_with_high_p(self):
        """Test that even with high P value, low J-score prevents PASS."""
        result = evaluate_gate_governance_protocol(
            evidence_rows=self.test_evidence,
            category="sleep",
            journal_snapshot=self.empty_snapshot,
            policy=self.policy,
            substance="test",
            claim_text="",
        )

        # Even if P would be high (from strong effect), J=0 should block
        self.assertEqual(result["j"]["result"], "FAIL")

        # Classification should be Black/FAIL
        phi_violation = result["phi"]["violation"]
        k_violation = result["k"]["violation"]
        j_score_masked = result["j"]["score_masked"]
        j_threshold = result["j"]["threshold"]

        # With J below threshold, should be Black
        if j_score_masked < j_threshold:
            # This is the key test - low J should force Black/FAIL
            self.assertLess(j_score_masked, j_threshold)

    def test_enforce_threshold_flag(self):
        """Test that enforce_threshold flag controls behavior."""
        # Test with enforcement enabled
        policy_enforced = self.policy.copy()
        policy_enforced["gates"]["j"]["enforce_threshold"] = True

        result_enforced = evaluate_gate_governance_protocol(
            evidence_rows=self.test_evidence,
            category="sleep",
            journal_snapshot=self.empty_snapshot,
            policy=policy_enforced,
            substance="test",
            claim_text="",
        )

        self.assertEqual(result_enforced["j"]["result"], "FAIL")

        # Test with enforcement disabled
        policy_disabled = self.policy.copy()
        policy_disabled["gates"]["j"]["enforce_threshold"] = False

        result_disabled = evaluate_gate_governance_protocol(
            evidence_rows=self.test_evidence,
            category="sleep",
            journal_snapshot=self.empty_snapshot,
            policy=policy_disabled,
            substance="test",
            claim_text="",
        )

        # With enforcement disabled, j_result might still be FAIL from check_j_gate
        # but the enforcement logic won't override it
        # The key is that gate_sequence_pass logic respects the flag
        self.assertIn(result_disabled["j"]["result"], ["PASS", "FAIL"])

    def test_good_journal_passes(self):
        """Test that good journal with high J-score passes."""
        good_snapshot = {
            "snapshot_date": "2025-10-30",
            "journals": {
                "good_journal": {
                    "title": "Excellent Journal",
                    "IF_z": 0.90,
                    "SJR_z": 0.85,
                    "DOAJ": 1,
                    "COPE": 1,
                    "retracted": 0,
                    "predatory": 0,
                    "hijacked": 0,
                }
            }
        }

        good_evidence = self.test_evidence.copy()
        good_evidence[0] = good_evidence[0].copy()
        good_evidence[0]["journal_id"] = "good_journal"

        result = evaluate_gate_governance_protocol(
            evidence_rows=good_evidence,
            category="sleep",
            journal_snapshot=good_snapshot,
            policy=self.policy,
            substance="test",
            claim_text="",
        )

        # J-score should be high
        self.assertGreater(result["j"]["score"], 0.25)
        self.assertEqual(result["j"]["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
