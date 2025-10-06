"""
Gate Governance Protocol (GGP) implementation for VERA.

Implements the five gates: Φ (Natural/Category), R (Relevance), 
J (Journal Trust), K (Safety), and L (Language Exaggeration).
"""

import re
import math
import json
from typing import Dict, Any, List, Tuple, Optional


def sigmoid(x: float, a: float = 3.0, b: float = -1.5) -> float:
    """
    Sigmoid transformation function.
    
    Args:
        x: Input value
        a: Slope parameter (default: 3.0)
        b: Shift parameter (default: -1.5)
    
    Returns:
        Sigmoid-transformed value in [0, 1]
    """
    try:
        return 1.0 / (1.0 + math.exp(-(a * x + b)))
    except OverflowError:
        return 0.0 if (a * x + b) < 0 else 1.0


def compute_j_star(snapshot: Dict[str, Any], journal_id: str) -> float:
    """
    Compute Journal Trust Oracle score (J*) for a given journal.
    
    Combines JCR/SJR percentiles, DOAJ membership, COPE compliance,
    and applies black mask for retracted/predatory/hijacked journals.
    
    Args:
        snapshot: Journal trust snapshot data
        journal_id: Journal identifier
    
    Returns:
        J* score in [0, 1], with 0 for blacklisted journals
    """
    journal_data = snapshot.get("journals", {}).get(journal_id)
    if not journal_data:
        return 0.0
    
    # Black mask: automatic zero for problematic journals
    if (journal_data.get("retracted", 0) or 
        journal_data.get("predatory", 0) or 
        journal_data.get("hijacked", 0)):
        return 0.0
    
    # Compute raw weighted score
    # Weights: IF_z (35%), SJR_z (35%), DOAJ (15%), COPE (15%)
    raw_score = (
        0.35 * journal_data.get("IF_z", 0) +
        0.35 * journal_data.get("SJR_z", 0) +
        0.15 * journal_data.get("DOAJ", 0) +
        0.15 * journal_data.get("COPE", 0)
    )
    
    # Apply sigmoid transformation
    j_score = sigmoid(raw_score, a=3.0, b=-1.5)
    
    # Ensure bounds
    return min(1.0, max(0.0, j_score))


