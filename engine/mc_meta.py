"""
Monte Carlo meta-analysis engine for VERA Protocol.

Implements REML-based random effects meta-analysis with Monte Carlo simulation
to compute P(effect > δ) probabilities for HBV tier assignment.
"""

import math
import numpy as np
from typing import List, Dict, Any, Tuple


def _ci_to_se(effect_type: str, y: float, lo: float, hi: float) -> Tuple[float, float]:
    """
    Convert confidence interval to standard error.
    
    Args:
        effect_type: Type of effect size (SMD, MD, OR, RR)
        y: Point estimate
        lo: Lower bound of 95% CI
        hi: Upper bound of 95% CI
    
    Returns:
        Tuple of (transformed_y, standard_error)
    """
    if effect_type.upper() in ("OR", "RR"):
        # Log-transform for odds ratios and risk ratios
        y_transformed = math.log(y)
        se = (math.log(hi) - math.log(lo)) / (2.0 * 1.96)
    else:
        # Linear scale for SMD, MD
        y_transformed = y
        se = (hi - lo) / (2.0 * 1.96)
    
    return y_transformed, se


def _restricted_nll(tau2: float, y: np.ndarray, v: np.ndarray) -> float:
    """
    Compute restricted negative log-likelihood for REML tau-squared estimation.
    
    Args:
        tau2: Between-study variance parameter
        y: Effect sizes
        v: Within-study variances
    
    Returns:
        Restricted negative log-likelihood value
    """
    vt = v + tau2  # Total variance
    w = 1.0 / vt   # Weights
    mu = np.sum(w * y) / np.sum(w)  # Weighted mean
    
    # REML likelihood components
    log_det_V = np.sum(np.log(vt))
    log_det_XVX = np.log(np.sum(w))
    quadratic_form = np.sum((y - mu)**2 * w)
    
    return 0.5 * (log_det_V + log_det_XVX + quadratic_form)


def _reml_tau2(y: np.ndarray, v: np.ndarray) -> float:
    """
    Estimate between-study variance using REML method.
    
    Args:
        y: Effect sizes
        v: Within-study variances
    
    Returns:
        Estimated tau-squared value
    """
    if len(y) <= 1:
        return 0.0
    
    # Set upper bound for tau2 search
    vmax = float(np.max(v))
    upper = max(1e-12, vmax * 100.0)
    
    # Coarse grid search
    grid = [0.0] + list(np.geomspace(1e-10, upper, 400))
    nll_values = [_restricted_nll(t, y, v) for t in grid]
    idx = int(np.argmin(nll_values))
    
    # Fine search around minimum
    left = grid[max(0, idx - 2)]
    right = grid[min(len(grid) - 1, idx + 2)]
    fine_grid = np.linspace(left, right, 400)
    fine_nll = [_restricted_nll(t, y, v) for t in fine_grid]
    
    optimal_tau2 = float(fine_grid[int(np.argmin(fine_nll))])
    return max(0.0, optimal_tau2)


def compute_heterogeneity_stats(y: np.ndarray, v: np.ndarray, tau2: float) -> Dict[str, float]:
    """
    Compute heterogeneity statistics (I² and H²).
    
    Args:
        y: Effect sizes
        v: Within-study variances  
        tau2: Between-study variance
    
    Returns:
        Dictionary with heterogeneity statistics
    """
    if len(y) <= 1:
        return {"I2": 0.0, "H2": 1.0, "tau": math.sqrt(tau2)}
    
    # Compute Q statistic
    w = 1.0 / v
    mu_fixed = np.sum(w * y) / np.sum(w)
    Q = float(np.sum(w * (y - mu_fixed)**2))
    df = len(y) - 1
    
    # I-squared
    I2 = max(0.0, 100.0 * (Q - df) / Q) if Q > 0 else 0.0
    
    # H-squared
    H2 = Q / df if df > 0 and Q > 0 else 1.0
    
    return {
        "I2": I2,
        "H2": H2, 
        "tau": math.sqrt(tau2),
        "Q": Q,
        "df": df
    }


