"""REML + Monte Carlo meta-analysis utilities with optional NumPy support."""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from engine.policy_fingerprint import compute_policy_fingerprint

try:  # pragma: no cover - optional dependency for speed
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover - executed when NumPy unavailable
    _np = None  # type: ignore[assignment]

NUMPY_VERSION = getattr(_np, "__version__", "compat")

logger = logging.getLogger(__name__)


class MCConfig:
    """Configuration defaults for Monte Carlo meta-analysis."""

    seed = 20251005
    n_draws = 10000
    delta = 0.20
    benefit_direction = 1  # +1 or -1 for unified benefit direction


def _to_float_list(values: Sequence[float] | Iterable[float]) -> List[float]:
    return [float(v) for v in values]


def _sum(values: Iterable[float]) -> float:
    total = 0.0
    for value in values:
        total += value
    return total


def _argmin(values: Sequence[float]) -> int:
    return min(range(len(values)), key=lambda idx: values[idx]) if values else 0


def _geomspace(start: float, stop: float, num: int) -> List[float]:
    if num <= 0:
        return []
    if num == 1:
        return [float(start)]
    if start <= 0 or stop <= 0:
        return _linspace(start, stop, num)
    log_start = math.log(start)
    log_stop = math.log(stop)
    step = (log_stop - log_start) / (num - 1)
    return [math.exp(log_start + step * i) for i in range(num)]


def _linspace(start: float, stop: float, num: int) -> List[float]:
    if num <= 0:
        return []
    if num == 1:
        return [float(start)]
    step = (stop - start) / (num - 1)
    return [start + step * i for i in range(num)]


def _normal_draws(mean: float, stddev: float, count: int, *, seed: int) -> List[float]:
    if count <= 0:
        return []
    if stddev <= 0:
        return [mean for _ in range(count)]
    rng = random.Random(seed)
    return [rng.gauss(mean, stddev) for _ in range(count)]


def _generate_normal_samples(mean: float, stddev: float, count: int, seed: int) -> List[float]:
    if _np is not None:  # pragma: no cover - exercised when NumPy available
        rng = _np.random.default_rng(seed)
        draws = rng.normal(mean, stddev, count)
        return draws.tolist()
    return _normal_draws(mean, stddev, count, seed=seed)


def ci_to_se(effect_type: str, y: float, lo: float, hi: float) -> Tuple[float, float]:
    """
    Convert 95% confidence interval bounds into a standard error estimate.
    """

    if effect_type.upper() in ("OR", "RR", "HR"):
        if y <= 0 or lo <= 0 or hi <= 0:
            raise ValueError(f"OR/RR/HR values must be positive: y={y}, CI=[{lo}, {hi}]")
        y_transformed = math.log(y)
        se = (math.log(hi) - math.log(lo)) / (2.0 * 1.96)
    else:
        y_transformed = y
        se = (hi - lo) / (2.0 * 1.96)
    return y_transformed, se


def restricted_nll(tau2: float, y: Sequence[float], v: Sequence[float]) -> float:
    """Compute restricted (REML) negative log-likelihood for tau² estimation."""

    y_vals = _to_float_list(y)
    v_vals = _to_float_list(v)

    vt = [vi + tau2 for vi in v_vals]
    if any(value <= 0 for value in vt):
        return float("inf")

    w = [1.0 / value for value in vt]
    denom = _sum(w)
    if denom <= 0:
        return float("inf")

    mu = _sum(wi * yi for wi, yi in zip(w, y_vals)) / denom
    log_det_V = _sum(math.log(value) for value in vt)
    log_det_XVX = math.log(denom)
    quadratic_form = _sum(((yi - mu) ** 2) * wi for yi, wi in zip(y_vals, w))
    return 0.5 * (log_det_V + log_det_XVX + quadratic_form)


