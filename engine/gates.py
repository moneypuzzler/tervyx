"""
Gate Governance Protocol (GGP) implementation for TERVYX Protocol.

Implements the five sequential gates: Φ (Natural/Category), R (Relevance), 
J (Journal Trust), K (Safety), and L (Language Exaggeration) with safety-first 
monotonicity where Φ or K violations cannot be offset by high J scores.
"""

import re
import math
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, List, Tuple, Optional
import logging

import yaml

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT_DIR / "protocol"


@lru_cache(maxsize=1)
def _load_phi_rules() -> Dict[str, Any]:
    rules_path = RULES_DIR / "phi_rules.yaml"
    with rules_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=1)
def _load_l_rules() -> Dict[str, Any]:
    rules_path = RULES_DIR / "L_rules.yaml"
    with rules_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def sigmoid(x: float, a: float = 3.0, b: float = -1.5) -> float:
    """
    Calibrated sigmoid transformation for Journal-Trust Oracle.
    
    Args:
        x: Input value (raw J score)
        a: Slope parameter (default: 3.0)
        b: Shift parameter (default: -1.5)
    
    Returns:
        Sigmoid-transformed value in [0, 1]
    """
    try:
        return 1.0 / (1.0 + math.exp(-(a * x + b)))
    except OverflowError:
        return 0.0 if (a * x + b) < 0 else 1.0


def compute_journal_trust_score(snapshot: Dict[str, Any], journal_id: str) -> float:
    """
    Compute Journal-Trust Oracle score (J*) with BLACK pre-mask and signal fusion.
    
    Implements the J* algorithm from TERVYX Protocol:
    1. BLACK pre-mask: Retraction/Predatory/Hijacked → J* = 0
    2. Raw linear combination of normalized signals
    3. Calibrated squashing with sigmoid
    4. Clipping to [0, 1] bounds
    
    Args:
        snapshot: Journal trust snapshot data
        journal_id: Journal identifier
    
    Returns:
        J* score in [0, 1], with 0 for blacklisted journals
    """
    journal_data = snapshot.get("journals", {}).get(journal_id)
    if not journal_data:
        logger.warning(f"Journal '{journal_id}' not found in trust snapshot")
        return 0.0
    
    # BLACK pre-mask: automatic zero for problematic journals
    retracted = journal_data.get("retracted", 0)
    predatory = journal_data.get("predatory", 0) 
    hijacked = journal_data.get("hijacked", 0)
    
    if retracted or predatory or hijacked:
        violation_types = []
        if retracted: violation_types.append("retracted")
        if predatory: violation_types.append("predatory") 
        if hijacked: violation_types.append("hijacked")
        logger.info(f"Journal '{journal_id}' blacklisted: {', '.join(violation_types)}")
        return 0.0
    
    # Raw linear combination (policy-tunable weights from paper)
    IF_z = journal_data.get("IF_z", 0.0)      # JCR percentile normalized
    SJR_z = journal_data.get("SJR_z", 0.0)    # SJR percentile normalized  
    DOAJ = journal_data.get("DOAJ", 0.0)      # Binary DOAJ membership
    COPE = journal_data.get("COPE", 0.0)      # Binary COPE compliance
    
    J_raw = (0.35 * IF_z + 0.35 * SJR_z + 0.15 * DOAJ + 0.05 * COPE 
             - 0.50 * retracted - 0.50 * predatory - 0.30 * hijacked)
    
    # Calibrated squashing + clipping
    j_score = sigmoid(J_raw, a=3.0, b=-1.5)
    return max(0.0, min(1.0, j_score))


