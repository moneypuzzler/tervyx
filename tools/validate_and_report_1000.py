#!/usr/bin/env python3
"""Comprehensive validation and reporting for 1,000 entries."""

import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]


def find_all_entries() -> List[Path]:
    """Find all entry directories with entry.jsonld."""
    entries_dir = ROOT / "entries"
    return list(entries_dir.rglob("entry.jsonld"))


def validate_entry(entry_file: Path) -> Tuple[bool, Dict[str, any]]:
    """Validate a single entry and extract key metrics."""
    entry_dir = entry_file.parent

    # Check required files
    required_files = {
        "entry.jsonld": entry_file.exists(),
        "simulation.json": (entry_dir / "simulation.json").exists(),
        "citations.json": (entry_dir / "citations.json").exists(),
        "evidence.csv": (entry_dir / "evidence.csv").exists(),
    }

    if not all(required_files.values()):
        return False, {"error": "Missing files", "missing": [k for k, v in required_files.items() if not v]}

    # Load and validate entry.jsonld
    try:
        with entry_file.open("r", encoding="utf-8") as f:
            entry_data = json.load(f)

        # Check required fields
        required_fields = [
            "@context", "@type", "tier", "label", "P_effect_gt_delta",
            "gate_results", "policy_refs", "version", "policy_fingerprint", "audit_hash"
        ]

        missing_fields = [field for field in required_fields if field not in entry_data]
        if missing_fields:
            return False, {"error": "Missing fields in entry.jsonld", "missing": missing_fields}

        # Load simulation data
        with (entry_dir / "simulation.json").open("r", encoding="utf-8") as f:
            simulation = json.load(f)

        # Extract metrics
        metrics = {
            "entry_id": entry_data.get("identifier", "unknown"),
            "tier": entry_data.get("tier"),
            "label": entry_data.get("label"),
            "P_effect_gt_delta": simulation.get("P_effect_gt_delta"),
            "I2": simulation.get("I2"),
            "n_studies": simulation.get("n_studies"),
            "policy_fingerprint": entry_data.get("policy_fingerprint"),
            "audit_hash": entry_data.get("audit_hash"),
            "category": entry_dir.parent.parent.name,
            "path": str(entry_dir.relative_to(ROOT))
        }

        # Check gate results
        gates = entry_data.get("gate_results", {})
        gate_pass = all(
            gate.get("outcome") in ["pass", "Pass", "PASS"]
            for gate in gates.values()
            if isinstance(gate, dict)
        )

        if not gate_pass:
            return False, {"error": "Gate validation failed", "gates": gates}

        return True, metrics

    except Exception as e:
        return False, {"error": str(e)}


def generate_comprehensive_report(entries: List[Path]) -> Dict:
    """Generate comprehensive validation and metrics report."""
    print(f"\n🔍 Validating {len(entries)} entries...")

    valid_entries = []
    invalid_entries = []
    tier_counts = Counter()
    label_counts = Counter()
    category_counts = Counter()
    policy_fingerprints = Counter()

    for i, entry_file in enumerate(entries):
        is_valid, data = validate_entry(entry_file)

        if is_valid:
            valid_entries.append(data)
            tier_counts[data["tier"]] += 1
            label_counts[data["label"]] += 1
            category_counts[data["category"]] += 1
            if data["policy_fingerprint"]:
                policy_fingerprints[data["policy_fingerprint"]] += 1
        else:
            invalid_entries.append({
                "path": str(entry_file.relative_to(ROOT)),
                "error": data.get("error", "Unknown"),
                "details": data
            })

        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"   Progress: {i + 1}/{len(entries)}")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_entries": len(entries),
            "valid_entries": len(valid_entries),
            "invalid_entries": len(invalid_entries),
            "success_rate": (len(valid_entries) / len(entries) * 100) if entries else 0
        },
        "distributions": {
            "by_tier": dict(tier_counts),
            "by_label": dict(label_counts),
            "by_category": dict(category_counts)
        },
        "policy_compliance": {
            "unique_policy_fingerprints": len(policy_fingerprints),
            "fingerprint_counts": dict(policy_fingerprints)
        },
        "validation_failures": invalid_entries[:20]  # Top 20 failures
    }

    return report


def write_detailed_csv(valid_entries: List[Dict], output_path: Path) -> None:
    """Write detailed entry metrics to CSV."""
    if not valid_entries:
        return

    fieldnames = [
        "entry_id", "category", "tier", "label", "P_effect_gt_delta",
        "I2", "n_studies", "policy_fingerprint", "audit_hash", "path"
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in valid_entries:
            writer.writerow(entry)

    print(f"📄 Detailed CSV: {output_path}")


def run_schema_validation_suite() -> Tuple[int, int]:
    """Run comprehensive schema validation on all entries."""
    print("\n🔍 Running schema validation suite...")

    entries_dir = ROOT / "entries"
    passed = 0
    failed = 0

    for entry_file in entries_dir.rglob("entry.jsonld"):
        entry_dir = entry_file.parent

        cmd = [
            sys.executable,
            str(ROOT / "engine" / "schema_validate.py"),
            str(entry_dir)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)

        if result.returncode == 0:
            passed += 1
        else:
            failed += 1
            if failed <= 10:  # Show first 10 failures
                print(f"❌ {entry_dir.relative_to(ROOT)}: {result.stderr[:100]}")

        if (passed + failed) % 50 == 0:
            print(f"   Progress: {passed + failed} entries validated")

    return passed, failed


def main():
    print("🚀 Starting comprehensive validation and reporting...")

    # Find all entries
    entries = find_all_entries()
    print(f"📊 Found {len(entries)} entries")

    if not entries:
        print("❌ No entries found")
        return 1

    # Generate report
    report = generate_comprehensive_report(entries)

    # Write JSON report
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    json_path = reports_dir / "validation_report_1000.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n📊 Validation Report Summary:")
    print(f"   Total entries: {report['summary']['total_entries']}")
    print(f"   Valid entries: {report['summary']['valid_entries']}")
    print(f"   Invalid entries: {report['summary']['invalid_entries']}")
    print(f"   Success rate: {report['summary']['success_rate']:.1f}%")

    print(f"\n📈 Tier Distribution:")
    for tier, count in sorted(report['distributions']['by_tier'].items()):
        print(f"   {tier}: {count}")

    print(f"\n🏷️  Label Distribution:")
    for label, count in sorted(report['distributions']['by_label'].items()):
        print(f"   {label}: {count}")

    print(f"\n📂 Category Distribution:")
    for category, count in sorted(report['distributions']['by_category'].items()):
        print(f"   {category}: {count}")

    print(f"\n💾 JSON report: {json_path}")

    # Write CSV with valid entries
    valid_entries = [
        entry for entry in report.get("valid_entries_data", [])
        if isinstance(entry, dict)
    ]

    # Re-extract valid entries for CSV
    print("\n📝 Generating detailed CSV...")
    valid_list = []
    for entry_file in entries:
        is_valid, data = validate_entry(entry_file)
        if is_valid:
            valid_list.append(data)

    csv_path = reports_dir / "entry_summary_1000.csv"
    write_detailed_csv(valid_list, csv_path)

    # Run schema validation
    passed, failed = run_schema_validation_suite()
    print(f"\n🔍 Schema Validation Results:")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Pass rate: {(passed / (passed + failed) * 100) if (passed + failed) > 0 else 0:.1f}%")

    # Final status
    if report['summary']['success_rate'] >= 95:
        print("\n✅ Validation PASSED (>= 95% success rate)")
        return 0
    else:
        print("\n⚠️  Validation needs attention (< 95% success rate)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
