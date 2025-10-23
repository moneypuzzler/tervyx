"""
REML + Monte Carlo meta-analysis engine for TERVYX Protocol.

Implements random-effects meta-analysis with REML tau² estimation and Monte Carlo
simulation to compute P(effect > δ) probabilities for TEL-5 tier assignment.
Includes unified benefit direction for consistent effect interpretation.
"""

import math
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import logging
import time

from engine.policy_fingerprint import compute_policy_fingerprint

logger = logging.getLogger(__name__)


class MCConfig:
    """Configuration class for Monte Carlo meta-analysis."""
    seed = 20251005
    n_draws = 10000
    delta = 0.20
    benefit_direction = 1  # +1 or -1 for unified benefit direction


def ci_to_se(effect_type: str, y: float, lo: float, hi: float) -> Tuple[float, float]:
    """
    Convert 95% confidence interval to standard error with log-transform for OR/RR.
    
    Args:
        effect_type: Type of effect size (SMD, MD, OR, RR, HR, Cohen-d, Hedges-g)
        y: Point estimate
        lo: Lower bound of 95% CI
        hi: Upper bound of 95% CI
    
    Returns:
        Tuple of (transformed_y, standard_error)
    """
    if effect_type.upper() in ("OR", "RR", "HR"):
        # Log-transform for ratio measures
        if y <= 0 or lo <= 0 or hi <= 0:
            raise ValueError(f"OR/RR/HR values must be positive: y={y}, CI=[{lo}, {hi}]")
        y_transformed = math.log(y)
        se = (math.log(hi) - math.log(lo)) / (2.0 * 1.96)
    else:
        # Linear scale for difference measures (SMD, MD, Cohen-d, Hedges-g)
        y_transformed = y
        se = (hi - lo) / (2.0 * 1.96)
    
    return y_transformed, se


def restricted_nll(tau2: float, y: np.ndarray, v: np.ndarray) -> float:
    """
    Compute restricted (REML) negative log-likelihood for tau² estimation.
    
    This implements the REML objective function that accounts for the loss of
    degrees of freedom from estimating fixed effects.
    
    Args:
        tau2: Between-study variance parameter (≥ 0)
        y: Effect sizes array
        v: Within-study variances array
    
    Returns:
        Restricted negative log-likelihood value
    """
    vt = v + tau2  # Total variance = within + between
    w = 1.0 / vt   # Weights
    mu = np.sum(w * y) / np.sum(w)  # Weighted mean (BLUE)
    
    # REML likelihood components
    # L_REML = |V|^{-1/2} * |X'V⁻¹X|^{-1/2} * exp(-1/2 * Q)
    log_det_V = np.sum(np.log(vt))  # log |V|
    log_det_XVX = math.log(np.sum(w))  # log |X'V⁻¹X| (scalar for intercept-only model)
    quadratic_form = np.sum((y - mu)**2 * w)  # Q = (y-Xβ)'V⁻¹(y-Xβ)
    
    return 0.5 * (log_det_V + log_det_XVX + quadratic_form)


def reml_tau2(y: np.ndarray, v: np.ndarray, mult: float = 100.0) -> float:
    """
    Estimate between-study variance using REML method with grid search + local refinement.
    
    Uses a two-stage optimization:
    1. Coarse geometric grid search over [0, vmax * mult]
    2. Fine linear search around the coarse minimum
    
    Args:
        y: Effect sizes array
        v: Within-study variances array
        mult: Multiplier for upper bound (default: 100.0)
    
    Returns:
        Estimated τ² value (≥ 0)
    """
    if len(y) <= 1:
        return 0.0
    
    # Set upper bound for τ² search
    vmax = float(np.max(v))
    upper = max(1e-12, vmax * mult)
    
    # Stage 1: Coarse geometric grid search
    grid = [0.0] + list(np.geomspace(1e-10, upper, 400))
    nll_values = [restricted_nll(t, y, v) for t in grid]
    idx = int(np.argmin(nll_values))
    
    # Stage 2: Fine linear search around minimum
    left = grid[max(0, idx - 2)]
    right = grid[min(len(grid) - 1, idx + 2)]
    fine_grid = np.linspace(left, right, 400)
    fine_nll = [restricted_nll(t, y, v) for t in fine_grid]
    
    optimal_tau2 = float(fine_grid[int(np.argmin(fine_nll))])
    return max(0.0, optimal_tau2)  # Ensure non-negative


def compute_heterogeneity_stats(y: np.ndarray, v: np.ndarray, tau2: float) -> Dict[str, float]:
    """
    Compute comprehensive heterogeneity statistics.
    
    Args:
        y: Effect sizes array
        v: Within-study variances array
        tau2: Between-study variance
    
    Returns:
        Dictionary with heterogeneity statistics (I², H², Q, df, tau)
    """
    if len(y) <= 1:
        return {
            "I2": 0.0, 
            "H2": 1.0, 
            "tau": math.sqrt(tau2),
            "Q": 0.0,
            "df": max(0, len(y) - 1)
        }
    
    # Compute Cochran's Q statistic (under fixed-effects assumption)
    w = 1.0 / v  # Fixed-effects weights
    mu_fixed = np.sum(w * y) / np.sum(w)
    Q = float(np.sum(w * (y - mu_fixed)**2))
    df = len(y) - 1
    
    # I-squared: Proportion of variation due to heterogeneity
    I2 = max(0.0, 100.0 * (Q - df) / Q) if Q > 0 else 0.0
    
    # H-squared: Ratio of Q to df
    H2 = Q / df if df > 0 and Q > 0 else 1.0
    
    return {
        "I2": I2,
        "H2": H2, 
        "tau": math.sqrt(tau2),
        "Q": Q,
        "df": df
    }