def check_phi_gate(category: str, evidence_rows: List[Dict[str, Any]],
                   substance: str = "") -> Tuple[str, str]:
    """Evaluate Φ gate using deterministic policy rules."""

    if not evidence_rows:
        return "FAIL", "No evidence provided for Φ gate evaluation"

    rules = _load_phi_rules()
    category_rules = (rules.get("categories") or {}).get(category)

    if not category_rules:
        return "FAIL", f"Unknown category '{category}' - cannot validate appropriateness"

    violations: List[str] = []
    allowed_effects = {str(eff).upper() for eff in category_rules.get("allowed_effects", [])}

    for idx, study in enumerate(evidence_rows, start=1):
        effect_type = str(study.get("effect_type", "")).upper()
        if allowed_effects and effect_type not in allowed_effects:
            violations.append(f"Study {idx}: {effect_type} not permitted for {category}")

        effect_point = float(study.get("effect_point", 0) or 0)

        for cap in category_rules.get("physiological_caps", []) or []:
            effect_types = {str(e).upper() for e in cap.get("effect_types", []) if e}
            if effect_types and effect_type not in effect_types:
                continue

            if "max_abs" in cap and abs(effect_point) > float(cap["max_abs"]):
                violations.append(
                    f"Study {idx}: {cap.get('id', 'cap')} |effect| {abs(effect_point):.2f} > {cap['max_abs']}"
                )
            if "max" in cap and effect_point > float(cap["max"]):
                violations.append(
                    f"Study {idx}: {cap.get('id', 'cap')} effect {effect_point:.2f} > {cap['max']}"
                )
            if "min" in cap and effect_point < float(cap["min"]):
                violations.append(
                    f"Study {idx}: {cap.get('id', 'cap')} effect {effect_point:.2f} < {cap['min']}"
                )

    substance_lower = substance.lower()
    for ban in category_rules.get("forbidden_substances", []) or []:
        pattern = str(ban.get("pattern", "")).lower()
        if pattern and pattern in substance_lower:
            violations.append(ban.get("reason", f"Substance pattern '{pattern}' blocked for {category}"))

    for rule in rules.get("misrouting", []) or []:
        pattern = str(rule.get("substance_pattern", "")).lower()
        blocked = {str(cat).lower() for cat in rule.get("blocked_categories", [])}
        if pattern and pattern in substance_lower and category.lower() in blocked:
            violations.append(rule.get("reason", "Category misrouting detected"))

    if violations:
        reason = "Category/physiological violations: " + "; ".join(violations[:2])
        return "FAIL", reason

    return "PASS", "No category misrouting or physiological impossibilities detected"


def _check_category_misrouting(*_args: Any, **_kwargs: Any) -> List[str]:  # pragma: no cover - backward compat
    logger.warning("_check_category_misrouting is deprecated; Φ rules now handled via protocol/phi_rules.yaml")
    return []


def _check_physiological_impossibilities(*_args: Any, **_kwargs: Any) -> List[str]:  # pragma: no cover
    logger.warning("_check_physiological_impossibilities is deprecated; Φ caps now handled via protocol rules")
    return []


def check_r_gate(evidence_rows: List[Dict[str, Any]], 
                category: str,
                threshold: float = 0.7) -> Tuple[str, float, str]:
    """
    Check R (Relevance) gate for routing fit between claim and category.
    
    Evaluates how well the evidence matches the target category.
    Below threshold results in AMBER↓ or exclusion.
    
    Args:
        evidence_rows: List of study evidence
        category: Target category
        threshold: Relevance threshold (default: 0.7)
    
    Returns:
        Tuple of (qualitative_result, relevance_score, reason)
    """
    if not evidence_rows:
        return "LOW", 0.0, "No evidence provided"
    
    total_weight = 0
    weighted_sum = 0
    
    for study in evidence_rows:
        relevance = _compute_study_relevance(study, category)
        weight = study.get("n_treat", 0) + study.get("n_ctrl", 0)

        weighted_sum += relevance * weight
        total_weight += weight
    
    # Overall relevance is weighted average (could use median for robustness)
    if total_weight == 0:
        overall_relevance = 0.0
    else:
        overall_relevance = weighted_sum / total_weight
    
    # Map to qualitative categories
    if overall_relevance >= 0.8:
        return "HIGH", overall_relevance, f"High relevance: {overall_relevance:.3f}"
    elif overall_relevance >= threshold:
        return "MEDIUM", overall_relevance, f"Medium relevance: {overall_relevance:.3f}"
    else:
        return "LOW", overall_relevance, f"Low relevance: {overall_relevance:.3f} (threshold: {threshold})"


