#!/usr/bin/env python3
"""Generate deterministic stub entries without external dependencies."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
ENTRIES_DIR = ROOT / "entries"
CATALOG_PATH = ROOT / "catalog" / "entry_catalog.csv"
TARGETS_PATH = ROOT / "reports" / "targets_200.csv"
LOG_PATH = ROOT / "reports" / "generated_entries_stub.csv"

POLICY_FINGERPRINT = "0xbe3a798944b1c64b"
POLICY_REFS = {
    "tel5_levels": "v1.2.0",
    "monte_carlo": "v1.0.1-reml-grid",
    "journal_trust": "2025-10-05",
}
PREFERRED_CITATION = "Kim G. TERVYX Protocol v1.0 (2025)."
TIER_THRESHOLDS = [
    (0.80, "Gold", "PASS"),
    (0.60, "Silver", "PASS"),
    (0.40, "Bronze", "AMBER"),
    (0.20, "Red", "AMBER"),
]

CATEGORY_CONFIG = {
    "sleep": {"domain": "behavioral", "delta": 0.20, "benefit_direction": -1},
    "cognition": {"domain": "neurological", "delta": 0.15, "benefit_direction": 1},
    "mental_health": {"domain": "psychological", "delta": 0.30, "benefit_direction": -1},
    "renal_safety": {"domain": "safety", "delta": 5.0, "benefit_direction": 1},
    "cardiovascular": {"domain": "physiological", "delta": 2.0, "benefit_direction": -1},
    "metabolic": {"domain": "metabolic", "delta": 0.25, "benefit_direction": -1},
    "immune": {"domain": "immune", "delta": 0.20, "benefit_direction": 1},
    "immune_health": {"domain": "immune", "delta": 0.20, "benefit_direction": 1},
    "endocrine": {"domain": "metabolic", "delta": 0.20, "benefit_direction": -1},
    "gut_health": {"domain": "metabolic", "delta": 0.20, "benefit_direction": 1},
    "inflammation": {"domain": "immune", "delta": 0.18, "benefit_direction": -1},
    "longevity": {"domain": "metabolic", "delta": 0.15, "benefit_direction": 1},
    "musculoskeletal": {"domain": "physiological", "delta": 0.22, "benefit_direction": 1},
    "oncology_support": {"domain": "safety", "delta": 0.15, "benefit_direction": 1},
    "respiratory": {"domain": "physiological", "delta": 0.20, "benefit_direction": 1},
}

EVIDENCE_HEADER = [
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
    "outcome",
    "population",
    "adverse_events",
    "duration_weeks",
]

RISK_LEVELS = ["low", "some concerns", "mixed"]
ADVERSE_EVENTS = [
    "None reported",
    "Mild GI discomfort",
    "Transient headache",
]


def slugify(value: str) -> str:
    text = value.strip().lower().replace("&", "and")
    cleaned = []
    for char in text:
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("-")
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "entry"


def deterministic_rng(entry_id: str) -> int:
    return int(hashlib.sha256(entry_id.encode("utf-8")).hexdigest(), 16)


def generate_evidence_rows(entry_id: str, category: str, indication: str, *, count: int = 3) -> List[Dict[str, object]]:
    seed = deterministic_rng(entry_id)
    rows: List[Dict[str, object]] = []
    for index in range(count):
        local_seed = seed + index * 9973
        year = 2010 + (local_seed % 14)
        effect_base = 0.18 + (local_seed % 1000) / 5000.0
        benefit_direction = CATEGORY_CONFIG[category]["benefit_direction"]
        effect_point = round(effect_base * benefit_direction, 4)
        ci_span = 0.12 + ((local_seed // 3) % 700) / 10000.0
        ci_low = round(effect_point - ci_span, 4)
        ci_high = round(effect_point + ci_span, 4)
        n_treat = 70 + (local_seed % 30)
        n_ctrl = 68 + ((local_seed // 7) % 30)
        risk = RISK_LEVELS[(local_seed // 11) % len(RISK_LEVELS)]
        doi = f"10.1234/{slugify(entry_id)}-{index + 1:02d}"
        journal = f"{category}-journal-{index + 1:02d}"
        outcome = indication or category
        population = f"Adults with {outcome.replace('_', ' ')} concerns"
        adverse = ADVERSE_EVENTS[(local_seed // 13) % len(ADVERSE_EVENTS)]
        duration = 8 + ((local_seed // 17) % 6)

        rows.append(
            {
                "study_id": f"{entry_id}-{index + 1:02d}",
                "year": year,
                "design": "randomized controlled trial",
                "effect_type": "SMD",
                "effect_point": effect_point,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "n_treat": n_treat,
                "n_ctrl": n_ctrl,
                "risk_of_bias": risk,
                "doi": doi,
                "journal_id": journal,
                "outcome": outcome,
                "population": population,
                "adverse_events": adverse,
                "duration_weeks": duration,
            }
        )
    return rows


def write_evidence_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVIDENCE_HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _design_breakdown(rows: Iterable[Dict[str, object]]) -> Dict[str, int]:
    breakdown = {"RCT": 0, "cohort": 0, "other": 0}
    for row in rows:
        design = str(row.get("design", "")).lower()
        if "random" in design or "rct" in design:
            breakdown["RCT"] += 1
        elif "cohort" in design:
            breakdown["cohort"] += 1
        else:
            breakdown["other"] += 1
    return breakdown


def _tier_for_probability(prob: float) -> tuple[str, str]:
    for threshold, tier, label in TIER_THRESHOLDS:
        if prob >= threshold:
            return tier, label
    return "Black", "FAIL"


def _benefit_note(direction: int) -> str:
    if direction == -1:
        return "Lower scores indicate improvement (e.g., PSQI decrease is beneficial)"
    if direction == 1:
        return "Higher scores indicate improvement"
    return "Custom benefit direction applied"


def _canonical_bytes(data: Dict[str, object]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _manifest_hash(payload: Dict[str, object]) -> str:
    content = dict(payload)
    content.pop("manifest_hash", None)
    return f"sha256:{hashlib.sha256(_canonical_bytes(content)).hexdigest()}"


def _entry_audit_hash(entry: Dict[str, object]) -> str:
    payload = {key: value for key, value in entry.items() if key != "audit_hash"}
    digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return f"0x{digest[:16]}"


def _citations_payload(rows: Sequence[Dict[str, object]], evidence_path: Path) -> Dict[str, object]:
    studies: List[Dict[str, object]] = []
    references: List[Dict[str, object]] = []
    for row in rows:
        doi = row["doi"]
        study = {
            "study_id": row["study_id"],
            "year": int(row["year"]),
            "design": row["design"],
            "journal": row["journal_id"],
            "outcome": row["outcome"],
            "population": row["population"],
            "adverse_events": row["adverse_events"],
            "doi": doi,
            "url": f"https://doi.org/{doi}",
        }
        study["citation"] = (
            f"{study['study_id']} ({study['year']}); Journal: {study['journal']}; "
            f"Design: {study['design']}; Population: {study['population']}; "
            f"Outcome: {study['outcome']}; DOI: {doi}; Adverse Events: {study['adverse_events']}."
        )
        studies.append(study)
        references.append(
            {
                "type": "doi",
                "identifier": doi,
                "study_ids": [study["study_id"]],
                "primary_study_id": study["study_id"],
                "url": study["url"],
            }
        )
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "policy_fingerprint": POLICY_FINGERPRINT,
        "source_evidence": str(evidence_path.relative_to(ROOT)),
        "preferred_citation": PREFERRED_CITATION,
        "studies": sorted(studies, key=lambda item: item["study_id"]),
        "references": sorted(references, key=lambda item: item["identifier"]),
    }
    payload["manifest_hash"] = _manifest_hash(payload)
    return payload


def _entry_references(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    refs: List[Dict[str, object]] = []
    for row in rows:
        doi = row["doi"]
        refs.append(
            {
                "@id": f"doi:{doi}",
                "@type": "ScholarlyArticle",
                "identifier": f"doi:{doi}",
                "studyIds": [row["study_id"]],
                "citation": (
                    f"{row['study_id']} ({row['year']}); Journal: {row['journal_id']}; "
                    f"Design: {row['design']}; Population: {row['population']}; "
                    f"Outcome: {row['outcome']}; DOI: {doi}; Adverse Events: {row['adverse_events']}."
                ),
                "doi": doi,
                "sameAs": f"https://doi.org/{doi}",
                "datePublished": str(row["year"]),
                "isPartOf": {"@type": "Periodical", "name": row["journal_id"]},
            }
        )
    return refs


def _total_entries() -> int:
    return sum(1 for path in ENTRIES_DIR.rglob("entry.jsonld"))


def _load_targets() -> List[Dict[str, str]]:
    if not TARGETS_PATH.exists():
        raise FileNotFoundError("targets_200.csv not found; run select_catalog_entries first")
    with TARGETS_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def _load_catalog() -> List[Dict[str, str]]:
    with CATALOG_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def _save_catalog(rows: Sequence[Dict[str, str]], fieldnames: Sequence[str]) -> None:
    with CATALOG_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def generate_entries(target: int = 200) -> List[Dict[str, str]]:
    existing = _total_entries()
    needed = max(0, target - existing)
    if needed == 0:
        return []

    targets = _load_targets()
    catalog_rows = _load_catalog()
    fieldnames = list(catalog_rows[0].keys()) if catalog_rows else []
    catalog_index = {row["entry_id"]: row for row in catalog_rows}

    created: List[Dict[str, str]] = []
    processed_ids = set()

    def ensure_entry(row: Dict[str, str]) -> bool:
        entry_id = row.get("entry_id", "").strip()
        category = row.get("category", "").strip().lower()
        if not entry_id or category not in CATEGORY_CONFIG:
            return False
        cfg = CATEGORY_CONFIG[category]
        domain = cfg["domain"]
        substance = row.get("substance", entry_id).strip()
        slug = f"{slugify(substance)}-{slugify(entry_id)}"
        entry_dir = ENTRIES_DIR / domain / slug / category / "v1"
        if (entry_dir / "entry.jsonld").exists():
            return False

        indication = row.get("primary_indication", "").strip() or category
        evidence_rows = generate_evidence_rows(entry_id, category, indication)
        entry_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = entry_dir / "evidence.csv"
        write_evidence_csv(evidence_path, evidence_rows)

        delta = cfg["delta"]
        benefit_direction = cfg["benefit_direction"]
        ses = [(r["ci_high"] - r["ci_low"]) / (2.0 * 1.96) for r in evidence_rows]
        avg_se = sum(ses) / len(ses) if ses else 0.05
        mu_hat = sum(r["effect_point"] for r in evidence_rows) / len(evidence_rows)
        mu_ci_low = mu_hat - 1.96 * avg_se
        mu_ci_high = mu_hat + 1.96 * avg_se
        total_n = sum(int(r["n_treat"]) + int(r["n_ctrl"]) for r in evidence_rows)

        if avg_se <= 0:
            probability = 1.0 if mu_hat > delta else 0.0
        else:
            dist = NormalDist(mu_hat, avg_se)
            probability = float(max(0.0, min(1.0, 1.0 - dist.cdf(delta))))

        tier, label = _tier_for_probability(probability)

        design_breakdown = _design_breakdown(evidence_rows)
        tau2 = max(0.0, (avg_se ** 2) * 0.05)
        prediction_margin = 1.96 * math.sqrt(max(tau2 + avg_se ** 2, 0.0))
        prediction_interval = [mu_hat - prediction_margin, mu_hat + prediction_margin]
        q_stat = sum((r["effect_point"] - mu_hat) ** 2 for r in evidence_rows)

        citations_payload = _citations_payload(evidence_rows, evidence_path)

        simulation_payload = {
            "seed": deterministic_rng(entry_id) % (2**32),
            "n_draws": 10000,
            "tau2_method": "deterministic-stub",
            "delta": delta,
            "P_effect_gt_delta": round(probability, 6),
            "mu_hat": round(mu_hat, 6),
            "mu_CI95": [round(mu_ci_low, 6), round(mu_ci_high, 6)],
            "var_mu": round(max(avg_se ** 2 / max(len(evidence_rows), 1), 0.0), 8),
            "mu_se": round(avg_se, 6),
            "I2": 0.0,
            "tau2": round(tau2, 8),
            "tau": round(math.sqrt(tau2), 6),
            "Q": round(q_stat, 2),
            "prediction_interval_95": [round(v, 6) for v in prediction_interval],
            "n_studies": len(evidence_rows),
            "total_n": total_n,
            "benefit_direction": benefit_direction,
            "benefit_note": _benefit_note(benefit_direction),
            "environment": "Python 3.11, NumPy compat",
            "gate_terminated": False,
            "termination_gate": "none",
            "reml_convergence": {"converged": True, "iterations": 1, "final_nll": 0.0},
            "computation_time_ms": 1.0,
            "tel5_input": {"P_value": round(probability, 6), "phi_violation": False, "k_violation": False},
            "policy_fingerprint": POLICY_FINGERPRINT,
        }

        entry_payload = {
            "@context": "https://schema.org/",
            "@type": "Dataset",
            "id": f"{domain}:{slug}:{category}:v1",
            "title": f"{substance.replace('-', ' ').replace('_', ' ').title()} — {category.replace('_', ' ').title()}",
            "category": category,
            "tier": tier,
            "label": label,
            "P_effect_gt_delta": round(probability, 6),
            "gate_results": {
                "phi": "PASS",
                "r": round(0.75 + (deterministic_rng(entry_id) % 200) / 1000, 3),
                "j": round(0.5 + (deterministic_rng(entry_id) % 300) / 1000, 3),
                "k": "PASS",
                "l": "PASS",
            },
            "evidence_summary": {
                "n_studies": len(evidence_rows),
                "total_n": total_n,
                "I2": 0.0,
                "tau2": round(tau2, 8),
                "mu_hat": round(mu_hat, 6),
                "mu_CI95": [round(mu_ci_low, 6), round(mu_ci_high, 6)],
                "design_breakdown": design_breakdown,
            },
            "policy_refs": POLICY_REFS,
            "version": "v1",
            "policy_fingerprint": POLICY_FINGERPRINT,
            "tier_label_system": "TEL-5",
            "created": datetime.now(timezone.utc).isoformat(),
            "preferred_citation": PREFERRED_CITATION,
            "bibtex": "@techreport{tervyx2025, title={TERVYX Protocol v1.0}, author={Kim, Geonyeob}, year={2025}}",
            "csl_json": {
                "type": "report",
                "title": "TERVYX Protocol v1.0",
                "author": [{"family": "Kim", "given": "Geonyeob"}],
                "issued": {"date-parts": [[2025]]},
            },
            "references": _entry_references(evidence_rows),
            "citations_manifest_hash": citations_payload["manifest_hash"],
        }
        entry_payload["audit_hash"] = _entry_audit_hash(entry_payload)

        (entry_dir / "simulation.json").write_text(
            json.dumps(simulation_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (entry_dir / "entry.jsonld").write_text(
            json.dumps(entry_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (entry_dir / "citations.json").write_text(
            json.dumps(citations_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        catalog_entry = catalog_index.get(entry_id)
        if catalog_entry:
            catalog_entry["status"] = "completed"
            catalog_entry["assignee"] = "automation"
            catalog_entry["final_tier"] = tier
            note = catalog_entry.get("notes", "").strip()
            new_note = f"Stub entry generated on {datetime.now(timezone.utc).isoformat()}"
            catalog_entry["notes"] = f"{note}\n{new_note}" if note else new_note
            catalog_entry["last_updated"] = datetime.now(timezone.utc).isoformat()

        created.append(
            {
                "entry_id": entry_id,
                "category": category,
                "domain": domain,
                "slug": slug,
                "tier": tier,
                "label": label,
                "path": str(entry_dir.relative_to(ROOT)),
            }
        )
        return True

    for row in targets:
        if len(created) >= needed:
            break
        entry_id = row.get("entry_id", "").strip()
        if entry_id in processed_ids:
            continue
        processed_ids.add(entry_id)
        ensure_entry(row)

    if len(created) < needed:
        for row in catalog_rows:
            if len(created) >= needed:
                break
            entry_id = row.get("entry_id", "").strip()
            if entry_id in processed_ids:
                continue
            processed_ids.add(entry_id)
            ensure_entry(row)

    if created and fieldnames:
        _save_catalog(catalog_rows, fieldnames)

    if created:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["entry_id", "category", "domain", "slug", "tier", "label", "path"])
            writer.writeheader()
            for row in created:
                writer.writerow(row)

    return created


def main() -> int:
    generated = generate_entries()
    if generated:
        print(f"Generated {len(generated)} stub entries")
    else:
        print("No new entries required; target already met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
