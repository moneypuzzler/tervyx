#!/usr/bin/env python3
"""Extract substance-category-outcome requirements from all entries."""

import csv
import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]


def extract_entry_info(evidence_path: Path) -> Dict:
    """Extract info from evidence.csv file."""
    with open(evidence_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        if not rows:
            return None

        # Get first row for metadata
        first_row = rows[0]

        # Parse path to extract substance and category
        parts = evidence_path.parts
        # entries/category_domain/substance-id/category/v1/evidence.csv
        substance_id = parts[-5]  # e.g., "magnesium-slp-mag-core"
        category = parts[-3]      # e.g., "sleep"
        domain = parts[-6]        # e.g., "behavioral"

        # Extract clean substance name
        # substance_id format: "magnesium-slp-mag-core" or "5htp-slp-fhtp-serotonin"
        # substance is the main ingredient
        parts_id = substance_id.split('-')

        # Handle complex names: find where the category code starts (slp, imm, etc)
        category_codes = ['slp', 'imm', 'infl', 'long', 'musc', 'card', 'met', 'cog', 'ment', 'ren']
        substance_parts = []
        for part in parts_id:
            if part in category_codes:
                break
            substance_parts.append(part)

        substance = '-'.join(substance_parts) if substance_parts else parts_id[0]

        outcome = first_row.get("outcome", "unknown")
        population = first_row.get("population", "unknown")

        return {
            "substance": substance,
            "substance_id": substance_id,
            "category": category,
            "domain": domain,
            "outcome": outcome,
            "population": population,
            "n_studies": len(rows),
            "entry_path": str(evidence_path.parent.relative_to(ROOT)),
            "years": [row["year"] for row in rows],
        }


def main():
    print("🔍 Extracting all entry requirements...\n")

    entries = []
    evidence_files = sorted(ROOT.glob("entries/**/evidence.csv"))

    for evidence_path in evidence_files:
        info = extract_entry_info(evidence_path)
        if info:
            entries.append(info)

    # Group by substance
    by_substance: Dict[str, List[Dict]] = {}
    for entry in entries:
        substance = entry["substance"]
        if substance not in by_substance:
            by_substance[substance] = []
        by_substance[substance].append(entry)

    # Print summary
    print(f"📊 Found {len(entries)} entries using {len(by_substance)} unique substances\n")

    print("=" * 80)
    print("SUBSTANCE USAGE ANALYSIS")
    print("=" * 80)

    for substance, substance_entries in sorted(by_substance.items()):
        categories = set(e["category"] for e in substance_entries)
        print(f"\n{substance.upper()} ({len(substance_entries)} entries)")
        print("-" * 40)
        for entry in substance_entries:
            print(f"  • {entry['category']:20s} → {entry['outcome']:30s}")
            print(f"    Path: {entry['entry_path']}")

    # Save as CSV
    output_csv = ROOT / "entry_requirements.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["substance", "substance_id", "category", "domain", "outcome",
                     "population", "n_studies", "entry_path", "needs_real_dois"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            entry["needs_real_dois"] = "yes"  # All need real DOIs
            writer.writerow({k: entry[k] for k in fieldnames})

    print(f"\n\n✅ Saved to: {output_csv}")

    # Save as JSON for detailed analysis
    output_json = ROOT / "entry_requirements.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    print(f"✅ Detailed JSON: {output_json}")


if __name__ == "__main__":
    main()