def _compute_study_relevance(study: Dict[str, Any], category: str) -> float:
    """Compute individual study relevance score."""
    base_score = 0.5  # Default baseline
    
    # Study design contribution
    design = study.get("design", "").lower()
    if "rct" in design or "randomized" in design:
        design_score = 0.9
    elif "cohort" in design:
        design_score = 0.7
    elif "cross-sectional" in design:
        design_score = 0.5
    else:
        design_score = 0.3
    
    # Outcome measure relevance
    outcome = study.get("outcome", "").lower()
    measure_score = 0.0
    
    category_measures = {
        "sleep": ["psqi", "isi", "sleep efficiency", "sleep latency", "sleep quality"],
        "cognition": ["mmse", "moca", "cognitive", "memory", "attention"],
        "mental_health": ["phq", "gad", "hamilton", "beck", "depression", "anxiety"],
        "renal_safety": ["egfr", "creatinine", "bun", "kidney", "renal"],
        "cardiovascular": ["blood pressure", "bp", "ldl", "hdl", "cholesterol"]
    }
    
    relevant_measures = category_measures.get(category, [])
    if any(measure in outcome for measure in relevant_measures):
        measure_score = 0.2
    
    # Population relevance
    population = study.get("population", "").lower()
    population_score = 0.0
    if category == "sleep" and any(term in population for term in ["insomnia", "sleep"]):
        population_score = 0.1
    elif category == "renal_safety" and any(term in population for term in ["kidney", "renal"]):
        population_score = 0.1
    
    return min(1.0, design_score + measure_score + population_score)


def check_j_gate(evidence_rows: List[Dict[str, Any]], 
                snapshot: Dict[str, Any],
                threshold: float = 0.25) -> Tuple[str, float, str]:
    """
    Check J (Journal Trust) gate using Journal-Trust Oracle.
    
    Computes average J* scores across all studies. Predatory/hijacked/retracted
    journals automatically result in J-BLACK = 0.
    
    Args:
        evidence_rows: List of study evidence
        snapshot: Journal trust snapshot (dated)
        threshold: Minimum acceptable J* threshold
    
    Returns:
        Tuple of (gate_result, j_star_average, reason)
    """
    if not evidence_rows:
        return "FAIL", 0.0, "No evidence provided"
    
    j_scores = []
    blacklisted_count = 0
    
    for study in evidence_rows:
        journal_id = study.get("journal_id", "")
        if not journal_id:
            logger.warning(f"Study {study.get('study_id', 'unknown')} missing journal_id")
            j_scores.append(0.0)
            continue
            
        j_score = compute_journal_trust_score(snapshot, journal_id)
        j_scores.append(j_score)
        
        if j_score == 0.0:
            blacklisted_count += 1
    
    if not j_scores:
        return "FAIL", 0.0, "No journal scores available"
    
    # Compute average (including zeros from blacklisted journals)
    j_star_avg = sum(j_scores) / len(j_scores)
    
    # Assessment
    if blacklisted_count > 0:
        if blacklisted_count == len(j_scores):
            return "FAIL", 0.0, f"All {blacklisted_count} journals blacklisted"
        else:
            reason = f"J*={j_star_avg:.3f} ({blacklisted_count}/{len(j_scores)} blacklisted)"
    else:
        reason = f"Average J*: {j_star_avg:.3f}"
    
    result = "PASS" if j_star_avg >= threshold else "FAIL"
    return result, j_star_avg, reason