def run_mc(evidence_rows: List[Dict[str, Any]], 
          delta: float, 
          seed: int = 20251005, 
          n_draws: int = 10000, 
          tau2_method: str = "REML") -> Dict[str, Any]:
    """
    Run Monte Carlo meta-analysis simulation.
    
    Args:
        evidence_rows: List of study data dictionaries
        delta: Minimally important difference (δ)
        seed: Random seed for reproducibility
        n_draws: Number of Monte Carlo draws
        tau2_method: Method for tau-squared estimation
    
    Returns:
        Dictionary with simulation results and statistics
    """
    if not evidence_rows:
        return {
            "seed": seed,
            "n_draws": n_draws,
            "tau2_method": tau2_method,
            "delta": delta,
            "P_effect_gt_delta": 0.0,
            "mu_CI95": [0.0, 0.0],
            "I2": None,
            "tau2": None,
            "environment": "Python/NumPy (empty dataset)",
            "error": "No evidence provided"
        }
    
    # Extract and transform effect sizes
    ys, ses = [], []
    for r in evidence_rows:
        y = float(r["effect_point"])
        lo = float(r["ci_low"]) 
        hi = float(r["ci_high"])
        et = str(r["effect_type"])
        
        y_transformed, se = _ci_to_se(et, y, lo, hi)
        ys.append(y_transformed)
        ses.append(se)
    
    # Convert to numpy arrays
    y = np.array(ys)
    v = np.array(ses)**2  # Variances
    
    # Estimate tau-squared using REML
    tau2 = _reml_tau2(y, v) if tau2_method == "REML" else 0.0
    
    # Random effects meta-analysis
    w = 1.0 / (v + tau2)  # Random effects weights
    mu = float(np.sum(w * y) / np.sum(w))  # Pooled effect
    var_mu = float(1.0 / np.sum(w))  # Variance of pooled effect
    
    # Compute heterogeneity statistics
    het_stats = compute_heterogeneity_stats(y, v, tau2)
    
    # Monte Carlo simulation
    rng = np.random.default_rng(seed)
    draws = rng.normal(mu, math.sqrt(var_mu), n_draws)
    P = float(np.mean(draws > delta))
    
    # Confidence interval for pooled effect
    ci_margin = 1.96 * math.sqrt(var_mu)
    mu_ci95 = [mu - ci_margin, mu + ci_margin]
    
    return {
        "seed": seed,
        "n_draws": n_draws,
        "tau2_method": tau2_method,
        "delta": delta,
        "P_effect_gt_delta": P,
        "mu_point": mu,
        "mu_CI95": mu_ci95,
        "mu_se": math.sqrt(var_mu),
        "I2": het_stats["I2"],
        "tau2": tau2,
        "tau": het_stats["tau"],
        "Q": het_stats["Q"],
        "n_studies": len(evidence_rows),
        "environment": "Python/NumPy"
    }


def validate_evidence_data(evidence_rows: List[Dict[str, Any]]) -> List[str]:
    """
    Validate evidence data for required fields and reasonable values.
    
    Args:
        evidence_rows: List of study data dictionaries
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    required_fields = ["effect_point", "ci_low", "ci_high", "effect_type"]
    
    for i, row in enumerate(evidence_rows):
        # Check required fields
        for field in required_fields:
            if field not in row:
                errors.append(f"Row {i+1}: Missing required field '{field}'")
                continue
        
        # Check numeric values
        try:
            effect = float(row["effect_point"])
            ci_low = float(row["ci_low"]) 
            ci_high = float(row["ci_high"])
            
            # Check CI ordering
            if ci_low >= ci_high:
                errors.append(f"Row {i+1}: CI lower bound must be < upper bound")
            
            # Check effect is within CI bounds
            if not (ci_low <= effect <= ci_high):
                errors.append(f"Row {i+1}: Effect point estimate outside CI bounds")
                
        except (ValueError, TypeError):
            errors.append(f"Row {i+1}: Non-numeric values in effect size fields")
    
    return errors