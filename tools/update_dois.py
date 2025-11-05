#!/usr/bin/env python3
"""Update DOIs in evidence.csv files based on a mapping file."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]


def load_doi_mappings(mapping_file: Path) -> Dict[str, List[Dict[str, str]]]:
    """Load DOI mappings from CSV file, grouped by entry_path."""
    mappings: Dict[str, List[Dict[str, str]]] = {}

    with open(mapping_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry_path = row["entry_path"]
            if entry_path not in mappings:
                mappings[entry_path] = []
            mappings[entry_path].append(row)

    return mappings


def update_evidence_csv(evidence_path: Path, mappings: List[Dict[str, str]]) -> bool:
    """Update DOIs in evidence.csv file."""
    if not evidence_path.exists():
        print(f"❌ Evidence file not found: {evidence_path}")
        return False

    # Create mapping dict: study_id -> new_doi
    doi_map = {m["study_id"]: m["new_doi"] for m in mappings}

    # Read existing CSV
    rows = []
    with open(evidence_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            study_id = row["study_id"]
            if study_id in doi_map:
                old_doi = row["doi"]
                new_doi = doi_map[study_id]
                row["doi"] = new_doi
                print(f"  📝 {study_id}: {old_doi} → {new_doi}")
            rows.append(row)

    # Write updated CSV
    with open(evidence_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    return True


def rebuild_entry(entry_dir: Path) -> bool:
    """Rebuild entry using build_protocol_entry.py."""
    substance = entry_dir.parent.parent.name.replace("-", " ")
    category = entry_dir.parent.name.replace("_", " ")
    claim = f"{substance.title()} supplementation improves {category} outcomes"

    cmd = [
        sys.executable,
        str(ROOT / "tools" / "build_protocol_entry.py"),
        str(entry_dir),
        "--claim", claim
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return True
        else:
            print(f"  ❌ Rebuild failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Rebuild error: {str(e)[:200]}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Update DOIs from mapping file")
    parser.add_argument(
        "--mapping",
        type=Path,
        required=True,
        help="CSV file with DOI mappings (entry_path,study_id,old_doi,new_doi,...)"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Automatically rebuild entries after updating DOIs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without actually changing files"
    )
    args = parser.parse_args()

    if not args.mapping.exists():
        print(f"❌ Mapping file not found: {args.mapping}")
        return 1

    print(f"📖 Loading mappings from {args.mapping}")
    mappings = load_doi_mappings(args.mapping)

    print(f"Found {len(mappings)} entries to update")
    print()

    success_count = 0
    fail_count = 0

    for entry_path_str, entry_mappings in mappings.items():
        entry_dir = ROOT / entry_path_str
        evidence_path = entry_dir / "evidence.csv"

        print(f"🔄 {entry_path_str}")

        if args.dry_run:
            for m in entry_mappings:
                print(f"  [DRY-RUN] {m['study_id']}: {m['old_doi']} → {m['new_doi']}")
            print(f"  [DRY-RUN] Would rebuild entry")
            success_count += 1
            continue

        # Update evidence.csv
        if not update_evidence_csv(evidence_path, entry_mappings):
            fail_count += 1
            continue

        # Rebuild if requested
        if args.rebuild:
            print(f"  🔨 Rebuilding...")
            if rebuild_entry(entry_dir):
                print(f"  ✅ Complete")
                success_count += 1
            else:
                print(f"  ❌ Failed to rebuild")
                fail_count += 1
        else:
            print(f"  ✅ DOIs updated (rebuild skipped)")
            success_count += 1

        print()

    print("=" * 60)
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("=" * 60)

    if not args.rebuild:
        print("\nℹ️  Run with --rebuild to automatically rebuild entries")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
