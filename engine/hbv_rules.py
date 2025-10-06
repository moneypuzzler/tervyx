"""
HBV 5-tier labeling system for VERA Protocol.

Implements the Health Benefit Verification system that maps
P(effect > δ) probabilities to tier labels (Gold/Silver/Bronze/Red/Black).
"""

from typing import Tuple, Dict, Any


def hbv_label(P: float, phi_fail: bool = False, k_fail: bool = False) -> Tuple[str, str]:
    """
    Determine HBV tier and label based on effect probability and gate violations.
    
    Args:
        P: Probability that effect > δ (minimally important difference)
        phi_fail: Whether Φ (natural/category) gate failed
        k_fail: Whether K (safety) gate failed
    
    Returns:
        Tuple of (label, tier) where:
        - label: PASS, AMBER, or FAIL
        - tier: Gold, Silver, Bronze, Red, or Black
    """
    # Safety-first monotonicity: Φ/K violations cannot be offset
    if phi_fail or k_fail:
        return "FAIL", "Black"
    
    # Standard HBV tier assignment based on probability
    if P >= 0.80:
        return "PASS", "Gold"
    elif P >= 0.60:
        return "PASS", "Silver"  
    elif P >= 0.40:
        return "AMBER", "Bronze"
    elif P >= 0.20:
        return "AMBER", "Red"
    else:
        return "FAIL", "Black"


def apply_l_gate_penalty(label: str, tier: str, l_flag: bool) -> Tuple[str, str]:
    """
    Apply L-gate (language exaggeration) penalty to labels.
    
    The L-gate implements a soft penalty system where exaggerated language
    causes a downward shift in tier assignment but not automatic failure.
    
    Args:
        label: Current label (PASS, AMBER, FAIL)
        tier: Current tier (Gold, Silver, Bronze, Red, Black)
        l_flag: Whether exaggerated language was detected
    
    Returns:
        Tuple of (adjusted_label, adjusted_tier)
    """
    if not l_flag or label == "FAIL":
        return label, tier
    
    # Soft penalty: demote by one level
    if label == "PASS":
        # PASS becomes AMBER, but maintain tier structure
        if tier == "Gold":
            return "AMBER", "Bronze"
        elif tier == "Silver":
            return "AMBER", "Bronze"
    
    # Already AMBER - demote tier within AMBER category
    elif label == "AMBER":
        if tier == "Bronze":
            return "AMBER", "Red"
        # Red is already lowest AMBER tier
    
    return label, tier


def get_tier_description(tier: str) -> Dict[str, Any]:
    """
    Get detailed description and properties of an HBV tier.
    
    Args:
        tier: Tier name (Gold, Silver, Bronze, Red, Black)
    
    Returns:
        Dictionary with tier properties and description
    """
    tier_info = {
        "Gold": {
            "min_probability": 0.80,
            "label": "PASS",
            "color": "#FFD700",
            "confidence": "High",
            "description": "Strong evidence of beneficial effect (P ≥ 0.80)",
            "recommendation": "Evidence strongly supports the claimed benefit"
        },
        "Silver": {
            "min_probability": 0.60,
            "label": "PASS", 
            "color": "#C0C0C0",
            "confidence": "Moderate-High",
            "description": "Good evidence of beneficial effect (P ≥ 0.60)",
            "recommendation": "Evidence supports the claimed benefit"
        },
        "Bronze": {
            "min_probability": 0.40,
            "label": "AMBER",
            "color": "#CD7F32", 
            "confidence": "Moderate",
            "description": "Limited evidence of beneficial effect (P ≥ 0.40)",
            "recommendation": "Evidence provides limited support; further research needed"
        },
        "Red": {
            "min_probability": 0.20,
            "label": "AMBER",
            "color": "#DC3545",
            "confidence": "Low",
            "description": "Weak evidence of beneficial effect (P ≥ 0.20)",
            "recommendation": "Evidence is insufficient; caution advised"
        },
        "Black": {
            "min_probability": 0.00,
            "label": "FAIL",
            "color": "#000000",
            "confidence": "None",
            "description": "No credible evidence or safety concerns (P < 0.20 or gate violations)",
            "recommendation": "Claim not supported by evidence or poses safety concerns"
        }
    }
    
    return tier_info.get(tier, {})


def compute_tier_statistics(entries: list) -> Dict[str, Any]:
    """
    Compute distribution statistics across a collection of entries.
    
    Args:
        entries: List of entry dictionaries with 'tier' field
    
    Returns:
        Dictionary with tier distribution statistics
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
    
    # Aggregate by label
    label_counts = {"PASS": 0, "AMBER": 0, "FAIL": 0}
    for entry in entries:
        tier = entry.get("tier", "Black")
        tier_info = get_tier_description(tier)
        label = tier_info.get("label", "FAIL")
        label_counts[label] += 1
    
    label_percentages = {
        label: (count / total_entries) * 100
        for label, count in label_counts.items()
    }
    
    return {
        "total_entries": total_entries,
        "tier_counts": tier_counts,
        "tier_percentages": tier_percentages,
        "label_counts": label_counts,
        "label_percentages": label_percentages,
        "pass_rate": label_percentages["PASS"],
        "amber_rate": label_percentages["AMBER"],
        "fail_rate": label_percentages["FAIL"]
    }


def validate_hbv_assignment(P: float, tier: str, label: str) -> bool:
    """
    Validate that an HBV tier assignment is consistent with probability.
    
    Args:
        P: Probability value
        tier: Assigned tier
        label: Assigned label
    
    Returns:
        True if assignment is valid, False otherwise
    """
    tier_info = get_tier_description(tier)
    if not tier_info:
        return False
    
    # Check probability threshold
    if P < tier_info["min_probability"]:
        return False
    
    # Check label consistency
    if label != tier_info["label"]:
        return False
    
    return True


def recommend_tier_adjustment(current_tier: str, 
                            phi_violation: bool = False,
                            k_violation: bool = False, 
                            l_violation: bool = False) -> Tuple[str, str, str]:
    """
    Recommend tier adjustment based on gate violations.
    
    Args:
        current_tier: Current HBV tier
        phi_violation: Φ gate violation (natural/category)
        k_violation: K gate violation (safety)
        l_violation: L gate violation (language exaggeration)
    
    Returns:
        Tuple of (recommended_tier, recommended_label, reason)
    """
    # Safety violations override everything
    if phi_violation or k_violation:
        violation_type = "Φ (natural/category)" if phi_violation else "K (safety)"
        return "Black", "FAIL", f"{violation_type} gate violation"
    
    # Get current tier info
    tier_info = get_tier_description(current_tier)
    if not tier_info:
        return "Black", "FAIL", "Invalid tier"
    
    current_label = tier_info["label"]
    
    # Apply L-gate penalty if needed
    if l_violation:
        adjusted_label, adjusted_tier = apply_l_gate_penalty(current_label, current_tier, True)
        return adjusted_tier, adjusted_label, "L gate penalty (exaggerated language)"
    
    # No adjustment needed
    return current_tier, current_label, "No violations detected"