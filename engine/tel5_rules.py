"""
TEL-5 (TERVYX Evidence Levels) labeling system for TERVYX Protocol.

Implements the 5-tier classification system that maps P(effect > δ) probabilities 
to TEL-5 tiers (Gold/Silver/Bronze/Red/Black) with Gate Governance Protocol enforcement.
"""

from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def tel5_classify(P: float, phi_violation: bool = False, k_violation: bool = False) -> Tuple[str, str]:
    """
    Determine TEL-5 tier and label based on effect probability and gate violations.
    
    Implements the core TEL-5 classification algorithm with safety-first monotonicity:
    - Φ or K violations cannot be offset by high P values
    - PASS cannot be upgraded under Φ/K violations
    
    Args:
        P: Probability that effect > δ (minimally important difference)
        phi_violation: Whether Φ (natural/category) gate failed
        k_violation: Whether K (safety) gate failed
    
    Returns:
        Tuple of (label, tier) where:
        - label: PASS, AMBER, or FAIL
        - tier: Gold, Silver, Bronze, Red, or Black
    """
    # Safety-first monotonicity: Φ/K violations → BLACK (cannot be offset)
    if phi_violation or k_violation:
        return "FAIL", "Black"
    
    # Standard TEL-5 tier assignment based on P(effect > δ)
    if P >= 0.90:
        return "PASS", "Gold"      # High confidence
    elif P >= 0.75:
        return "PASS", "Silver"    # Moderate confidence
    elif P >= 0.60:
        return "AMBER", "Bronze"   # Low confidence
    elif P >= 0.20:
        return "AMBER", "Red"      # Very low confidence
    else:
        return "FAIL", "Black"     # Inappropriate/Risky


def apply_l_gate_penalty(label: str, tier: str, l_violation: bool) -> Tuple[str, str]:
    """
    Apply L-gate (exaggeration language) corrective down-shift.
    
    The L-gate implements a soft penalty system where exaggerated language
    ("cure/permanent/instant/miracle/risk-free") causes a downward shift
    in tier assignment but not automatic failure (unlike Φ/K gates).
    
    Args:
        label: Current label (PASS, AMBER, FAIL)
        tier: Current tier (Gold, Silver, Bronze, Red, Black)
        l_violation: Whether exaggerated language patterns were detected
    
    Returns:
        Tuple of (adjusted_label, adjusted_tier)
    """
    if not l_violation or label == "FAIL":
        return label, tier
    
    # Corrective down-shift implementation
    if label == "PASS":
        # PASS demoted to AMBER
        if tier == "Gold":
            return "AMBER", "Bronze"  # Gold → Bronze
        elif tier == "Silver":
            return "AMBER", "Red"     # Silver → Red
    
    elif label == "AMBER":
        # AMBER demoted within AMBER tier
        if tier == "Bronze":
            return "AMBER", "Red"     # Bronze → Red
        # Red is already lowest AMBER tier, no further demotion
    
    return label, tier


def get_tel5_tier_info(tier: str) -> Dict[str, Any]:
    """
    Get detailed description and properties of a TEL-5 tier.
    
    Args:
        tier: Tier name (Gold, Silver, Bronze, Red, Black)
    
    Returns:
        Dictionary with tier properties, thresholds, and descriptions
    """
    tier_info = {
        "Gold": {
            "tel5_level": 1,
            "min_probability": 0.90,
            "label": "PASS",
            "color": "#FFD700",
            "confidence": "High",
            "description": "High confidence evidence (P ≥ 0.90)",
            "recommendation": "Evidence strongly supports the claimed benefit",
            "icon": "🥇"
        },
        "Silver": {
            "tel5_level": 2,
            "min_probability": 0.75,
            "label": "PASS",
            "color": "#C0C0C0",
            "confidence": "Moderate",
            "description": "Moderate confidence evidence (P ≥ 0.75)",
            "recommendation": "Evidence supports the claimed benefit",
            "icon": "🥈"
        },
        "Bronze": {
            "tel5_level": 3,
            "min_probability": 0.60,
            "label": "AMBER",
            "color": "#CD7F32",
            "confidence": "Low",
            "description": "Low confidence evidence (P ≥ 0.60)",
            "recommendation": "Evidence provides limited support; further research needed",
            "icon": "🥉"
        },
        "Red": {
            "tel5_level": 4,
            "min_probability": 0.20,
            "label": "AMBER",
            "color": "#DC3545",
            "confidence": "Very Low",
            "description": "Very low confidence evidence (P ≥ 0.20)",
            "recommendation": "Evidence is insufficient; caution advised",
            "icon": "🔴"
        },
        "Black": {
            "tel5_level": 5,
            "min_probability": 0.00,
            "label": "FAIL",
            "color": "#000000",
            "confidence": "None/Inappropriate",
            "description": "Inappropriate/Risky (P < 0.20 or Φ/K violations)",
            "recommendation": "Claim not supported by evidence or poses safety concerns",
            "icon": "⚫"
        }
    }
    
    return tier_info.get(tier, {})