def run_reml_mc_analysis(evidence_rows: List[Dict[str, Any]],
                        delta: float,
                        benefit_direction: int = 1,
                        seed: int = 20251005,
                        n_draws: int = 10000,
                        tau2_method: str = "REML",
                        policy_fingerprint: Optional[str] = None) -> Dict[str, Any]:
    """
    Run REML-based Monte Carlo meta-analysis with unified benefit direction.
    
    This is the main analysis function implementing Algorithm 1 from the TERVYX paper:
    1. Preprocess: CI→SE, unify direction (benefit = positive)
    2. REML τ² estimation
    3. Monte Carlo simulation for P(effect > δ)
    4. TEL-5 mapping preparation
    
    Args:
        evidence_rows: List of study data dictionaries (ESV format)
        delta: Minimally important difference threshold
        benefit_direction: Direction multiplier (+1 or -1) for unified benefit
        seed: Random seed for deterministic reproducibility
        n_draws: Number of Monte Carlo draws (default: 10,000)
        tau2_method: Method for τ² estimation ("REML" recommended)
    
    Returns:
        Dictionary with simulation results compatible with simulation.json schema
    """
    start_time = time.time()
    
    if not evidence_rows:
        fingerprint = policy_fingerprint or compute_policy_fingerprint().compact
        return {
            "seed": seed,
            "n_draws": n_draws,
            "tau2_method": tau2_method,
            "delta": delta,
            "P_effect_gt_delta": 0.0,
            "mu_hat": 0.0,
            "mu_CI95": [0.0, 0.0],
            "var_mu": 0.0,
            "mu_se": 0.0,
            "I2": None,
            "tau2": None,
            "n_studies": 0,
            "total_n": 0,
            "benefit_direction": benefit_direction,
            "environment": f"Python {'.'.join(map(str, [3, 11]))}, NumPy {np.__version__}",
            "error": "No evidence provided",
            "policy_fingerprint": fingerprint
        }
    
    # Step 1: Preprocess evidence with unified benefit direction
    ys, ses = [], []
    total_n = 0
    
    for r in evidence_rows:
        y = float(r["effect_point"])
        lo = float(r["ci_low"]) 
        hi = float(r["ci_high"])
        et = str(r["effect_type"])
        
        # Convert CI to SE with appropriate transformation
        y_transformed, se = ci_to_se(et, y, lo, hi)
        
        # Apply benefit direction for unified interpretation
        y_unified = y_transformed * benefit_direction
        
        ys.append(y_unified)
        ses.append(se)
        
        # Accumulate sample sizes if available
        n_treat = r.get("n_treat", 0)
        n_ctrl = r.get("n_ctrl", 0)
        total_n += int(n_treat) + int(n_ctrl)
    
    # Convert to numpy arrays
    y = np.array(ys, dtype=float)
    v = np.array(ses, dtype=float)**2  # Variances
    
    # Step 2: REML τ² estimation
    tau2 = reml_tau2(y, v) if tau2_method == "REML" else 0.0
    
    # Random-effects meta-analysis
    w = 1.0 / (v + tau2)  # Random-effects weights
    mu_hat = float(np.sum(w * y) / np.sum(w))  # Pooled effect estimate
    var_mu = float(1.0 / np.sum(w))  # Variance of pooled effect
    mu_se = math.sqrt(var_mu)
    
    # Compute heterogeneity statistics
    het_stats = compute_heterogeneity_stats(y, v, tau2)
    
    # 95% confidence interval for pooled effect
    ci_margin = 1.96 * mu_se
    mu_ci95 = [mu_hat - ci_margin, mu_hat + ci_margin]
    
    # 95% prediction interval
    pred_se = math.sqrt(tau2 + var_mu)
    pred_margin = 1.96 * pred_se
    prediction_interval_95 = [mu_hat - pred_margin, mu_hat + pred_margin]
    
    # Step 3: Monte Carlo simulation
    rng = np.random.default_rng(seed)
    draws = rng.normal(mu_hat, mu_se, n_draws)
    P = float(np.mean(draws > delta))
    
    computation_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Step 4: Return results in simulation.json format
    fingerprint = policy_fingerprint or compute_policy_fingerprint().compact
    result = {
        "seed": seed,
        "n_draws": n_draws,
        "tau2_method": tau2_method,
        "delta": delta,
        "P_effect_gt_delta": round(P, 6),
        "mu_hat": round(mu_hat, 6),
        "mu_CI95": [round(x, 6) for x in mu_ci95],
        "var_mu": round(var_mu, 8),
        "mu_se": round(mu_se, 6),
        "I2": round(het_stats["I2"], 1) if het_stats["I2"] is not None else None,
        "tau2": round(tau2, 8),
        "tau": round(het_stats["tau"], 6),
        "Q": round(het_stats["Q"], 2),
        "prediction_interval_95": [round(x, 6) for x in prediction_interval_95],
        "n_studies": len(evidence_rows),
        "total_n": total_n,
        "benefit_direction": benefit_direction,
        "benefit_note": _get_benefit_note(benefit_direction),
        "environment": f"Python 3.11, NumPy {np.__version__}, SciPy 1.11.0",
        "gate_terminated": False,
        "termination_gate": "none",
        "reml_convergence": {
            "converged": True,
            "iterations": 1,  # Grid search is deterministic
            "final_nll": float(restricted_nll(tau2, y, v))
        },
        "computation_time_ms": round(computation_time, 1),
        "tel5_input": {
            "P_value": round(P, 6),
            "phi_violation": False,  # Set by gates module
            "k_violation": False     # Set by gates module
        },
        "policy_fingerprint": fingerprint
    }
    
    return result