def check_phi_gate(category: str, evidence_rows: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Check Φ (Phi) gate for natural/category violations.
    
    Validates that effect types are appropriate for the given category
    and checks for obvious physical/physiological impossibilities.
    
    Args:
        category: Evidence category (e.g., 'sleep', 'cognition')
        evidence_rows: List of study evidence
    
    Returns:
        Tuple of (gate_result, reason)
        gate_result: "PASS", "AMBER", or "FAIL"
    """
    if not evidence_rows:
        return "FAIL", "No evidence provided"
    
    # Define allowed effect types per category
    allowed_effect_types = {
        "sleep": {"SMD", "MD"},
        "cognition": {"SMD", "MD"},
        "mental_health": {"SMD", "MD"},
        "renal_safety": {"MD", "SMD"},
        "cardiovascular": {"MD", "SMD"},
        "default": {"SMD", "MD", "OR", "RR"}
    }
    
    allowed_types = allowed_effect_types.get(category, allowed_effect_types["default"])
    
    # Check each study's effect type
    violations = []
    for i, study in enumerate(evidence_rows):
        effect_type = study.get("effect_type", "").upper()
        if effect_type not in allowed_types:
            violations.append(f"Study {i+1}: {effect_type} not allowed for {category}")
    
    # Additional category-specific checks
    category_violations = _check_category_specific_violations(category, evidence_rows)
    violations.extend(category_violations)
    
    if violations:
        return "FAIL", "; ".join(violations[:3])  # Limit to first 3 violations
    
    return "PASS", "All studies use appropriate effect types for category"


def _check_category_specific_violations(category: str, evidence_rows: List[Dict[str, Any]]) -> List[str]:
    """
    Check for category-specific violations (internal helper).
    
    Args:
        category: Evidence category
        evidence_rows: List of study evidence
    
    Returns:
        List of violation messages
    """
    violations = []
    
    # Safety categories should have appropriate direction
    if category in ["renal_safety", "cardiovascular"]:
        for i, study in enumerate(evidence_rows):
            effect_point = study.get("effect_point", 0)
            # For safety, we generally expect neutral or positive effects
            # (though this depends on specific measures)
            if effect_point < -2.0:  # Arbitrary threshold for demonstration
                violations.append(f"Study {i+1}: Large negative effect in safety category")
    
    return violations


def check_r_gate(evidence_rows: List[Dict[str, Any]], 
                category: str,
                min_relevance: float = 0.5) -> Tuple[str, float, str]:
    """
    Check R (Relevance) gate.
    
    Assesses the relevance of evidence to the claimed category.
    This is a simplified implementation - in practice would involve
    more sophisticated relevance scoring.
    
    Args:
        evidence_rows: List of study evidence
        category: Target category
        min_relevance: Minimum relevance threshold
    
    Returns:
        Tuple of (gate_result, relevance_score, reason)
    """
    if not evidence_rows:
        return "FAIL", 0.0, "No evidence provided"
    
    # Simplified relevance scoring based on study design and measures
    relevance_scores = []
    
    for study in evidence_rows:
        design = study.get("design", "").lower()
        measures = study.get("measures", "")
        
        # Base score from study design
        if "rct" in design or "randomized" in design:
            base_score = 0.9
        elif "cohort" in design:
            base_score = 0.7
        elif "cross-sectional" in design:
            base_score = 0.5
        else:
            base_score = 0.3
        
        # Adjust based on outcome measures (simplified)
        measure_bonus = 0.0
        if category == "sleep" and any(m in measures.lower() for m in ["psqi", "isi", "sleep"]):
            measure_bonus = 0.1
        elif category == "cognition" and any(m in measures.lower() for m in ["mmse", "moca", "cognitive"]):
            measure_bonus = 0.1
        
        study_relevance = min(1.0, base_score + measure_bonus)
        relevance_scores.append(study_relevance)
    
    # Overall relevance is average of study relevances
    overall_relevance = sum(relevance_scores) / len(relevance_scores)
    
    if overall_relevance >= min_relevance:
        return "PASS", overall_relevance, f"Average relevance: {overall_relevance:.3f}"
    else:
        return "FAIL", overall_relevance, f"Relevance {overall_relevance:.3f} below threshold {min_relevance}"


def check_j_gate(evidence_rows: List[Dict[str, Any]], 
                snapshot: Dict[str, Any],
                min_j: float = 0.25,
                blacklist_nulls: bool = True) -> Tuple[str, float, str]:
    """
    Check J (Journal Trust) gate using Journal Trust Oracle.
    
    Args:
        evidence_rows: List of study evidence
        snapshot: Journal trust snapshot
        min_j: Minimum J* threshold
        blacklist_nulls: Whether to fail on any zero J* scores
    
    Returns:
        Tuple of (gate_result, j_star_avg, reason)
    """
    if not evidence_rows:
        return "FAIL", 0.0, "No evidence provided"
    
    j_scores = []
    blacklisted_journals = []
    
    for study in evidence_rows:
        journal_id = study.get("journal_id", "")
        j_score = compute_j_star(snapshot, journal_id)
        j_scores.append(j_score)
        
        if j_score == 0.0:
            blacklisted_journals.append(journal_id)
    
    # Apply blacklist policy
    if blacklist_nulls and blacklisted_journals:
        return "FAIL", 0.0, f"Blacklisted journals: {', '.join(blacklisted_journals[:3])}"
    
    # Compute average J* (excluding zeros if not blacklisting)
    valid_scores = [s for s in j_scores if s > 0.0] if not blacklist_nulls else j_scores
    
    if not valid_scores:
        return "FAIL", 0.0, "No valid journal scores"
    
    j_star_avg = sum(valid_scores) / len(valid_scores)
    
    if j_star_avg >= min_j:
        return "PASS", j_star_avg, f"Average J*: {j_star_avg:.3f}"
    else:
        return "FAIL", j_star_avg, f"J* {j_star_avg:.3f} below threshold {min_j}"


def check_k_gate(evidence_rows: List[Dict[str, Any]], 
                category: str) -> Tuple[str, str]:
    """
    Check K (Safety) gate for safety violations.
    
    Assesses whether the intervention poses safety concerns
    based on the evidence provided.
    
    Args:
        evidence_rows: List of study evidence
        category: Evidence category
    
    Returns:
        Tuple of (gate_result, reason)
    """
    if not evidence_rows:
        return "PASS", "No evidence to assess safety"
    
    safety_concerns = []
    
    for i, study in enumerate(evidence_rows):
        # Check for adverse events reporting
        adverse_events = study.get("adverse_events", "")
        risk_of_bias = study.get("risk_of_bias", "").lower()
        
        # Flag studies with high risk of bias in safety-related categories
        if category in ["renal_safety", "cardiovascular"] and "high" in risk_of_bias:
            safety_concerns.append(f"Study {i+1}: High risk of bias in safety category")
        
        # Check for reported serious adverse events
        if "serious" in adverse_events.lower() or "death" in adverse_events.lower():
            safety_concerns.append(f"Study {i+1}: Serious adverse events reported")
    
    if safety_concerns:
        return "FAIL", "; ".join(safety_concerns[:2])
    
    return "PASS", "No safety concerns identified"


def check_l_gate(text_content: str, deny_patterns: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Check L (Language) gate for exaggerated claims.
    
    Detects problematic language patterns that suggest
    exaggerated or misleading claims.
    
    Args:
        text_content: Text to analyze for exaggerated language
        deny_patterns: List of regex patterns to flag
    
    Returns:
        Tuple of (violation_detected, matched_pattern)
    """
    if not text_content or not deny_patterns:
        return False, None
    
    # Check each deny pattern
    for pattern in deny_patterns:
        try:
            if re.search(pattern, text_content, flags=re.IGNORECASE):
                return True, pattern
        except re.error:
            # Skip invalid regex patterns
            continue
    
    return False, None


def apply_monotonic_capping(j_score: float, 
                          phi_violation: bool, 
                          k_violation: bool) -> float:
    """
    Apply monotonic capping based on Φ/K gate violations.
    
    Implements safety-first monotonicity where Φ/K violations
    cannot be offset by high journal trust scores.
    
    Args:
        j_score: Original J* score
        phi_violation: Whether Φ gate failed
        k_violation: Whether K gate failed
    
    Returns:
        Capped J* score
    """
    if phi_violation or k_violation:
        return 0.0  # Hard cap to zero for safety violations
    
    return j_score


def evaluate_all_gates(evidence_rows: List[Dict[str, Any]],
                      category: str,
                      journal_snapshot: Dict[str, Any],
                      policy: Dict[str, Any],
                      text_content: str = "") -> Dict[str, Any]:
    """
    Evaluate all five gates and return comprehensive results.
    
    Args:
        evidence_rows: List of study evidence
        category: Evidence category
        journal_snapshot: Journal trust snapshot
        policy: Policy configuration
        text_content: Text content for L-gate analysis
    
    Returns:
        Dictionary with all gate results
    """
    gates_config = policy.get("gates", {})
    
    # Φ Gate (Natural/Category)
    phi_result, phi_reason = check_phi_gate(category, evidence_rows)
    phi_violation = (phi_result == "FAIL")
    
    # R Gate (Relevance) 
    r_min = gates_config.get("r", {}).get("min_relevance", 0.5)
    r_result, r_score, r_reason = check_r_gate(evidence_rows, category, r_min)
    
    # K Gate (Safety)
    k_result, k_reason = check_k_gate(evidence_rows, category)
    k_violation = (k_result == "FAIL")
    
    # J Gate (Journal Trust)
    j_config = gates_config.get("j", {})
    j_min = j_config.get("min_j", 0.25)
    j_blacklist = j_config.get("blacklist_nulls", True)
    j_result, j_score, j_reason = check_j_gate(evidence_rows, journal_snapshot, j_min, j_blacklist)
    
    # Apply monotonic capping to J score
    j_score_capped = apply_monotonic_capping(j_score, phi_violation, k_violation)
    
    # L Gate (Language)
    l_patterns = gates_config.get("l", {}).get("deny_patterns", [])
    l_violation, l_pattern = check_l_gate(text_content, l_patterns)
    l_result = "FLAG" if l_violation else "PASS"
    
    return {
        "phi": {
            "result": phi_result,
            "reason": phi_reason,
            "violation": phi_violation
        },
        "r": {
            "result": r_result,
            "score": r_score,
            "reason": r_reason
        },
        "j": {
            "result": j_result,
            "score": j_score,
            "score_capped": j_score_capped,
            "reason": j_reason
        },
        "k": {
            "result": k_result,
            "reason": k_reason,
            "violation": k_violation
        },
        "l": {
            "result": l_result,
            "violation": l_violation,
            "pattern": l_pattern
        },
        "summary": {
            "phi_violation": phi_violation,
            "k_violation": k_violation,
            "l_violation": l_violation,
            "j_score_final": j_score_capped,
            "safety_monotonic": phi_violation or k_violation
        }
    }