"""
Integration tests for TERVYX Protocol end-to-end workflows.
Tests the complete pipeline from evidence.csv to entry.jsonld.
"""

import json
import tempfile
import unittest
from pathlib import Path
import csv
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mc_meta import run_reml_mc_analysis, validate_evidence_data
from tel5_rules import tel5_classify, apply_l_gate_penalty
from gates import evaluate_all_gates
from schema_validate import validate_all_artifacts


class TestEntryBuildIntegration(unittest.TestCase):
    """Test complete entry build workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_evidence = [
            {
                "study_id": "TestStudy2023",
                "year": 2023,
                "design": "randomized controlled trial",
                "effect_type": "SMD",
                "effect_point": -0.40,
                "ci_low": -0.65,
                "ci_high": -0.15,
                "n_treat": 50,
                "n_ctrl": 50,
                "risk_of_bias": "low",
                "doi": "10.1234/test.2023.001",
                "journal_id": "ISSN:1234-5678",
            },
            {
                "study_id": "TestStudy2024",
                "year": 2024,
                "design": "double-blind randomized trial",
                "effect_type": "SMD",
                "effect_point": -0.35,
                "ci_low": -0.58,
                "ci_high": -0.12,
                "n_treat": 60,
                "n_ctrl": 60,
                "risk_of_bias": "some",
                "doi": "10.1234/test.2024.002",
                "journal_id": "ISSN:1234-5678",
            },
            {
                "study_id": "TestStudy2024b",
                "year": 2024,
                "design": "randomized controlled trial",
                "effect_type": "SMD",
                "effect_point": -0.38,
                "ci_low": -0.61,
                "ci_high": -0.15,
                "n_treat": 55,
                "n_ctrl": 58,
                "risk_of_bias": "low",
                "doi": "10.1234/test.2024.003",
                "journal_id": "ISSN:1234-5678",
            },
        ]

        self.test_policy = {
            "version": "1.3.0",
            "categories": {
                "sleep": {
                    "delta": 0.20,
                    "benefit_direction": -1,
                }
            },
            "monte_carlo": {
                "seed": 20251005,
                "n_draws": 10000,
                "tau2_method": "REML",
            },
            "gates": {
                "phi": {"hard_cap": True},
                "j": {"use_snapshot": "protocol/journal_trust/snapshot-2025-10-05.json"},
            },
        }

        self.test_snapshot = {
            "snapshot_date": "2025-10-05",
            "journals": {
                "ISSN:1234-5678": {
                    "journal_name": "Test Journal",
                    "IF_z": 0.5,
                    "SJR_z": 0.5,
                    "DOAJ": 1.0,
                    "COPE": 1.0,
                    "retracted": False,
                    "predatory": False,
                    "hijacked": False,
                }
            },
        }

    def test_evidence_validation(self):
        """Test that evidence data passes validation."""
        errors = validate_evidence_data(self.test_evidence)
        self.assertEqual(len(errors), 0, f"Evidence validation failed: {errors}")

    def test_monte_carlo_analysis(self):
        """Test Monte Carlo meta-analysis runs successfully."""
        result = run_reml_mc_analysis(
            evidence_rows=self.test_evidence,
            delta=0.20,
            benefit_direction=-1,
            seed=20251005,
            n_draws=10000,
            tau2_method="REML",
        )

        # Check required fields
        self.assertIn("P_effect_gt_delta", result)
        self.assertIn("mu_hat", result)
        self.assertIn("mu_CI95", result)
        self.assertIn("I2", result)
        self.assertIn("tau2", result)
        self.assertIn("n_studies", result)
        self.assertIn("total_n", result)

        # Check value ranges
        self.assertGreaterEqual(result["P_effect_gt_delta"], 0.0)
        self.assertLessEqual(result["P_effect_gt_delta"], 1.0)
        self.assertEqual(result["n_studies"], 3)
        self.assertEqual(result["total_n"], 333)

    def test_gate_evaluation(self):
        """Test gate evaluation produces expected structure."""
        result = evaluate_all_gates(
            evidence_rows=self.test_evidence,
            category="sleep",
            journal_snapshot=self.test_snapshot,
            policy=self.test_policy,
            substance_hint="test-substance sleep nutrient",
        )

        # Check all gates are present
        self.assertIn("phi", result)
        self.assertIn("r", result)
        self.assertIn("j", result)
        self.assertIn("k", result)
        self.assertIn("l", result)
        self.assertIn("summary", result)

        # Check gate structure
        self.assertIn("result", result["phi"])
        self.assertIn("violation", result["phi"])
        self.assertIn("score", result["r"])
        self.assertIn("score", result["j"])
        self.assertIn("result", result["k"])
        self.assertIn("result", result["l"])

    def test_tel5_classification(self):
        """Test TEL-5 classification logic."""
        # Test Gold tier
        label, tier = tel5_classify(0.95, phi_violation=False, k_violation=False)
        self.assertEqual(label, "PASS")
        self.assertEqual(tier, "Gold")

        # Test Silver tier
        label, tier = tel5_classify(0.80, phi_violation=False, k_violation=False)
        self.assertEqual(label, "PASS")
        self.assertEqual(tier, "Silver")

        # Test Bronze tier
        label, tier = tel5_classify(0.65, phi_violation=False, k_violation=False)
        self.assertEqual(label, "AMBER")
        self.assertEqual(tier, "Bronze")

        # Test Phi violation forces Black
        label, tier = tel5_classify(0.95, phi_violation=True, k_violation=False)
        self.assertEqual(label, "FAIL")
        self.assertEqual(tier, "Black")

        # Test K violation forces Black
        label, tier = tel5_classify(0.95, phi_violation=False, k_violation=True)
        self.assertEqual(label, "FAIL")
        self.assertEqual(tier, "Black")

    def test_l_gate_penalty(self):
        """Test L-gate penalty demotion logic."""
        # Gold with L violation -> Bronze
        label, tier = apply_l_gate_penalty("PASS", "Gold", l_violation=True)
        self.assertEqual(label, "AMBER")
        self.assertEqual(tier, "Bronze")

        # Silver with L violation -> Red
        label, tier = apply_l_gate_penalty("PASS", "Silver", l_violation=True)
        self.assertEqual(label, "AMBER")
        self.assertEqual(tier, "Red")

        # No change without L violation
        label, tier = apply_l_gate_penalty("PASS", "Gold", l_violation=False)
        self.assertEqual(label, "PASS")
        self.assertEqual(tier, "Gold")

    def test_full_entry_build_workflow(self):
        """Test complete workflow: evidence -> simulation -> classification -> entry."""

        # Step 1: Validate evidence
        errors = validate_evidence_data(self.test_evidence)
        self.assertEqual(len(errors), 0)

        # Step 2: Run Monte Carlo analysis
        simulation = run_reml_mc_analysis(
            evidence_rows=self.test_evidence,
            delta=0.20,
            benefit_direction=-1,
            seed=20251005,
            n_draws=10000,
            tau2_method="REML",
        )

        # Step 3: Evaluate gates
        gate_results = evaluate_all_gates(
            evidence_rows=self.test_evidence,
            category="sleep",
            journal_snapshot=self.test_snapshot,
            policy=self.test_policy,
            substance_hint="magnesium sleep",
        )

        # Step 4: Classify
        P_effect = simulation["P_effect_gt_delta"]
        phi_violation = gate_results["phi"]["violation"]
        k_violation = gate_results["k"]["violation"]
        l_violation = gate_results["l"]["violation"]

        label, tier = tel5_classify(P_effect, phi_violation, k_violation)
        label, tier = apply_l_gate_penalty(label, tier, l_violation)

        # Step 5: Verify final entry structure
        entry = {
            "id": "nutrient:test-substance:sleep:v1",
            "tier": tier,
            "label": label,
            "P_effect_gt_delta": P_effect,
            "gate_results": {
                "phi": gate_results["phi"]["result"],
                "r": gate_results["r"]["score"],
                "j": gate_results["j"]["score"],
                "k": gate_results["k"]["result"],
                "l": gate_results["l"]["result"],
            },
            "evidence_summary": {
                "n_studies": simulation["n_studies"],
                "total_n": simulation["total_n"],
                "I2": simulation["I2"],
                "tau2": simulation["tau2"],
            },
        }

        # Verify structure
        self.assertIn("tier", entry)
        self.assertIn("label", entry)
        self.assertIn("P_effect_gt_delta", entry)
        self.assertIn("gate_results", entry)
        self.assertIn("evidence_summary", entry)

        # Verify gate results
        self.assertIn("phi", entry["gate_results"])
        self.assertIn("r", entry["gate_results"])
        self.assertIn("j", entry["gate_results"])
        self.assertIn("k", entry["gate_results"])
        self.assertIn("l", entry["gate_results"])

        # With this test data, should get high P value and PASS label
        self.assertGreater(P_effect, 0.70, "Expected high probability with test data")

    def test_deterministic_builds(self):
        """Test that same input produces identical output (reproducibility)."""

        # Run analysis twice with same seed
        result1 = run_reml_mc_analysis(
            evidence_rows=self.test_evidence,
            delta=0.20,
            benefit_direction=-1,
            seed=20251005,
            n_draws=10000,
            tau2_method="REML",
        )

        result2 = run_reml_mc_analysis(
            evidence_rows=self.test_evidence,
            delta=0.20,
            benefit_direction=-1,
            seed=20251005,
            n_draws=10000,
            tau2_method="REML",
        )

        # Results should be identical
        self.assertAlmostEqual(
            result1["P_effect_gt_delta"], result2["P_effect_gt_delta"], places=10
        )
        self.assertAlmostEqual(result1["mu_hat"], result2["mu_hat"], places=10)
        self.assertEqual(result1["tau2"], result2["tau2"])
        self.assertEqual(result1["I2"], result2["I2"])


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation integration."""

    def test_schema_validation_with_temp_entry(self):
        """Test schema validation on a temporary entry directory."""

        with tempfile.TemporaryDirectory() as tmpdir:
            entry_dir = Path(tmpdir)

            # Create evidence.csv
            evidence_csv = entry_dir / "evidence.csv"
            with evidence_csv.open("w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "study_id",
                        "year",
                        "design",
                        "effect_type",
                        "effect_point",
                        "ci_low",
                        "ci_high",
                        "n_treat",
                        "n_ctrl",
                        "risk_of_bias",
                        "doi",
                        "journal_id",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "study_id": "Test2023",
                        "year": 2023,
                        "design": "randomized controlled trial",
                        "effect_type": "SMD",
                        "effect_point": -0.40,
                        "ci_low": -0.65,
                        "ci_high": -0.15,
                        "n_treat": 50,
                        "n_ctrl": 50,
                        "risk_of_bias": "low",
                        "doi": "10.1234/test.2023",
                        "journal_id": "ISSN:1234-5678",
                    }
                )

            # Create minimal simulation.json
            simulation = {
                "seed": 20251005,
                "n_draws": 10000,
                "tau2_method": "REML",
                "delta": 0.20,
                "P_effect_gt_delta": 0.85,
                "mu_hat": -0.40,
                "mu_CI95": [-0.65, -0.15],
                "I2": 0.0,
                "tau2": 0.0,
                "n_studies": 1,
                "total_n": 100,
            }
            (entry_dir / "simulation.json").write_text(json.dumps(simulation))

            # Create minimal entry.jsonld
            entry = {
                "@context": "https://schema.org/",
                "@type": "Dataset",
                "id": "test:substance:category:v1",
                "title": "Test Entry",
                "category": "sleep",
                "tier": "Silver",
                "label": "PASS",
                "P_effect_gt_delta": 0.85,
                "gate_results": {
                    "phi": "PASS",
                    "r": "PASS (0.85)",
                    "j": 0.65,
                    "k": "PASS",
                    "l": "PASS",
                },
            }
            (entry_dir / "entry.jsonld").write_text(json.dumps(entry))

            # Create minimal citations.json
            citations = {
                "generated": "2025-10-30T00:00:00+00:00",
                "policy_fingerprint": "0xtest",
                "studies": [],
                "references": [],
            }
            (entry_dir / "citations.json").write_text(json.dumps(citations))

            # Validate all artifacts
            results = validate_all_artifacts(entry_dir)

            # Should pass validation
            self.assertTrue(
                results["overall_valid"],
                f"Validation failed: {results.get('validations')}",
            )


if __name__ == "__main__":
    unittest.main()
