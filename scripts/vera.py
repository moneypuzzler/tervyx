#!/usr/bin/env python3
"""
VERA Protocol CLI - Command line interface for building and managing health-claim entries.

This script provides the main interface for creating, building, and validating
VERA Protocol entries using the semi-automated pipeline.
"""

import argparse
import json
import os
import csv
import re
import hashlib
import sys
import pathlib
import yaml
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add engine modules to path
ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE_PATH = ROOT / "engine"
sys.path.insert(0, str(ENGINE_PATH))

# Import VERA engine modules
from mc_meta import run_mc, validate_evidence_data
from hbv_rules import hbv_label, apply_l_gate_penalty
from gates import evaluate_all_gates
from schema_validate import validate_all_artifacts

# Template files for new entries
TEMPLATE_EVIDENCE = """study_id,year,design,effect_type,effect_point,ci_low,ci_high,n_treat,n_ctrl,risk_of_bias,doi,journal_id
Kim2022,2022,RCT,SMD,0.42,0.15,0.69,120,118,low,10.1016/j.sleep.2022.abc,sleep_med
Lee2021,2021,RCT,SMD,0.25,0.02,0.48,80,78,some,10.1111/jsr.2021.def,j_sleep_res
Chen2020,2020,RCT,SMD,0.38,0.15,0.61,95,97,low,10.1016/j.sleh.2020.ghi,sleep_health
"""

PRISMA_HEADERS = [
    "stage", "date", "who", "query", "source", 
    "n_found", "n_screened", "n_excluded", "reasons", "notes"
]