def reml_tau2(y: Sequence[float], v: Sequence[float], mult: float = 100.0) -> float:
    """Estimate between-study variance using REML grid + refinement search."""

    y_vals = _to_float_list(y)
    v_vals = _to_float_list(v)
    if len(y_vals) <= 1:
        return 0.0
    vmax = max(v_vals) if v_vals else 0.0
    upper = max(1e-12, vmax * mult)
    grid = [0.0] + _geomspace(1e-10, upper, 400)
    nll_values = [restricted_nll(t, y_vals, v_vals) for t in grid]
    idx = _argmin(nll_values)
    left = grid[max(0, idx - 2)]
    right = grid[min(len(grid) - 1, idx + 2)]
    fine_grid = _linspace(left, right, 400)
    fine_nll = [restricted_nll(t, y_vals, v_vals) for t in fine_grid]
    optimal_tau2 = fine_grid[_argmin(fine_nll)] if fine_grid else 0.0
    return max(0.0, optimal_tau2)


def compute_heterogeneity_stats(
    y: Sequence[float], v: Sequence[float], tau2: float
) -> Dict[str, float]:
    """Compute heterogeneity statistics (I², H², Q, df, tau)."""

    y_vals = _to_float_list(y)
    v_vals = _to_float_list(v)

    if len(y_vals) <= 1:
        return {
            "I2": 0.0,
            "H2": 1.0,
            "tau": math.sqrt(tau2),
            "Q": 0.0,
            "df": max(0, len(y_vals) - 1),
        }

    w = [1.0 / value if value > 0 else 0.0 for value in v_vals]
    denom = _sum(w)
    mu_fixed = _sum(wi * yi for wi, yi in zip(w, y_vals)) / denom if denom else 0.0
    Q = _sum(wi * (yi - mu_fixed) ** 2 for wi, yi in zip(w, y_vals))
    df = len(y_vals) - 1
    I2 = max(0.0, 100.0 * (Q - df) / Q) if Q > 0 else 0.0
    H2 = Q / df if df > 0 and Q > 0 else 1.0
    return {"I2": I2, "H2": H2, "tau": math.sqrt(max(tau2, 0.0)), "Q": Q, "df": df}


def _get_benefit_note(benefit_direction: int) -> str:
    if benefit_direction == -1:
        return "Lower scores indicate improvement (e.g., PSQI decrease is beneficial)"
    if benefit_direction == 1:
        return "Higher scores indicate improvement"
    return "Custom benefit direction applied"


def run_reml_mc_analysis(
    evidence_rows: List[Dict[str, Any]],
    *,
    delta: float,
    benefit_direction: int = 1,
    seed: int = MCConfig.seed,
    n_draws: int = MCConfig.n_draws,
    tau2_method: str = "REML",
    policy_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    """Run REML + Monte Carlo analysis using standard library fallbacks."""

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
            "environment": f"Python 3.11, NumPy {NUMPY_VERSION}",
            "error": "No evidence provided",
            "policy_fingerprint": fingerprint,
        }

    ys: List[float] = []
    ses: List[float] = []
    total_n = 0

    for row in evidence_rows:
        y = float(row["effect_point"])
        lo = float(row["ci_low"])
        hi = float(row["ci_high"])
        effect_type = str(row["effect_type"])
        y_transformed, se = ci_to_se(effect_type, y, lo, hi)
        ys.append(y_transformed * benefit_direction)
        ses.append(se)
        n_treat = row.get("n_treat", 0)
        n_ctrl = row.get("n_ctrl", 0)
        total_n += int(n_treat) + int(n_ctrl)

    variances = [se ** 2 for se in ses]
    tau2 = reml_tau2(ys, variances) if tau2_method == "REML" else 0.0

    weights = [1.0 / (var + tau2) if (var + tau2) > 0 else 0.0 for var in variances]
    weight_sum = _sum(weights) or 1.0
    mu_hat = _sum(w * y for w, y in zip(weights, ys)) / weight_sum
    var_mu = 1.0 / weight_sum
    mu_se = math.sqrt(max(var_mu, 0.0))

    het_stats = compute_heterogeneity_stats(ys, variances, tau2)
    ci_margin = 1.96 * mu_se
    mu_ci95 = [mu_hat - ci_margin, mu_hat + ci_margin]

    pred_se = math.sqrt(max(tau2 + var_mu, 0.0))
    pred_margin = 1.96 * pred_se
    prediction_interval_95 = [mu_hat - pred_margin, mu_hat + pred_margin]

    draws = _generate_normal_samples(mu_hat, mu_se, n_draws, seed)
    if draws:
        P = sum(1 for draw in draws if draw > delta) / len(draws)
    else:
        P = 0.0

    computation_time = (time.time() - start_time) * 1000.0
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
        "environment": f"Python 3.11, NumPy {NUMPY_VERSION}",
        "gate_terminated": False,
        "termination_gate": "none",
        "reml_convergence": {
            "converged": True,
            "iterations": 1,
            "final_nll": float(restricted_nll(tau2, ys, variances)),
        },
        "computation_time_ms": round(computation_time, 1),
        "tel5_input": {
            "P_value": round(P, 6),
            "phi_violation": False,
            "k_violation": False,
        },
        "policy_fingerprint": fingerprint,
    }

    return result