def check_k_gate(evidence_rows: List[Dict[str, Any]], 
                category: str,
                substance: str = "") -> Tuple[str, str]:
    """
    Check K (Safety) gate for contraindications and serious adverse events.
    
    This is the second safety gate that enforces absolute safety caps.
    Violations here result in BLACK tier regardless of efficacy evidence.
    
    Args:
        evidence_rows: List of study evidence
        category: Evidence category
        substance: Substance name for safety database lookup
    
    Returns:
        Tuple of (gate_result, reason) 
        gate_result: "PASS" or "FAIL" (no AMBER for safety gates)
    """
    if not evidence_rows:
        return "PASS", "No evidence to assess for safety violations"
    
    safety_violations = []
    
    # Check for reported serious adverse events
    for i, study in enumerate(evidence_rows):
        adverse_events = study.get("adverse_events", "").lower()
        duration_weeks = study.get("duration_weeks", 0)
        
        # Flag serious adverse events
        serious_ae_patterns = ["death", "hospitalization", "serious", "severe", "toxic"]
        if any(pattern in adverse_events for pattern in serious_ae_patterns):
            safety_violations.append(f"Study {i+1}: Serious adverse events reported")
        
        # Check for concerning study characteristics in safety categories
        if category in ["renal_safety", "cardiovascular"]:
            risk_of_bias = study.get("risk_of_bias", "").lower()
            if "high" in risk_of_bias:
                safety_violations.append(f"Study {i+1}: High bias risk in safety category")
            
            # Flag very long interventions without safety monitoring
            if duration_weeks > 52:  # > 1 year
                safety_violations.append(f"Study {i+1}: Extended intervention without safety data")
    
    # Substance-specific safety checks
    substance_violations = _check_substance_safety(substance, evidence_rows)
    safety_violations.extend(substance_violations)
    
    if safety_violations:
        reason = f"Safety violations: {'; '.join(safety_violations[:2])}"
        return "FAIL", reason
    
    return "PASS", "No contraindications or serious adverse events identified"


def _check_substance_safety(substance: str, evidence_rows: List[Dict[str, Any]]) -> List[str]:
    """Check substance-specific safety contraindications."""
    violations = []
    
    # Example safety database lookup (simplified)
    substance_lower = substance.lower()
    
    if "magnesium" in substance_lower:
        # Check for renal impairment populations (magnesium can accumulate)
        for i, study in enumerate(evidence_rows):
            population = study.get("population", "").lower()
            if "renal" in population or "kidney" in population:
                violations.append(f"Study {i+1}: Magnesium in renal impairment population")
    
    # Additional substance-specific rules would be loaded from safety database
    
    return violations


def check_l_gate(text_content: str, language: str = "en") -> Tuple[str, bool, Optional[str]]:
    """Check L-gate using rule table from protocol/L_rules.yaml."""

    if not text_content:
        return "PASS", False, None

    rules = _load_l_rules()
    language = language.lower()

    if language not in {"en", "ko", "bilingual"}:
        language = "bilingual"

    lang_keys = ["en"] if language == "en" else ["ko"] if language == "ko" else ["en", "ko"]

    for entry in rules.get("forbidden", []) or []:
        patterns: List[str] = []
        for key in lang_keys:
            patterns.extend(entry.get(key, []))

        exceptions = [re.compile(exc, re.IGNORECASE) for exc in entry.get("exceptions", [])]

        for pattern in patterns:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:  # pragma: no cover - defensive logging
                logger.warning("Invalid L-gate regex '%s': %s", pattern, exc)
                continue

            match = regex.search(text_content)
            if not match:
                continue

            context = text_content[max(0, match.start() - 50): match.end() + 50]
            if any(exc.search(context) for exc in exceptions):
                continue

            return "FLAG", True, entry.get("id", pattern)

    return "PASS", False, None


def apply_monotonic_masking(j_score: float, phi_violation: bool, k_violation: bool) -> float:
    """
    Apply safety-first monotonic masking/capping to Journal Trust scores.
    
    Core principle: Φ or K violations cannot be offset by high J scores.
    This implements the "monotone masking/capping" mentioned in the paper.
    
    Args:
        j_score: Original J* score [0, 1]
        phi_violation: Whether Φ gate failed
        k_violation: Whether K gate failed
    
    Returns:
        Masked J* score (0.0 if any safety violation)
    """
    if phi_violation or k_violation:
        logger.info("Safety violation detected - applying monotonic masking to J* score")
        return 0.0  # Hard mask to zero
    
    return j_score