def load_yaml(file_path: pathlib.Path) -> Dict[str, Any]:
    """Load and parse YAML file."""
    return yaml.safe_load(file_path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hash of byte data."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> bytes:
    """Convert object to canonical JSON bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_policy_fingerprint() -> str:
    """
    Compute policy fingerprint for reproducibility.
    
    Combines canonical representations of policy.yaml and journal snapshot
    to create a unique fingerprint for the current configuration.
    """
    try:
        # Load policy
        policy = load_yaml(ROOT / "policy.yaml")
        
        # Load journal snapshot
        snap_path = ROOT / policy["gates"]["j"]["use_snapshot"]
        snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
        
        # Create minimal policy representation (excluding noise)
        policy_min = {
            "version": policy["version"],
            "categories": policy["categories"],
            "gates": {
                "phi": policy["gates"]["phi"],
                "j": {"min_j": policy["gates"]["j"]["min_j"]},
                "k": policy["gates"]["k"],
                "l": {"deny_patterns": policy["gates"]["l"]["deny_patterns"]}
            },
            "monte_carlo": policy["monte_carlo"]
        }
        
        # Compute hashes
        h_policy = sha256_bytes(canonical_json(policy_min)).split(":", 1)[1]
        h_snap = sha256_bytes(canonical_json(snapshot["journals"])).split(":", 1)[1]
        
        # Combined fingerprint
        combined_hash = hashlib.sha256((h_policy + h_snap).encode()).hexdigest()
        return f"sha256:{combined_hash}"
        
    except Exception as e:
        print(f"Error computing policy fingerprint: {e}", file=sys.stderr)
        return f"sha256:ERROR_{datetime.now().isoformat()}"


def ensure_directory(path: pathlib.Path) -> None:
    """Ensure directory exists, create if necessary."""
    path.mkdir(parents=True, exist_ok=True)


def cmd_new(args) -> None:
    """
    Create a new entry scaffold.
    
    Creates directory structure and template files for a new health claim entry.
    """
    # Create entry directory: entries/{domain}/{slug}/{category}/v1
    entry_dir = ROOT / "entries" / args.domain / args.slug / args.category / "v1"
    ensure_directory(entry_dir)
    
    # Create template files
    (entry_dir / "evidence.csv").write_text(TEMPLATE_EVIDENCE, encoding="utf-8")
    (entry_dir / "citations.json").write_text("[]", encoding="utf-8")
    (entry_dir / "prisma_log.csv").write_text(",".join(PRISMA_HEADERS) + "\n", encoding="utf-8")
    
    # Create empty metadata file
    metadata = {
        "entry_id": f"{args.domain}:{args.slug}:{args.category}:v1",
        "created": datetime.now().isoformat(),
        "domain": args.domain,
        "slug": args.slug,
        "category": args.category,
        "version": "v1",
        "status": "draft"
    }
    (entry_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    print(f"✅ Entry scaffold created: {entry_dir}")
    print(f"📝 Next steps:")
    print(f"   1. Edit {entry_dir}/evidence.csv with study data")
    print(f"   2. Update {entry_dir}/prisma_log.csv with search records")
    print(f"   3. Run: vera build {entry_dir.relative_to(ROOT)} --category {args.category}")


def load_evidence_csv(file_path: pathlib.Path) -> List[Dict[str, Any]]:
    """Load and validate evidence CSV file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Evidence file not found: {file_path}")
    
    evidence = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                # Convert numeric fields
                processed_row = dict(row)  # Copy all fields
                processed_row["year"] = int(row["year"])
                processed_row["effect_point"] = float(row["effect_point"])
                processed_row["ci_low"] = float(row["ci_low"])
                processed_row["ci_high"] = float(row["ci_high"])
                processed_row["n_treat"] = int(row["n_treat"])
                processed_row["n_ctrl"] = int(row["n_ctrl"])
                
                evidence.append(processed_row)
            except (ValueError, KeyError) as e:
                raise ValueError(f"Error in evidence.csv row {i}: {e}")
    
    # Validate evidence data
    validation_errors = validate_evidence_data(evidence)
    if validation_errors:
        raise ValueError("Evidence validation failed:\n" + "\n".join(validation_errors))
    
    return evidence


def get_entry_text_hint(domain: str, slug: str, category: str) -> str:
    """Generate text hint for L-gate analysis."""
    return f"{slug.replace('-', ' ')} {category} {domain}"


def cmd_build(args) -> None:
    """
    Build an entry from evidence data.
    
    Processes evidence.csv through the VERA pipeline to generate
    simulation.json and entry.jsonld artifacts.
    """
    # Load policy and compute fingerprint
    policy = load_yaml(ROOT / "policy.yaml")
    policy_fingerprint = compute_policy_fingerprint()
    
    # Resolve entry directory
    if args.path.startswith("/"):
        entry_dir = pathlib.Path(args.path)
    else:
        entry_dir = ROOT / args.path
    
    if not entry_dir.exists():
        print(f"❌ Entry directory not found: {entry_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Load evidence
    try:
        evidence = load_evidence_csv(entry_dir / "evidence.csv")
        print(f"📊 Loaded {len(evidence)} studies from evidence.csv")
    except Exception as e:
        print(f"❌ Error loading evidence: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Load journal snapshot
    try:
        snap_path = ROOT / policy["gates"]["j"]["use_snapshot"]
        journal_snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
        print(f"📚 Loaded journal snapshot: {snap_path.name}")
    except Exception as e:
        print(f"❌ Error loading journal snapshot: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Extract entry metadata from path
    path_parts = entry_dir.parts
    try:
        # Expect: .../entries/domain/slug/category/v1
        domain = path_parts[-4]
        slug = path_parts[-3] 
        category = path_parts[-2]
        version = path_parts[-1]
    except IndexError:
        print(f"❌ Invalid entry path structure: {entry_dir}", file=sys.stderr)
        print("   Expected: entries/domain/slug/category/v1", file=sys.stderr)
        sys.exit(1)
    
    # Validate category matches argument
    if category != args.category:
        print(f"❌ Category mismatch: path={category}, argument={args.category}", file=sys.stderr)
        sys.exit(1)
    
    print(f"🔬 Building entry: {domain}:{slug}:{category}:{version}")
    
    # Evaluate gates
    text_hint = get_entry_text_hint(domain, slug, category)
    gate_results = evaluate_all_gates(evidence, category, journal_snapshot, policy, text_hint)
    
    # Check for early termination conditions
    if gate_results["summary"]["safety_monotonic"]:
        print("⚠️  Safety violations detected - applying monotonic cap")
        P = 0.0
        label = "FAIL"
        tier = "Black"
        
        # Create minimal simulation result
        simulation = {
            "seed": policy["monte_carlo"]["seed"],
            "n_draws": policy["monte_carlo"]["n_draws"],
            "tau2_method": policy["monte_carlo"]["tau2_method"],
            "delta": policy["categories"][category]["delta"],
            "P_effect_gt_delta": P,
            "I2": None,
            "tau2": None,
            "environment": "policy-only (safety violations)",
            "policy_fingerprint": policy_fingerprint,
            "gate_terminated": True
        }
    else:
        # Run Monte Carlo meta-analysis
        print("🎲 Running Monte Carlo meta-analysis...")
        delta = policy["categories"][category]["delta"]
        simulation = run_mc(
            evidence, 
            delta=delta,
            seed=policy["monte_carlo"]["seed"],
            n_draws=policy["monte_carlo"]["n_draws"], 
            tau2_method=policy["monte_carlo"]["tau2_method"]
        )
        simulation["policy_fingerprint"] = policy_fingerprint
        
        P = simulation["P_effect_gt_delta"]
        
        # Determine HBV label
        phi_fail = gate_results["phi"]["violation"]
        k_fail = gate_results["k"]["violation"] 
        label, tier = hbv_label(P, phi_fail, k_fail)
        
        # Apply L-gate penalty
        l_flag = gate_results["l"]["violation"]
        label, tier = apply_l_gate_penalty(label, tier, l_flag)
    
    print(f"🏷️  HBV Result: {tier} ({label}) - P = {P:.3f}")
    
    # Save simulation.json
    sim_file = entry_dir / "simulation.json"
    sim_file.write_text(json.dumps(simulation, indent=2), encoding="utf-8")
    print(f"💾 Saved: {sim_file.name}")
    
    # Create entry.jsonld
    audit_hash = sha256_bytes(
        canonical_json(simulation) + 
        canonical_json({"path": str(entry_dir)})
    )
    
    entry_data = {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "id": f"{domain}:{slug}:{category}:{version}",
        "title": f"{slug.replace('-', ' ').title()} — {category.title()}",
        "category": category,
        "tier": tier,
        "label": label,
        "P_effect_gt_delta": round(P, 3),
        "gate_results": {
            "phi": gate_results["phi"]["result"],
            "r": round(gate_results["r"]["score"], 3),
            "j": round(gate_results["j"]["score_capped"], 3), 
            "k": gate_results["k"]["result"],
            "l": gate_results["l"]["result"]
        },
        "evidence_summary": {
            "n_studies": len(evidence),
            "I2": simulation.get("I2"),
            "tau2": simulation.get("tau2")
        },
        "policy_refs": {
            "policy_version": policy["version"],
            "journal_trust": journal_snapshot["snapshot_date"]
        },
        "version": version,
        "audit_hash": audit_hash,
        "policy_fingerprint": policy_fingerprint,
        "created": datetime.now().isoformat() + "Z"
    }
    
    # Save entry.jsonld
    entry_file = entry_dir / "entry.jsonld" 
    entry_file.write_text(json.dumps(entry_data, indent=2), encoding="utf-8")
    print(f"💾 Saved: {entry_file.name}")
    
    # Append to audit log
    audit_log_path = ROOT / "AUDIT_LOG.jsonl"
    audit_record = {
        "timestamp": datetime.now().isoformat() + "Z",
        "entry_id": entry_data["id"],
        "audit_hash": audit_hash,
        "policy_fingerprint": policy_fingerprint,
        "tier": tier,
        "label": label,
        "P_effect_gt_delta": P
    }
    
    with open(audit_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_record) + "\n")
    
    print(f"📝 Audit log updated: {audit_log_path.name}")
    print(f"✅ Build complete: {entry_data['id']} → {label}/{tier}")


def cmd_fingerprint(args) -> None:
    """Compute and display current policy fingerprint."""
    fingerprint = compute_policy_fingerprint()
    print(fingerprint)


def cmd_validate(args) -> None:
    """Validate entry artifacts against schemas."""
    if args.path.startswith("/"):
        entry_dir = pathlib.Path(args.path)
    else:
        entry_dir = ROOT / args.path
    
    if not entry_dir.exists():
        print(f"❌ Entry directory not found: {entry_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"🔍 Validating artifacts in: {entry_dir}")
    
    try:
        results = validate_all_artifacts(entry_dir)
        
        if results["overall_valid"]:
            print("✅ All validations passed")
        else:
            print("❌ Validation failures detected")
            for artifact, result in results["validations"].items():
                if not result["valid"]:
                    print(f"\n{artifact.upper()} ERRORS:")
                    for error in result["errors"]:
                        path_str = " -> ".join(str(p) for p in error["path"]) if error["path"] else "root"
                        print(f"  {path_str}: {error['message']}")
        
        sys.exit(0 if results["overall_valid"] else 1)
        
    except Exception as e:
        print(f"❌ Validation error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args) -> None:
    """Show status of entries and system."""
    print("VERA Archives Status")
    print("=" * 40)
    
    # Policy info
    policy = load_yaml(ROOT / "policy.yaml")
    print(f"Policy Version: {policy['version']}")
    print(f"Policy Fingerprint: {compute_policy_fingerprint()}")
    
    # Count entries
    entries_dir = ROOT / "entries"
    if entries_dir.exists():
        entry_paths = list(entries_dir.glob("*/*/*/v*/entry.jsonld"))
        print(f"Total Entries: {len(entry_paths)}")
        
        # Count by status
        tier_counts = {}
        for entry_path in entry_paths:
            try:
                entry_data = json.loads(entry_path.read_text())
                tier = entry_data.get("tier", "Unknown")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            except:
                continue
        
        if tier_counts:
            print("\nTier Distribution:")
            for tier in ["Gold", "Silver", "Bronze", "Red", "Black"]:
                count = tier_counts.get(tier, 0)
                print(f"  {tier}: {count}")
    
    # Audit log info
    audit_log = ROOT / "AUDIT_LOG.jsonl"
    if audit_log.exists():
        with open(audit_log) as f:
            lines = f.readlines()
        print(f"\nAudit Log Entries: {len(lines)}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="VERA Protocol CLI - Build and manage health-claim entries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vera new nutrient magnesium-glycinate sleep
  vera build entries/nutrient/magnesium-glycinate/sleep/v1 --category sleep
  vera validate entries/nutrient/magnesium-glycinate/sleep/v1
  vera fingerprint
  vera status
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # New command
    parser_new = subparsers.add_parser("new", help="Create new entry scaffold")
    parser_new.add_argument("domain", help="Domain (e.g., nutrient, herb)")
    parser_new.add_argument("slug", help="Slug (e.g., magnesium-glycinate)")
    parser_new.add_argument("category", help="Category (e.g., sleep, cognition)")
    parser_new.set_defaults(func=cmd_new)
    
    # Build command
    parser_build = subparsers.add_parser("build", help="Build entry from evidence")
    parser_build.add_argument("path", help="Path to entry directory")
    parser_build.add_argument("--category", required=True, help="Evidence category")
    parser_build.set_defaults(func=cmd_build)
    
    # Validate command
    parser_validate = subparsers.add_parser("validate", help="Validate entry artifacts")
    parser_validate.add_argument("path", help="Path to entry directory")
    parser_validate.set_defaults(func=cmd_validate)
    
    # Fingerprint command
    parser_fingerprint = subparsers.add_parser("fingerprint", help="Show policy fingerprint")
    parser_fingerprint.set_defaults(func=cmd_fingerprint)
    
    # Status command
    parser_status = subparsers.add_parser("status", help="Show system status")
    parser_status.set_defaults(func=cmd_status)
    
    # Parse and execute
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()