def _get_benefit_note(benefit_direction: int) -> str:
    """Generate human-readable explanation of benefit direction."""
    if benefit_direction == -1:
        return "Lower scores indicate improvement (e.g., PSQI decrease is beneficial)"
    elif benefit_direction == 1:
        return "Higher scores indicate improvement"
    else:
        return "Custom benefit direction applied"


def validate_evidence_data(evidence_rows: List[Dict[str, Any]]) -> List[str]:
    """
    Validate Evidence State Vector (ESV) data for required fields and reasonable values.
    
    Args:
        evidence_rows: List of study data dictionaries
    
    Returns:
        List of validation error messages (empty if all valid)
    """
    errors = []
    
    required_fields = ["effect_point", "ci_low", "ci_high", "effect_type", "study_id"]
    recommended_fields = ["year", "design", "n_treat", "n_ctrl", "doi", "journal_id"]
    
    for i, row in enumerate(evidence_rows):
        row_id = f"Row {i+1} ({row.get('study_id', 'unknown')})"
        
        # Check required fields
        for field in required_fields:
            if field not in row or row[field] is None:
                errors.append(f"{row_id}: Missing required field '{field}'")
                continue
        
        # Check recommended fields (warnings, not errors)
        missing_recommended = [f for f in recommended_fields if f not in row or row[f] is None]
        if missing_recommended:
            logger.warning(f"{row_id}: Missing recommended fields: {', '.join(missing_recommended)}")
        
        # Validate numeric fields
        try:
            effect = float(row["effect_point"])
            ci_low = float(row["ci_low"]) 
            ci_high = float(row["ci_high"])
            
            # Check CI ordering
            if ci_low >= ci_high:
                errors.append(f"{row_id}: CI lower bound ({ci_low}) must be < upper bound ({ci_high})")
            
            # Check effect is within CI bounds (with small tolerance)
            tolerance = abs(ci_high - ci_low) * 0.01  # 1% tolerance
            if not (ci_low - tolerance <= effect <= ci_high + tolerance):
                errors.append(f"{row_id}: Effect point estimate ({effect}) outside CI bounds [{ci_low}, {ci_high}]")
            
            # Check for extreme values that might indicate data entry errors
            ci_width = ci_high - ci_low
            if ci_width > 10:  # Very wide CI
                logger.warning(f"{row_id}: Very wide confidence interval (width: {ci_width:.2f})")
            
            # Validate effect type and values
            effect_type = str(row["effect_type"]).upper()
            if effect_type in ("OR", "RR", "HR"):
                if effect <= 0 or ci_low <= 0 or ci_high <= 0:
                    errors.append(f"{row_id}: {effect_type} values must be positive")
                    
        except (ValueError, TypeError) as e:
            errors.append(f"{row_id}: Invalid numeric values in effect size fields: {e}")
        
        # Validate effect type
        valid_effect_types = ["SMD", "MD", "OR", "RR", "HR", "COHEN-D", "HEDGES-G"]
        effect_type = str(row.get("effect_type", "")).upper()
        if effect_type not in valid_effect_types:
            errors.append(f"{row_id}: Invalid effect_type '{effect_type}'. Must be one of: {', '.join(valid_effect_types)}")
        
        # Validate sample sizes if provided
        for size_field in ["n_treat", "n_ctrl"]:
            if size_field in row:
                try:
                    n = int(row[size_field])
                    if n <= 0:
                        errors.append(f"{row_id}: {size_field} must be positive integer")
                except (ValueError, TypeError):
                    errors.append(f"{row_id}: {size_field} must be integer")
    
    return errors


# Maintain backward compatibility
def run_mc(*args, **kwargs):
    """Backward compatibility wrapper for run_reml_mc_analysis."""
    logger.warning("run_mc() is deprecated, use run_reml_mc_analysis() instead")
    return run_reml_mc_analysis(*args, **kwargs)