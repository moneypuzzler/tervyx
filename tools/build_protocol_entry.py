#!/usr/bin/env python3
"""Build TERVYX Protocol entry artifacts from evidence CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.citations import build_citations_payload, to_entry_references
from engine.gates import evaluate_gate_governance_protocol
from engine.mc_meta import run_reml_mc_analysis, validate_evidence_data
from engine.policy_fingerprint import compute_policy_fingerprint
from engine.schema_validate import validate_all_artifacts
from engine.tel5_rules import apply_l_gate_penalty, tel5_classify
from tervyx.policy.utils import read_policy, load_journal_snapshot


def load_evidence(path: pathlib.Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not any(value.strip() for value in row.values()):
                continue
            row["effect_point"] = float(row["effect_point"])
            row["ci_low"] = float(row["ci_low"])
            row["ci_high"] = float(row["ci_high"])
            row["year"] = int(row["year"])
            row["n_treat"] = int(row["n_treat"])
            row["n_ctrl"] = int(row["n_ctrl"])
            row["duration_weeks"] = int(row.get("duration_weeks", 0) or 0)
            rows.append(row)
    errors = validate_evidence_data(rows)
    if errors:
        raise ValueError("Evidence validation failed:\n" + "\n".join(f"- {err}" for err in errors))
    return rows


def design_breakdown(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        design = row.get("design", "").lower()
        if "random" in design or "rct" in design:
            counter["RCT"] += 1
        elif "cohort" in design:
            counter["cohort"] += 1
        else:
            counter["other"] += 1
    return {"RCT": counter.get("RCT", 0), "cohort": counter.get("cohort", 0), "other": counter.get("other", 0)}


def build_entry(entry_dir: pathlib.Path, claim_text: str) -> None:
    policy = read_policy()
    category = entry_dir.parent.name
    version = entry_dir.name
    substance = entry_dir.parent.parent.name
    domain = entry_dir.parent.parent.parent.name

    category_cfg = policy.get("categories", {}).get(category)
    if not category_cfg:
        raise ValueError(f"Category '{category}' not defined in policy.yaml")

    delta = float(category_cfg.get("delta", 0.0))
    benefit_direction = int(category_cfg.get("benefit_direction", 1))

    evidence_path = entry_dir / "evidence.csv"
    evidence_rows = load_evidence(evidence_path)

    fingerprint = compute_policy_fingerprint()

    simulation = run_reml_mc_analysis(
        evidence_rows,
        delta=delta,
        benefit_direction=benefit_direction,
        seed=policy.get("monte_carlo", {}).get("seed", 20251005),
        n_draws=policy.get("monte_carlo", {}).get("n_draws", 10000),
        policy_fingerprint=fingerprint.compact,
    )

    snapshot_rel = policy.get("gates", {}).get("j", {}).get("use_snapshot")
    snapshot = load_journal_snapshot(snapshot_rel)
    gates = evaluate_gate_governance_protocol(
        evidence_rows,
        category,
        snapshot,
        policy,
        substance=substance.replace("-", " "),
        claim_text=claim_text,
    )

    phi_violation = gates["phi"]["violation"]
    k_violation = gates["k"]["violation"]
    l_violation = gates["l"]["violation"]

    simulation["tel5_input"]["phi_violation"] = phi_violation
    simulation["tel5_input"]["k_violation"] = k_violation

    P = simulation["P_effect_gt_delta"]
    label, tier = tel5_classify(P, phi_violation=phi_violation, k_violation=k_violation)
    label, tier = apply_l_gate_penalty(label, tier, l_violation)

    entry_id = f"{domain}:{substance}:{category}:{version}"

    taxonomy_path = ROOT / "protocol" / "taxonomy" / "tel5_categories@v1.0.0.json"
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    tel5_version = taxonomy.get("metadata", {}).get("tel5_version", "v1.0.0")

    gate_results = {
        "phi": gates["phi"]["result"],
        "r": round(gates["r"].get("score", 0.0), 3),
        "j": round(gates["j"].get("score_masked", gates["j"].get("score", 0.0)), 3),
        "k": gates["k"]["result"],
        "l": "FLAG" if l_violation else "PASS",
    }

    evidence_summary = {
        "n_studies": simulation["n_studies"],
        "total_n": simulation["total_n"],
        "I2": simulation["I2"],
        "tau2": simulation["tau2"],
        "mu_hat": simulation["mu_hat"],
        "mu_CI95": simulation["mu_CI95"],
        "design_breakdown": design_breakdown(evidence_rows),
    }

    policy_refs = {
        "tel5_levels": tel5_version,
        "monte_carlo": policy.get("monte_carlo", {}).get("version", "unknown"),
        "journal_trust": snapshot.get("snapshot_date", "unknown"),
    }

    title = f"{substance.replace('-', ' ').title()} — {category.replace('_', ' ').title()}"

    preferred_citation = "Kim G. TERVYX Protocol v1.0 (2025)."

    citations_payload = build_citations_payload(
        evidence_rows,
        policy_fingerprint=fingerprint.compact,
        evidence_path=str(evidence_path.relative_to(ROOT)),
        preferred_citation=preferred_citation,
    )

    entry = {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "id": entry_id,
        "title": title,
        "category": category,
        "tier": tier,
        "label": label,
        "P_effect_gt_delta": P,
        "gate_results": gate_results,
        "evidence_summary": evidence_summary,
        "policy_refs": policy_refs,
        "version": version,
        "policy_fingerprint": fingerprint.compact,
        "tier_label_system": "TEL-5",
        "created": datetime.now(timezone.utc).isoformat(),
        "preferred_citation": preferred_citation,
        "bibtex": "@techreport{tervyx2025, title={TERVYX Protocol v1.0}, author={Kim, Geonyeob}, year={2025}}",
        "csl_json": {
            "type": "report",
            "title": "TERVYX Protocol v1.0",
            "author": [{"family": "Kim", "given": "Geonyeob"}],
            "issued": {"date-parts": [[2025]]}
        },
        "references": to_entry_references(citations_payload),
        "citations_manifest_hash": citations_payload["manifest_hash"],
    }

    digest = hashlib.sha256(json.dumps({k: v for k, v in entry.items() if k != "audit_hash"}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    entry["audit_hash"] = f"0x{digest[:16]}"

    simulation_path = entry_dir / "simulation.json"
    entry_path = entry_dir / "entry.jsonld"
    citations_path = entry_dir / "citations.json"

    simulation_path.write_text(json.dumps(simulation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    entry_path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    citations_path.write_text(json.dumps(citations_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    results = validate_all_artifacts(entry_dir)
    if not results["overall_valid"]:
        raise RuntimeError("Artifact validation failed:\n" + json.dumps(results, indent=2))

    print(f"✅ Built entry at {entry_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build TERVYX entry artifacts")
    parser.add_argument("entry_path", type=pathlib.Path, help="Entry directory containing evidence.csv")
    parser.add_argument(
        "--claim",
        default="Magnesium glycinate supplementation improves sleep quality scores",
        help="Claim text for L-gate analysis",
    )
    args = parser.parse_args()

    build_entry(args.entry_path.resolve(), args.claim)


if __name__ == "__main__":
    main()
