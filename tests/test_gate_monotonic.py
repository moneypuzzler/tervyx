import unittest

from engine.gates import apply_monotonic_masking, evaluate_gate_governance_protocol
from engine.tel5_rules import tel5_classify
from tervyx.policy.utils import load_journal_snapshot, read_policy


class GateMonotonicityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = read_policy()
        snapshot_rel = cls.policy.get("gates", {}).get("j", {}).get("use_snapshot")
        cls.snapshot = load_journal_snapshot(snapshot_rel)

    def test_phi_violation_forces_black_tier(self):
        label, tier = tel5_classify(0.99, phi_violation=True, k_violation=False)
        self.assertEqual(label, "FAIL")
        self.assertEqual(tier, "Black")

    def test_k_violation_forces_black_tier(self):
        label, tier = tel5_classify(0.75, phi_violation=False, k_violation=True)
        self.assertEqual(label, "FAIL")
        self.assertEqual(tier, "Black")

    def test_monotonic_masking_zeroes_j_score(self):
        masked = apply_monotonic_masking(0.87, phi_violation=False, k_violation=True)
        self.assertEqual(masked, 0.0)

    def test_phi_violation_masks_j_score(self):
        evidence = [
            {
                "study_id": "BadPhi",
                "year": 2024,
                "design": "randomized controlled trial",
                "effect_type": "RR",  # Not permitted for sleep category
                "effect_point": -0.3,
                "ci_low": -0.5,
                "ci_high": -0.1,
                "n_treat": 30,
                "n_ctrl": 30,
                "risk_of_bias": "low",
                "journal_id": "ISSN:1389-9457",
                "outcome": "psqi_total",
                "population": "adults with insomnia",
                "adverse_events": "none",
                "duration_weeks": 8,
            }
        ]

        gates = evaluate_gate_governance_protocol(
            evidence,
            category="sleep",
            journal_snapshot=self.snapshot,
            policy=self.policy,
            substance="Magnesium",
            claim_text="Magnesium cures insomnia instantly",
        )

        self.assertEqual(gates["phi"]["result"], "FAIL")
        self.assertEqual(gates["j"]["score_masked"], 0.0)

    def test_k_violation_masks_j_score(self):
        evidence = [
            {
                "study_id": "SafetyFail",
                "year": 2023,
                "design": "randomized controlled trial",
                "effect_type": "SMD",
                "effect_point": -0.2,
                "ci_low": -0.4,
                "ci_high": 0.0,
                "n_treat": 40,
                "n_ctrl": 38,
                "risk_of_bias": "low",
                "journal_id": "ISSN:0161-8105",
                "outcome": "psqi_total",
                "population": "adults with insomnia",
                "adverse_events": "Serious toxicity reported",
                "duration_weeks": 6,
            }
        ]

        gates = evaluate_gate_governance_protocol(
            evidence,
            category="sleep",
            journal_snapshot=self.snapshot,
            policy=self.policy,
            substance="Magnesium",
            claim_text="Magnesium improves sleep quality",
        )

        self.assertEqual(gates["k"]["result"], "FAIL")
        self.assertEqual(gates["j"]["score_masked"], 0.0)


if __name__ == "__main__":
    unittest.main()
