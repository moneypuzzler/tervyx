#!/usr/bin/env python3
"""Parallel build script for 1,000 entries."""

import argparse
import concurrent.futures
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

def load_catalog_entries() -> List[Dict[str, str]]:
    """Load all pending entries from catalog."""
    catalog_path = ROOT / "catalog" / "entry_catalog.csv"
    entries = []

    with catalog_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").strip().lower() in ["pending", "ready", ""]:
                entries.append(row)

    return entries


def build_single_entry(entry_data: Dict[str, str], overwrite: bool = False) -> Tuple[str, bool, str]:
    """Build a single entry using generate_batch_entries.py."""
    entry_id = entry_data.get("entry_id", "unknown")
    category = entry_data.get("category", "unknown")

    try:
        # Use the generate_batch_entries.py script with filters
        cmd = [
            sys.executable,
            str(ROOT / "tools" / "generate_batch_entries.py"),
            "--count", "1",
            "--categories", category,
        ]

        if overwrite:
            cmd.append("--overwrite")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per entry
            cwd=ROOT
        )

        if result.returncode == 0:
            return (entry_id, True, "Success")
        else:
            return (entry_id, False, f"Build failed: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        return (entry_id, False, "Timeout (5 minutes)")
    except Exception as e:
        return (entry_id, False, f"Exception: {str(e)[:200]}")


def build_entries_parallel(
    entries: List[Dict[str, str]],
    max_workers: int = 10,
    overwrite: bool = False,
    limit: int = None
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Build entries in parallel."""
    if limit:
        entries = entries[:limit]

    successes = []
    failures = []

    print(f"🚀 Starting parallel build of {len(entries)} entries with {max_workers} workers...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_entry = {
            executor.submit(build_single_entry, entry, overwrite): entry
            for entry in entries
        }

        # Process results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            entry_id, success, message = future.result()
            completed += 1

            if success:
                successes.append(entry_id)
                print(f"✅ [{completed}/{len(entries)}] {entry_id}: {message}")
            else:
                failures.append((entry_id, message))
                print(f"❌ [{completed}/{len(entries)}] {entry_id}: {message}")

    return successes, failures


def write_build_report(
    successes: List[str],
    failures: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """Write build report to file."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_attempted": len(successes) + len(failures),
        "successes": len(successes),
        "failures": len(failures),
        "success_rate": len(successes) / (len(successes) + len(failures)) * 100 if (len(successes) + len(failures)) > 0 else 0,
        "successful_entries": successes,
        "failed_entries": [{"entry_id": eid, "reason": reason} for eid, reason in failures]
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n📊 Build Report:")
    print(f"   Total attempted: {report['total_attempted']}")
    print(f"   Successes: {report['successes']}")
    print(f"   Failures: {report['failures']}")
    print(f"   Success rate: {report['success_rate']:.1f}%")
    print(f"\n💾 Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build 1,000 entries in parallel")
    parser.add_argument("--workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing entries")
    parser.add_argument("--limit", type=int, help="Limit number of entries to build")
    parser.add_argument("--report", default="reports/build_1000_report.json", help="Output report path")

    args = parser.parse_args()

    # Load catalog
    print("📚 Loading catalog entries...")
    entries = load_catalog_entries()
    print(f"Found {len(entries)} pending entries")

    if not entries:
        print("❌ No pending entries found in catalog")
        return 1

    # Build in parallel
    successes, failures = build_entries_parallel(
        entries,
        max_workers=args.workers,
        overwrite=args.overwrite,
        limit=args.limit
    )

    # Write report
    write_build_report(successes, failures, Path(args.report))

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