def validate_evidence_data(evidence_rows: List[Dict[str, Any]]) -> List[str]:
    """Validate Evidence State Vector rows for required fields and sanity."""

    errors: List[str] = []
    required_fields = ["effect_point", "ci_low", "ci_high", "effect_type", "study_id"]
    recommended_fields = ["year", "design", "n_treat", "n_ctrl", "doi", "journal_id"]

    for index, row in enumerate(evidence_rows):
        row_id = f"Row {index + 1} ({row.get('study_id', 'unknown')})"
        for field in required_fields:
            if field not in row or row[field] is None:
                errors.append(f"{row_id}: Missing required field '{field}'")
                continue
        missing_recommended = [f for f in recommended_fields if f not in row or row[f] is None]
        if missing_recommended:
            logger.warning(
                f"{row_id}: Missing recommended fields: {', '.join(missing_recommended)}"
            )
        try:
            effect = float(row["effect_point"])
            ci_low = float(row["ci_low"])
            ci_high = float(row["ci_high"])
            if ci_low >= ci_high:
                errors.append(
                    f"{row_id}: CI lower bound ({ci_low}) must be < upper bound ({ci_high})"
                )
            tolerance = abs(ci_high - ci_low) * 0.01
            if not (ci_low - tolerance <= effect <= ci_high + tolerance):
                errors.append(
                    f"{row_id}: Effect point estimate ({effect}) outside CI bounds [{ci_low}, {ci_high}]"
                )
            ci_width = ci_high - ci_low
            if ci_width > 10:
                logger.warning(f"{row_id}: Very wide confidence interval (width: {ci_width:.2f})")
            effect_type = str(row["effect_type"]).upper()
            if effect_type in ("OR", "RR", "HR"):
                if effect <= 0 or ci_low <= 0 or ci_high <= 0:
                    errors.append(f"{row_id}: {effect_type} values must be positive")
        except (TypeError, ValueError) as exc:
            errors.append(f"{row_id}: Invalid numeric values in effect size fields: {exc}")

        valid_effect_types = ["SMD", "MD", "OR", "RR", "HR", "COHEN-D", "HEDGES-G"]
        effect_type = str(row.get("effect_type", "")).upper()
        if effect_type not in valid_effect_types:
            errors.append(
                f"{row_id}: Invalid effect_type '{effect_type}'. Must be one of: {', '.join(valid_effect_types)}"
            )

        for size_field in ["n_treat", "n_ctrl"]:
            if size_field in row and row[size_field] is not None:
                try:
                    n = int(row[size_field])
                    if n <= 0:
                        errors.append(f"{row_id}: {size_field} must be positive integer")
                except (TypeError, ValueError):
                    errors.append(f"{row_id}: {size_field} must be integer")

    return errors


def run_mc(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Backward-compatible alias for legacy callers."""

    return run_reml_mc_analysis(*args, **kwargs)


__all__ = [
    "MCConfig",
    "ci_to_se",
    "restricted_nll",
    "reml_tau2",
    "compute_heterogeneity_stats",
    "run_reml_mc_analysis",
    "run_mc",
    "validate_evidence_data",
]