def evaluate_gate_governance_protocol(evidence_rows: List[Dict[str, Any]],
                                    category: str,
                                    journal_snapshot: Dict[str, Any],
                                    policy: Dict[str, Any],
                                    substance: str = "",
                                    claim_text: str = "") -> Dict[str, Any]:
    """
    Evaluate complete Gate Governance Protocol (GGP): Φ → R → J → K → L.
    
    Implements the sequential gate evaluation with safety-first monotonicity
    as specified in the TERVYX Protocol paper.
    
    Args:
        evidence_rows: List of study evidence (ESV format)
        category: Target evidence category
        journal_snapshot: Dated journal trust snapshot
        policy: Policy configuration with gate parameters
        substance: Substance name for context
        claim_text: Claim text for L-gate analysis
    
    Returns:
        Dictionary with comprehensive gate results and summary
    """
    gates_config = policy.get("gates", {})
    
    # Gate Φ: Natural/Category violation (deterministic safety gate)
    phi_result, phi_reason = check_phi_gate(category, evidence_rows, substance)
    phi_violation = (phi_result == "FAIL")
    
    # Gate R: Relevance assessment 
    r_threshold = gates_config.get("r", {}).get("threshold", 0.7)
    r_result, r_score, r_reason = check_r_gate(evidence_rows, category, r_threshold)
    
    # Gate J: Journal Trust Oracle
    j_threshold = gates_config.get("j", {}).get("threshold", 0.25)
    j_result, j_score, j_reason = check_j_gate(evidence_rows, journal_snapshot, j_threshold)
    
    # Gate K: Safety assessment (deterministic safety gate)
    k_result, k_reason = check_k_gate(evidence_rows, category, substance)
    k_violation = (k_result == "FAIL")
    
    # Apply monotonic masking to J* score
    j_score_masked = apply_monotonic_masking(j_score, phi_violation, k_violation)

    # Enforce J-gate threshold on masked score (safety-first)
    j_enforce_threshold = gates_config.get("j", {}).get("enforce_threshold", True)
    if j_enforce_threshold and j_score_masked < j_threshold:
        # Override j_result to FAIL if masked score below threshold
        j_result = "FAIL"
        logger.warning(f"J-gate threshold enforcement: j_score_masked={j_score_masked:.3f} < threshold={j_threshold}")

    # Gate L: Exaggeration language
    l_result, l_violation, l_pattern = check_l_gate(claim_text)

    # Determine overall gate sequence result
    # Must pass all hard gates: Phi, K, and J (with threshold enforcement)
    gate_sequence_pass = (
        phi_result == "PASS" and
        k_result == "PASS" and
        j_result == "PASS" and
        (not j_enforce_threshold or j_score_masked >= j_threshold)
    )
    
    return {
        "phi": {
            "result": phi_result,
            "reason": phi_reason,
            "violation": phi_violation,
            "safety_critical": True
        },
        "r": {
            "result": r_result,
            "score": r_score,
            "threshold": r_threshold,
            "reason": r_reason
        },
        "j": {
            "result": j_result,
            "score": j_score,
            "score_masked": j_score_masked,
            "threshold": j_threshold,
            "reason": j_reason
        },
        "k": {
            "result": k_result,
            "reason": k_reason,
            "violation": k_violation,
            "safety_critical": True
        },
        "l": {
            "result": l_result,
            "violation": l_violation,
            "pattern": l_pattern
        },
        "summary": {
            "gate_sequence": "Φ → R → J → K → L",
            "safety_violations": phi_violation or k_violation,
            "phi_violation": phi_violation,
            "k_violation": k_violation,
            "l_violation": l_violation,
            "j_score_final": j_score_masked,
            "monotonic_masking_applied": (j_score != j_score_masked),
            "overall_pass": gate_sequence_pass and not l_violation
        },
        "policy_refs": {
            "gates_version": gates_config.get("version", "v1.0.0"),
            "journal_snapshot_date": journal_snapshot.get("snapshot_date", "unknown"),
            "evaluation_timestamp": journal_snapshot.get("snapshot_date", "2025-10-15")
        }
    }


# Maintain backward compatibility with legacy naming
def evaluate_all_gates(*args, **kwargs):
    """Backward compatibility wrapper for evaluate_gate_governance_protocol."""
    logger.warning("evaluate_all_gates() is deprecated, use evaluate_gate_governance_protocol() instead")
    return evaluate_gate_governance_protocol(*args, **kwargs)


def compute_j_star(*args, **kwargs):
    """Backward compatibility wrapper for compute_journal_trust_score."""
    logger.warning("compute_j_star() is deprecated, use compute_journal_trust_score() instead")  
    return compute_journal_trust_score(*args, **kwargs)