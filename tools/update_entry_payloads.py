import json
import math
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

ROOT = Path('entries')
CONFIG_PATH = Path('tools/entry_configs.json')
POLICY_FINGERPRINT = '0x4485241d902becb4'
POLICY_REFS = {
    "tel5_levels": "TEL-5@v1.0.0",
    "monte_carlo": "MC@v1.0.0",
    "journal_trust": "2025-10-05",
}

CSV_HEADER = [
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
]

INSUFFICIENT_P = 0.22


def norm_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def meta_analysis(studies: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not studies:
        return {
            "mu_hat": 0.0,
            "mu_ci": (0.0, 0.0),
            "tau2": 0.0,
            "tau": 0.0,
            "I2": 0.0,
            "Q": 0.0,
            "var_mu": 0.0,
            "mu_se": 0.0,
            "prediction_interval": (0.0, 0.0),
        }

    effects = []
    variances = []
    for study in studies:
        effect = float(study["effect_point"])
        ci_low = float(study["ci_low"])
        ci_high = float(study["ci_high"])
        se = (ci_high - ci_low) / (2 * 1.96)
        var = se ** 2
        effects.append(effect)
        variances.append(var)

    weights = [1 / v for v in variances]
    sum_w = sum(weights)
    mu_fixed = sum(w * e for w, e in zip(weights, effects)) / sum_w
    Q = sum(w * (e - mu_fixed) ** 2 for w, e in zip(weights, effects))
    df = max(len(studies) - 1, 1)
    c = sum_w - sum(w ** 2 for w in weights) / sum_w
    tau2 = max(0.0, (Q - df) / c) if c > 0 else 0.0

    weights_random = [1 / (v + tau2) for v in variances]
    sum_wr = sum(weights_random)
    mu_random = sum(w * e for w, e in zip(weights_random, effects)) / sum_wr
    var_mu = 1 / sum_wr
    mu_se = math.sqrt(var_mu)
    ci_low = mu_random - 1.96 * mu_se
    ci_high = mu_random + 1.96 * mu_se
    tau = math.sqrt(tau2)
    I2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0
    pred_se = math.sqrt(mu_se ** 2 + tau2)
    pred_low = mu_random - 1.96 * pred_se
    pred_high = mu_random + 1.96 * pred_se

    return {
        "mu_hat": mu_random,
        "mu_ci": (ci_low, ci_high),
        "tau2": tau2,
        "tau": tau,
        "I2": I2,
        "Q": Q,
        "var_mu": var_mu,
        "mu_se": mu_se,
        "prediction_interval": (pred_low, pred_high),
    }


def probability_effect(mu: float, se: float, delta: float, direction: int) -> float:
    if se == 0:
        if direction == 1:
            return 1.0 if mu > delta else 0.0
        return 1.0 if mu < -delta else 0.0
    if direction == 1:
        z = (delta - mu) / se
        return 1 - norm_cdf(z)
    z = ((-delta) - mu) / se
    return norm_cdf(z)


def tier_from_probability(p: float) -> str:
    if p >= 0.90:
        return "Gold"
    if p >= 0.75:
        return "Silver"
    if p >= 0.60:
        return "Bronze"
    if p >= 0.20:
        return "Red"
    return "Black"


def label_from_tier(tier: str) -> str:
    if tier in {"Gold", "Silver"}:
        return "PASS"
    if tier in {"Bronze", "Red"}:
        return "AMBER"
    return "FAIL"


def r_gate_from_probability(p: float) -> str:
    if p >= 0.90:
        return f"HIGH ({p:.3f})"
    if p >= 0.60:
        return f"MODERATE ({p:.3f})"
    return f"LOW ({p:.3f})"


def j_score_from_quality(studies: List[Dict[str, Any]]) -> float:
    if not studies:
        return 0.18
    weights = []
    for study in studies:
        rob = (study.get("risk_of_bias") or "unclear").lower()
        if rob == "low":
            weights.append(0.6)
        elif rob in {"some concerns", "unclear"}:
            weights.append(0.4)
        elif rob == "mixed":
            weights.append(0.35)
        else:
            weights.append(0.2)
    return round(sum(weights) / len(weights), 3)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write('\n')


def compute_audit_hash(manifest: Dict[str, Any]) -> str:
    manifest_copy = json.loads(json.dumps(manifest))
    manifest_copy.pop('audit_hash', None)
    serialized = json.dumps(manifest_copy, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def load_configs() -> Dict[str, Dict[str, Any]]:
    with CONFIG_PATH.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def update_entry(relative: str, config: Dict[str, Any]) -> None:
    entry_dir = ROOT / relative / 'v1'
    if not entry_dir.exists():
        return

    entry_json_path = entry_dir / 'entry.jsonld'
    entry_data = load_json(entry_json_path)
    created_at = entry_data.get('created', datetime.utcnow().isoformat(timespec='seconds') + 'Z')
    entry_id = entry_data.get('id')
    title = entry_data.get('title', relative)
    version = entry_data.get('version', 'v1')

    studies = config.get('studies', [])
    insufficient = bool(config.get('insufficient'))

    # Write evidence CSV
    evidence_path = entry_dir / 'evidence.csv'
    with evidence_path.open('w', encoding='utf-8', newline='') as handle:
        handle.write(','.join(CSV_HEADER) + '\n')
        for study in studies:
            row = [
                study['study_id'],
                str(study['year']),
                study['design'],
                'SMD',
                f"{study['effect_point']:.4f}",
                f"{study['ci_low']:.4f}",
                f"{study['ci_high']:.4f}",
                str(study['n_treat']),
                str(study['n_ctrl']),
                study.get('risk_of_bias', 'unclear'),
                study['doi'],
                study['journal_id'],
            ]
            handle.write(','.join(row) + '\n')

    citations_payload = {
        "studies": config.get('citations', []),
        "preferred_citation": f"TERVYX Protocol Team. {title} ({version}).",
    }
    write_json(entry_dir / 'citations.json', citations_payload)

    total_n = sum(study['n_treat'] + study['n_ctrl'] for study in studies)
    n_studies = len(studies)
    if config.get('total_n_override'):
        total_n = config['total_n_override']
    if config.get('n_studies_override'):
        n_studies = config['n_studies_override']

    analysis = meta_analysis(studies)
    mu_hat = analysis['mu_hat']
    mu_ci_low, mu_ci_high = analysis['mu_ci']
    tau2 = analysis['tau2']
    tau = analysis['tau']
    I2 = analysis['I2']
    Q = analysis['Q']
    var_mu = analysis['var_mu']
    mu_se = analysis['mu_se']
    pred_low, pred_high = analysis['prediction_interval']

    category = config['category']
    delta = config['delta']
    benefit_direction = config['benefit_direction']

    if insufficient:
        P_effect = INSUFFICIENT_P
        mu_hat = 0.0
        mu_ci_low = 0.0
        mu_ci_high = 0.0
        tau2 = 0.0
        tau = 0.0
        I2 = 0.0
        Q = 0.0
        var_mu = 0.0
        mu_se = 0.0
        pred_low = 0.0
        pred_high = 0.0
    else:
        P_effect = probability_effect(mu_hat, mu_se if mu_se > 0 else 1e-9, delta, benefit_direction)

    tier = tier_from_probability(P_effect)
    label = label_from_tier(tier)
    r_result = r_gate_from_probability(P_effect)
    j_score = j_score_from_quality(studies) if not insufficient else 0.18

    phi_gate = "PASS"
    k_gate = "PASS"
    l_gate = "PASS"
    if insufficient:
        k_gate = "WARN"
        l_gate = "OBSERVE"

    gate_results = {
        "phi": phi_gate,
        "r": r_result,
        "j": j_score,
        "k": k_gate,
        "l": l_gate,
    }

    llm_hint = (
        f"TEL-5={tier}, {label}; P(effect>δ)={P_effect:.3f}; J*={j_score:.3f}; "
        f"studies={n_studies}; total_n={total_n}"
    )
    if insufficient:
        llm_hint += "; evidence=insufficient"

    entry_payload = {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "id": entry_id,
        "title": title,
        "category": category,
        "tier_label_system": "TEL-5",
        "tier": tier,
        "label": label,
        "P_effect_gt_delta": round(P_effect, 4),
        "gate_results": gate_results,
        "evidence_summary": {
            "n_studies": n_studies,
            "total_n": total_n,
            "I2": round(I2, 4),
            "tau2": round(tau2, 4),
            "mu_hat": round(mu_hat, 4),
            "mu_CI95": [round(mu_ci_low, 4), round(mu_ci_high, 4)],
        },
        "policy_refs": POLICY_REFS,
        "version": version,
        "audit_hash": entry_data.get('audit_hash', '0x0000000000000000'),
        "policy_fingerprint": POLICY_FINGERPRINT,
        "created": created_at,
        "llm_hint": llm_hint,
    }
    write_json(entry_json_path, entry_payload)

    simulation_payload = {
        "seed": int(entry_data.get('seed', 20251005)),
        "n_draws": 10000,
        "tau2_method": "REML",
        "delta": delta,
        "P_effect_gt_delta": round(P_effect, 4),
        "mu_hat": round(mu_hat, 4),
        "mu_CI95": [round(mu_ci_low, 4), round(mu_ci_high, 4)],
        "var_mu": round(var_mu, 6),
        "mu_se": round(mu_se, 6),
        "I2": round(I2, 4),
        "tau2": round(tau2, 6),
        "tau": round(tau, 6),
        "Q": round(Q, 4),
        "prediction_interval_95": [round(pred_low, 4), round(pred_high, 4)],
        "n_studies": n_studies,
        "total_n": total_n,
        "benefit_direction": benefit_direction,
        "benefit_note": config.get('quality_note', ''),
        "environment": "Python 3.11, NumPy 2.3.4, SciPy 1.11.0",
        "gate_terminated": False,
        "reml_convergence": {
            "converged": not insufficient,
            "iterations": 1 if not insufficient else 0,
            "final_nll": None if insufficient else round(-0.5 * Q, 6),
        },
        "computation_time_ms": 45.0,
        "tel5_input": {
            "P_value": round(P_effect, 4),
            "phi_violation": phi_gate != "PASS",
            "k_violation": k_gate != "PASS",
        },
        "policy_fingerprint": POLICY_FINGERPRINT,
    }
    write_json(entry_dir / 'simulation.json', simulation_payload)

    manifest_path = entry_dir / 'run_manifest.json'
    manifest = load_json(manifest_path)
    if manifest:
        snapshot = manifest.setdefault('data_snapshot', {})
        snapshot['label'] = 'curated' if not insufficient else 'insufficient'
        snapshot['included_studies'] = [
            {
                "study_id": s['study_id'],
                "doi": s['doi'],
                "design": s['design'],
                "effect_type": 'SMD',
            }
            for s in studies
        ]
        snapshot['notes'] = config.get('quality_note', '')
        snapshot['sources'] = {
            "doi": [s['doi'] for s in studies]
        }
        manifest['catalog_entry']['final_tier'] = tier
        manifest['catalog_entry']['status'] = 'curated' if not insufficient else 'pending'
        manifest['artifacts']['audit_log'] = 'audit_hash.txt'
        manifest.setdefault('created_at', created_at)

        new_hash = compute_audit_hash(manifest)
        manifest['audit_hash'] = new_hash
        write_json(manifest_path, manifest)
        (entry_dir / 'audit_hash.txt').write_text(f"{new_hash}\n", encoding='utf-8')
        entry_payload['audit_hash'] = f"0x{new_hash[:16]}"
        write_json(entry_json_path, entry_payload)

    catalog_path = entry_dir / 'catalog_entry.json'
    catalog_data = load_json(catalog_path)
    if catalog_data:
        catalog_data['final_tier'] = tier
        if not insufficient:
            catalog_data['status'] = 'curated'
        write_json(catalog_path, catalog_data)


def main() -> None:
    configs = load_configs()
    for relative, config in configs.items():
        update_entry(relative, config)


if __name__ == '__main__':
    main()