def compute_tel5_statistics(entries: list) -> Dict[str, Any]:
    """
    Compute TEL-5 distribution statistics across a collection of entries.
    
    Args:
        entries: List of entry dictionaries with 'tier' field
    
    Returns:
        Dictionary with tier distribution statistics and TEL-5 metrics
    """
    if not entries:
        return {"error": "No entries provided"}
    
    # Count tier distribution
    tier_counts = {}
    total_entries = len(entries)
    
    for entry in entries:
        tier = entry.get("tier", "Unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    
    # Calculate percentages
    tier_percentages = {
        tier: (count / total_entries) * 100 
        for tier, count in tier_counts.items()
    }
    
    # Aggregate by label (PASS/AMBER/FAIL)
    label_counts = {"PASS": 0, "AMBER": 0, "FAIL": 0}
    tel5_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # TEL-5 level distribution
    
    for entry in entries:
        tier = entry.get("tier", "Black")
        tier_info = get_tel5_tier_info(tier)
        label = tier_info.get("label", "FAIL")
        tel5_level = tier_info.get("tel5_level", 5)
        
        label_counts[label] += 1
        tel5_distribution[tel5_level] += 1
    
    label_percentages = {
        label: (count / total_entries) * 100
        for label, count in label_counts.items()
    }
    
    tel5_percentages = {
        level: (count / total_entries) * 100
        for level, count in tel5_distribution.items()
    }
    
    return {
        "total_entries": total_entries,
        "tier_counts": tier_counts,
        "tier_percentages": tier_percentages,
        "label_counts": label_counts,
        "label_percentages": label_percentages,
        "tel5_distribution": tel5_distribution,
        "tel5_percentages": tel5_percentages,
        "pass_rate": label_percentages["PASS"],
        "amber_rate": label_percentages["AMBER"],
        "fail_rate": label_percentages["FAIL"],
        "quality_index": (label_percentages["PASS"] * 2 + label_percentages["AMBER"]) / 3  # Weighted quality metric
    }


def validate_tel5_assignment(P: float, tier: str, label: str, 
                            phi_violation: bool = False, k_violation: bool = False) -> bool:
    """
    Validate that a TEL-5 tier assignment is consistent with probability and gate results.
    
    Args:
        P: Probability value
        tier: Assigned tier
        label: Assigned label
        phi_violation: Whether Φ gate failed
        k_violation: Whether K gate failed
    
    Returns:
        True if assignment is valid, False otherwise
    """
    # Safety violations should result in Black/FAIL
    if phi_violation or k_violation:
        return tier == "Black" and label == "FAIL"
    
    tier_info = get_tel5_tier_info(tier)
    if not tier_info:
        return False
    
    # Check probability threshold
    if P < tier_info["min_probability"]:
        return False
    
    # Check next tier threshold (upper bound)
    all_tiers = ["Gold", "Silver", "Bronze", "Red", "Black"]
    try:
        tier_idx = all_tiers.index(tier)
        if tier_idx > 0:  # Not Gold
            next_tier = all_tiers[tier_idx - 1]
            next_tier_info = get_tel5_tier_info(next_tier)
            if P >= next_tier_info["min_probability"]:
                return False  # Should be in higher tier
    except ValueError:
        return False
    
    # Check label consistency
    if label != tier_info["label"]:
        return False
    
    return True


def recommend_tel5_adjustment(P: float, current_tier: str, 
                             phi_violation: bool = False,
                             k_violation: bool = False, 
                             l_violation: bool = False) -> Tuple[str, str, str]:
    """
    Recommend TEL-5 tier adjustment based on probability and gate violations.
    
    Args:
        P: Probability that effect > δ
        current_tier: Current TEL-5 tier
        phi_violation: Φ gate violation (natural/category)
        k_violation: K gate violation (safety)
        l_violation: L gate violation (language exaggeration)
    
    Returns:
        Tuple of (recommended_tier, recommended_label, reason)
    """
    # Safety violations override everything (monotone masking/capping)
    if phi_violation or k_violation:
        violation_type = "Φ (natural/category)" if phi_violation else "K (safety)"
        return "Black", "FAIL", f"{violation_type} gate violation - cannot be offset by high J"
    
    # Determine tier from P(effect > δ) 
    label, tier = tel5_classify(P, phi_violation, k_violation)
    
    # Apply L-gate penalty if needed
    if l_violation:
        adjusted_label, adjusted_tier = apply_l_gate_penalty(label, tier, True)
        return adjusted_tier, adjusted_label, "L gate corrective down-shift (exaggerated language)"
    
    # Check if current assignment matches recommendation
    if current_tier == tier:
        return current_tier, label, "Assignment correct"
    else:
        return tier, label, f"Probability P={P:.3f} suggests {tier} tier"


def generate_tel5_llm_hint(tier: str, label: str, P: float, delta: float, 
                          gate_results: Dict[str, Any], method: str = "REML+MC") -> str:
    """
    Generate structured hint for LLM consumption and citation.
    
    Args:
        tier: TEL-5 tier name
        label: Final label (PASS/AMBER/FAIL)
        P: Probability that effect > δ
        delta: Delta threshold used
        gate_results: Dictionary with gate results (phi, r, j, k, l)
        method: Method used (default: "REML+MC")
    
    Returns:
        Compact string with key information for LLM citation
    """
    # Check for safety violations
    phi_status = gate_results.get("phi", "PASS")
    k_status = gate_results.get("k", "PASS")
    
    if phi_status == "FAIL" or k_status == "FAIL":
        violation_gates = []
        if phi_status == "FAIL":
            violation_gates.append("Φ")
        if k_status == "FAIL":
            violation_gates.append("K")
        violations_text = "/".join(violation_gates) + " violations"
    else:
        violations_text = "Φ/K no violations"
    
    # Format category info (extract from context if available)
    category_info = f"δ={delta}"
    
    return f"TEL-5={tier}, {label}; {violations_text}; {category_info}; {method}"


def get_tel5_badge_svg(tier: str, label: str) -> str:
    """
    Generate SVG badge for TEL-5 tier display.
    
    Args:
        tier: TEL-5 tier name
        label: Final label
    
    Returns:
        SVG string for badge display
    """
    tier_info = get_tel5_tier_info(tier)
    color = tier_info.get("color", "#000000")
    icon = tier_info.get("icon", "⚫")
    
    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="120" height="24" viewBox="0 0 120 24">
        <rect width="120" height="24" fill="{color}" rx="4"/>
        <text x="12" y="16" fill="white" font-family="Arial, sans-serif" font-size="12" font-weight="bold">
            {icon} TEL-5: {tier}
        </text>
        <text x="118" y="16" fill="white" font-family="Arial, sans-serif" font-size="10" text-anchor="end">
            {label}
        </text>
    </svg>
    """.strip()


# Maintain backward compatibility with old HBV function names
def hbv_label(*args, **kwargs):
    """Backward compatibility wrapper for tel5_classify."""
    logger.warning("hbv_label() is deprecated, use tel5_classify() instead")
    return tel5_classify(*args, **kwargs)


def get_tier_description(tier: str) -> Dict[str, Any]:
    """Backward compatibility wrapper for get_tel5_tier_info.""" 
    logger.warning("get_tier_description() is deprecated, use get_tel5_tier_info() instead")
    return get_tel5_tier_info(tier)