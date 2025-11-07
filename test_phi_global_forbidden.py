#!/usr/bin/env python3
"""
Test script for global forbidden patterns in Φ gate.

Tests that non-local devices and pseudoscientific interventions
are correctly rejected by the Φ gate regardless of category.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from engine.gates import check_phi_gate

# Test cases: (substance, claim_text, expected_result, description)
TEST_CASES = [
    # SHOULD FAIL - Germanium bracelets
    (
        "germanium bracelet",
        "Germanium bracelet improves sleep quality",
        "FAIL",
        "Germanium bracelet (English)"
    ),
    (
        "게르마늄 팔찌",
        "게르마늄 팔찌는 수면의 질을 개선합니다",
        "FAIL",
        "Germanium bracelet (Korean)"
    ),

    # SHOULD FAIL - Magnetic bracelets
    (
        "magnetic bracelet",
        "Magnetic therapy band for pain relief",
        "FAIL",
        "Magnetic bracelet (English)"
    ),
    (
        "자석 팔찌",
        "자석 팔찌로 혈액순환 개선",
        "FAIL",
        "Magnetic bracelet (Korean)"
    ),

    # SHOULD FAIL - Ion bracelets
    (
        "ion band",
        "Negative ion wristband boosts energy",
        "FAIL",
        "Ion bracelet (English)"
    ),
    (
        "이온 밴드",
        "이온 팔찌로 피로 회복",
        "FAIL",
        "Ion bracelet (Korean)"
    ),

    # SHOULD FAIL - Copper bracelets
    (
        "copper bracelet",
        "Copper jewelry for arthritis relief",
        "FAIL",
        "Copper bracelet claiming systemic effect"
    ),

    # SHOULD FAIL - Quantum pseudoscience
    (
        "quantum pendant",
        "Quantum energy pendant for wellness",
        "FAIL",
        "Quantum pseudoscience device"
    ),

    # SHOULD FAIL - Bioresonance
    (
        "bioresonance device",
        "Bio-frequency therapy for detox",
        "FAIL",
        "Bioresonance device"
    ),

    # SHOULD FAIL - Scalar waves
    (
        "scalar energy bracelet",
        "Scalar wave technology for healing",
        "FAIL",
        "Scalar wave pseudoscience"
    ),

    # SHOULD FAIL - Detox foot pads
    (
        "detox foot pad",
        "Foot detox pads remove toxins",
        "FAIL",
        "Detox foot pad"
    ),

    # SHOULD PASS - Legitimate supplements
    (
        "magnesium glycinate",
        "Magnesium supplementation for sleep quality",
        "PASS",
        "Magnesium glycinate (legitimate supplement)"
    ),
    (
        "omega-3",
        "Omega-3 fatty acids for cardiovascular health",
        "PASS",
        "Omega-3 (legitimate supplement)"
    ),

    # SHOULD PASS - Evidence-based devices (EMS, TENS)
    # Note: These should pass Φ gate (plausible mechanism) but will be evaluated by R/J/K/L gates
    (
        "TENS unit",
        "Transcutaneous electrical nerve stimulation for pain",
        "PASS",
        "TENS (evidence-based device with local action)"
    ),
]


def run_tests():
    """Run all test cases and report results."""

    print("=" * 80)
    print("TESTING GLOBAL FORBIDDEN PATTERNS IN Φ GATE")
    print("=" * 80)
    print()

    # Create dummy evidence for testing (minimal valid structure)
    dummy_evidence = [
        {
            "study_id": "test_001",
            "effect_type": "SMD",
            "effect_point": 0.3,
            "ci_low": 0.1,
            "ci_high": 0.5,
        }
    ]

    passed = 0
    failed = 0

    for substance, claim, expected, description in TEST_CASES:
        result, reason = check_phi_gate(
            category="sleep",  # Use sleep as test category
            evidence_rows=dummy_evidence,
            substance=substance,
            claim_text=claim
        )

        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} | {description}")
        print(f"   Substance: {substance}")
        print(f"   Claim: {claim}")
        print(f"   Expected: {expected} | Got: {result}")
        if result == "FAIL":
            print(f"   Reason: {reason}")
        print()

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
