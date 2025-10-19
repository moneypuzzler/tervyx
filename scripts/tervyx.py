#!/usr/bin/env python3
"""
TERVYX Protocol CLI
===================

Command line interface for building, validating, and auditing TERVYX evidence
entries. The CLI provides three complementary workflows:

1. Manual curation (``new``/``build``/``validate``) for teams that already have
   structured study data in ``entries/.../evidence.csv``.
2. Policy and governance utilities (``fingerprint``/``status``) that surface
   reproducibility fingerprints and TEL-5 gate summaries.
3. Real-data ingestion (``ingest``) which orchestrates the production pipeline
   combining PubMed, Gemini (tiered), journal-quality assessments, and the REML
   + Monte Carlo engine.

The previous ``scripts/vera.py`` tooling shipped synthetic templates and HBV
labels. This rewrite removes fabricated defaults, aligns all commands with the
TERVYX naming, and wires the real-data pipeline so that entries can be generated
from actual publications once API credentials are configured.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import pathlib
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tervyx.core import ensure_paths_on_sys_path, settings
from tervyx.policy import (
    Fingerprint,
    PolicyError,
    canonical_json,
    compact_hex,
    compute_policy_fingerprint,
    load_journal_snapshot,
    read_policy,
    sha256_digest,
)

ensure_paths_on_sys_path()

ROOT = settings.root

# Engine imports (kept local to ensure path bootstrap above runs first)
from mc_meta import run_reml_mc_analysis, validate_evidence_data  # type: ignore  # noqa: E402
from tel5_rules import apply_l_gate_penalty, tel5_classify  # type: ignore  # noqa: E402
from gates import evaluate_all_gates  # type: ignore  # noqa: E402
from schema_validate import validate_all_artifacts  # type: ignore  # noqa: E402

try:  # Optional: real-data pipeline (skips gracefully in environments without deps)
    from real_tervyx_pipeline import RealTERVYXPipeline  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover - pipeline is optional for fast tests
    RealTERVYXPipeline = None  # type: ignore

# Shared credential helpers
try:  # noqa: E402 - depends on SYSTEM_PATH injection above
    from credential_validation import validate_gemini_api_key  # type: ignore
except Exception:  # pragma: no cover - helper is only required for ingest
    validate_gemini_api_key = None  # type: ignore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AUDIT_LOG_PATH = settings.audit_log_path
DEFAULT_ENTRY_TEMPLATE_HEADER = (
    "study_id,year,design,effect_type,effect_point,ci_low,ci_high,"  # noqa: B950
    "n_treat,n_ctrl,risk_of_bias,doi,journal_id"
)
PRISMA_HEADERS = [
    "stage",
    "date",
    "who",
    "query",
    "source",
    "n_found",
    "n_screened",
    "n_excluded",
    "included",
    "reasons",
    "notes",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_policy_or_exit() -> Dict[str, Any]:
    try:
        return read_policy()
    except PolicyError as exc:
        raise SystemExit(f"❌ {exc}") from exc


def load_policy_fingerprint() -> Fingerprint:
    try:
        return compute_policy_fingerprint()
    except PolicyError as exc:
        raise SystemExit(f"❌ {exc}") from exc


def load_snapshot_or_exit(relative_path: Optional[str]) -> Dict[str, Any]:
    try:
        return load_journal_snapshot(relative_path)
    except PolicyError as exc:
        raise SystemExit(f"❌ {exc}") from exc


def ensure_directory(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_evidence_csv(path: pathlib.Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Evidence file not found: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader if any(value.strip() for value in row.values())]

    if not rows:
        raise ValueError(
            "No study rows found in evidence.csv — populate the file with real study data "
            "before running 'build'."
        )

    # Normalize numeric columns
    for row in rows:
        for field in ("year", "n_treat", "n_ctrl"):
            if row.get(field):
                row[field] = int(row[field])

        for field in ("effect_point", "ci_low", "ci_high"):
            if row.get(field) is not None:
                row[field] = float(row[field])

    validation_errors = validate_evidence_data(rows)
    if validation_errors:
        error_block = "\n".join(f"- {err}" for err in validation_errors)
        raise ValueError(f"Evidence validation failed:\n{error_block}")

    return rows


def parse_entry_path(path_str: str) -> pathlib.Path:
    path = pathlib.Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Entry directory not found: {path}")
    return path


def resolve_entry_metadata(entry_dir: pathlib.Path) -> Dict[str, str]:
    parts = entry_dir.resolve().parts
    try:
        domain, slug, category, version = parts[-4:]
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"Invalid entry path '{entry_dir}'. Expected format: entries/<domain>/<slug>/<category>/<version>"
        ) from exc
    return {
        "domain": domain,
        "slug": slug,
        "category": category,
        "version": version,
    }


def write_json(path: pathlib.Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_audit_log(record: Dict[str, Any]) -> None:
    ensure_directory(AUDIT_LOG_PATH.parent)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def cmd_new(args: argparse.Namespace) -> None:
    meta = {
        "domain": args.domain,
        "slug": args.slug,
        "category": args.category,
        "version": "v1",
        "created": datetime.utcnow().isoformat() + "Z",
        "status": "draft",
    }

    entry_dir = ROOT / "entries" / args.domain / args.slug / args.category / "v1"
    ensure_directory(entry_dir)

    # evidence.csv: header only — no synthetic placeholder rows
    evidence_path = entry_dir / "evidence.csv"
    evidence_path.write_text(DEFAULT_ENTRY_TEMPLATE_HEADER + "\n", encoding="utf-8")

    # citations & metadata placeholders
    write_json(entry_dir / "citations.json", {"studies": [], "preferred_citation": ""})
    write_json(entry_dir / "metadata.json", meta)

    # PRISMA log scaffold (CSV header only)
    prisma_path = entry_dir / "prisma_log.csv"
    prisma_path.write_text(",".join(PRISMA_HEADERS) + "\n", encoding="utf-8")

    print(f"✅ Created entry scaffold at {entry_dir.relative_to(ROOT)}")
    print("   Populate evidence.csv with real study data before running 'build'.")


def cmd_build(args: argparse.Namespace) -> None:
    policy = load_policy_or_exit()
    policy_fingerprint = load_policy_fingerprint()

    entry_dir = parse_entry_path(args.path)
    metadata = resolve_entry_metadata(entry_dir)

    if metadata["category"] != args.category:
        raise ValueError(
            f"Category mismatch: entry path uses '{metadata['category']}' but '--category {args.category}' was provided."
        )

    evidence = load_evidence_csv(entry_dir / "evidence.csv")

    snapshot_rel = policy.get("gates", {}).get("j", {}).get("use_snapshot")
    journal_snapshot = load_snapshot_or_exit(snapshot_rel)

    substance_hint = metadata["slug"].replace("-", " ")
    gate_results = evaluate_all_gates(
        evidence,
        metadata["category"],
        journal_snapshot,
        policy,
        f"{substance_hint} {metadata['category']} {metadata['domain']}",
    )

    phi_violation = gate_results["phi"]["violation"]
    k_violation = gate_results["k"]["violation"]

    simulation: Dict[str, Any]
    if gate_results["summary"].get("safety_monotonic"):
        # Hard fail due to Φ/K gate violation
        simulation = {
            "seed": policy["monte_carlo"]["seed"],
            "n_draws": policy["monte_carlo"]["n_draws"],
            "tau2_method": policy["monte_carlo"]["tau2_method"],
            "delta": policy["categories"][metadata["category"]]["delta"],
            "P_effect_gt_delta": 0.0,
            "mu_hat": 0.0,
            "mu_CI95": [0.0, 0.0],
            "I2": None,
            "tau2": None,
            "var_mu": None,
            "mu_se": None,
            "policy_fingerprint": policy_fingerprint.compact,
            "gate_terminated": True,
        }
        label, tier = ("FAIL", "Black")
    else:
        category_cfg = policy["categories"][metadata["category"]]
        simulation = run_reml_mc_analysis(
            evidence_rows=evidence,
            delta=category_cfg["delta"],
            benefit_direction=category_cfg.get("benefit_direction", 1),
            seed=policy["monte_carlo"]["seed"],
            n_draws=policy["monte_carlo"]["n_draws"],
            tau2_method=policy["monte_carlo"].get("tau2_method", "REML"),
        )
        simulation["policy_fingerprint"] = policy_fingerprint.compact

        P_effect = simulation.get("P_effect_gt_delta", 0.0)
        label, tier = tel5_classify(P_effect, phi_violation, k_violation)
        label, tier = apply_l_gate_penalty(label, tier, gate_results["l"]["violation"])

    # Persist simulation.json
    write_json(entry_dir / "simulation.json", simulation)

    audit_digest_full = sha256_digest(
        canonical_json(simulation)
        + canonical_json({"path": str(entry_dir.relative_to(ROOT)), "timestamp": datetime.utcnow().isoformat()})
    )
    audit_hash = compact_hex(audit_digest_full)

    r_score = gate_results["r"].get("score")
    r_display = gate_results["r"].get("result")
    if r_score is not None:
        r_display = f"{gate_results['r']['result']} ({r_score:.3f})"

    j_score_masked = gate_results["j"].get("score_masked")
    if j_score_masked is None:
        j_score_masked = gate_results["j"].get("score", 0.0)

    entry_payload = {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "id": f"{metadata['domain']}:{metadata['slug']}:{metadata['category']}:{metadata['version']}",
        "title": f"{substance_hint.title()} — {metadata['category'].replace('_', ' ').title()}",
        "category": metadata["category"],
        "tier_label_system": "TEL-5",
        "tier": tier,
        "label": label,
        "P_effect_gt_delta": round(simulation.get("P_effect_gt_delta", 0.0), 6),
        "gate_results": {
            "phi": gate_results["phi"]["result"],
            "r": r_display,
            "j": round(j_score_masked, 3),
            "k": gate_results["k"]["result"],
            "l": gate_results["l"]["result"],
        },
        "evidence_summary": {
            "n_studies": len(evidence),
            "total_n": simulation.get("total_n"),
            "I2": simulation.get("I2"),
            "tau2": simulation.get("tau2"),
            "mu_hat": simulation.get("mu_hat"),
            "mu_CI95": simulation.get("mu_CI95"),
        },
        "policy_refs": {
            "tel5_levels": policy.get("metadata", {}).get("tel5_version", "unknown"),
            "monte_carlo": policy.get("monte_carlo", {}).get("version", "unknown"),
            "journal_trust": journal_snapshot.get("snapshot_date", "unknown"),
        },
        "policy_fingerprint": policy_fingerprint.compact,
        "audit_hash": audit_hash,
        "version": metadata["version"],
        "created": datetime.utcnow().isoformat() + "Z",
    }

    entry_payload["llm_hint"] = (
        f"TEL-5={tier}, {label}; P(effect>δ)={simulation.get('P_effect_gt_delta', 0.0):.3f}; "
        f"J*={j_score_masked:.3f}; studies={len(evidence)}; total_n={simulation.get('total_n')}"
    )

    write_json(entry_dir / "entry.jsonld", entry_payload)

    append_audit_log(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "entry_id": entry_payload["id"],
            "audit_hash": audit_hash,
            "audit_digest_full": audit_digest_full,
            "policy_fingerprint": policy_fingerprint.compact,
            "policy_fingerprint_full": policy_fingerprint.full,
            "tier": tier,
            "label": label,
            "P_effect_gt_delta": simulation.get("P_effect_gt_delta"),
        }
    )

    print(
        f"✅ Build complete: {entry_payload['id']} → {label}/{tier} "
        f"(P(effect>δ) = {simulation.get('P_effect_gt_delta', 0.0):.3f})"
    )


def cmd_validate(args: argparse.Namespace) -> None:
    entry_dir = parse_entry_path(args.path)

    results = validate_all_artifacts(entry_dir)
    if results["overall_valid"]:
        print("✅ All artifacts validated against schemas")
    else:
        print("❌ Validation failures detected")
        for name, outcome in results["validations"].items():
            if not outcome["valid"]:
                print(f"\n{name.upper()} ERRORS:")
                for error in outcome["errors"]:
                    path_str = " -> ".join(str(p) for p in error.get("path", [])) or "root"
                    print(f"  {path_str}: {error['message']}")
        sys.exit(1)


def cmd_fingerprint(_: argparse.Namespace) -> None:
    fingerprint = load_policy_fingerprint()
    print(fingerprint.compact)
    print(fingerprint.full)


def cmd_status(_: argparse.Namespace) -> None:
    policy = load_policy_or_exit()
    fingerprint = load_policy_fingerprint()

    entries_dir = ROOT / "entries"
    entry_files = list(entries_dir.glob("*/*/*/v*/entry.jsonld")) if entries_dir.exists() else []

    print("TERVYX System Status")
    print("=" * 80)
    print(f"Policy Version      : {policy.get('version')} ({policy.get('protocol')})")
    print(f"TEL-5 Tier System   : {policy.get('tier_system')}" )
    print(
        "Policy Fingerprint  : "
        f"{fingerprint.compact} (full {fingerprint.full})"
    )
    print(f"Entries Detected    : {len(entry_files)}")

    tier_counts: Dict[str, int] = {}
    for path in entry_files:
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            tier = entry.get("tier", "Unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        except Exception:
            continue

    if tier_counts:
        print("\nTEL-5 Distribution:")
        for tier, count in sorted(tier_counts.items(), key=lambda item: item[0]):
            print(f"  • {tier}: {count}")

    if AUDIT_LOG_PATH.exists():
        with AUDIT_LOG_PATH.open(encoding="utf-8") as handle:
            lines = handle.readlines()
        print(f"\nAudit Log Entries  : {len(lines)}")
        if lines:
            print(f"Last Audit Record  : {lines[-1].strip()}")


def cmd_ingest(args: argparse.Namespace) -> None:
    if RealTERVYXPipeline is None:
        raise RuntimeError(
            "Real pipeline modules are unavailable. Ensure system dependencies are installed "
            "and rerun."
        )

    email = args.email or os.getenv("TERVYX_EMAIL")
    gemini_key = args.gemini_key or os.getenv("GEMINI_API_KEY")
    ncbi_key = args.ncbi_key or os.getenv("NCBI_API_KEY")

    if validate_gemini_api_key is None:
        raise RuntimeError(
            "Credential validation helpers are unavailable. Ensure system/credential_validation.py is importable."
        )

    is_valid_key, cleaned_key, key_error = validate_gemini_api_key(gemini_key)
    if not is_valid_key:
        guidance = [key_error]
        guidance.append(
            "If you are running inside GitHub Actions, expose the secret using:\n"
            "  env:\n"
            "    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}\n"
            "    TERVYX_EMAIL: ${{ secrets.TERVYX_EMAIL }}"
        )
        raise ValueError("\n".join(guidance))

    gemini_key = cleaned_key or gemini_key

    if not email:
        raise ValueError("Contact email is required (use --email or TERVYX_EMAIL env var).")

    pipeline = RealTERVYXPipeline(email=email, gemini_api_key=gemini_key, ncbi_api_key=ncbi_key)
    validation = pipeline.validate_configuration()
    if not validation.get("overall"):
        raise RuntimeError(f"Pipeline configuration invalid: {validation}")

    async def _run() -> Dict[str, Any]:
        return await pipeline.generate_entry(args.substance, args.category)

    result = asyncio.run(_run())

    if "error" in result:
        raise RuntimeError(f"Pipeline reported error: {result['error']}")

    output_dir = pathlib.Path(args.output_dir or ROOT / "entries_real")
    entry_path = output_dir / f"{args.substance}/{args.category}/v1"
    ensure_directory(entry_path)

    write_json(entry_path / "entry.jsonld", result)
    write_json(entry_path / "analysis_detailed.json", result)

    print(f"✅ Real-data entry generated and saved to {entry_path}")


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TERVYX Protocol CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tervyx new nutrient melatonin sleep\n"
            "  tervyx build entries/nutrient/melatonin/sleep/v1 --category sleep\n"
            "  tervyx ingest --substance melatonin --category sleep --output-dir data/ingested\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command")

    # new
    p_new = subparsers.add_parser("new", help="Create an empty entry scaffold")
    p_new.add_argument("domain", help="Domain (e.g. nutrient, botanical, intervention)")
    p_new.add_argument("slug", help="Slug (kebab-case identifier, e.g. magnesium-glycinate)")
    p_new.add_argument("category", help="Evidence category (e.g. sleep, cognition)")
    p_new.set_defaults(func=cmd_new)

    # build
    p_build = subparsers.add_parser("build", help="Build entry using TEL-5 pipeline")
    p_build.add_argument("path", help="Path to entry directory")
    p_build.add_argument("--category", required=True, help="Evidence category for delta/benefit config")
    p_build.set_defaults(func=cmd_build)

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate entry artifacts against schemas")
    p_validate.add_argument("path", help="Path to entry directory")
    p_validate.set_defaults(func=cmd_validate)

    # fingerprint
    p_fingerprint = subparsers.add_parser("fingerprint", help="Print policy fingerprint")
    p_fingerprint.set_defaults(func=cmd_fingerprint)

    # status
    p_status = subparsers.add_parser("status", help="Display repository status and TEL-5 summary")
    p_status.set_defaults(func=cmd_status)

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Run real-data ingestion pipeline (PubMed + Gemini)")
    p_ingest.add_argument("--substance", required=True, help="Substance name to analyse (e.g. melatonin)")
    p_ingest.add_argument("--category", required=True, help="Outcome category (sleep, cognition, etc.)")
    p_ingest.add_argument("--email", help="Contact email for NCBI")
    p_ingest.add_argument("--gemini-key", help="Gemini API key")
    p_ingest.add_argument("--ncbi-key", help="NCBI API key (optional)")
    p_ingest.add_argument(
        "--output-dir",
        help="Directory to write generated entry artifacts (defaults to entries_real/)",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except KeyboardInterrupt:  # pragma: no cover - CLI UX
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
