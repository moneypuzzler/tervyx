#!/usr/bin/env python3
"""Complete pipeline to build 1,000 entries with parallel execution."""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

CATEGORIES = [
    "sleep", "cognition", "mental_health", "cardiovascular", "metabolic",
    "inflammation", "longevity", "musculoskeletal", "immune", "endocrine"
]


def run_command(cmd: List[str], category: str, timeout: int = 600) -> Tuple[str, bool, str]:
    """Run a command and return result."""
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=ROOT
        )
        elapsed = time.time() - start_time

        if result.returncode == 0:
            return (category, True, f"Success in {elapsed:.1f}s")
        else:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            return (category, False, f"Failed: {error_msg}")

    except subprocess.TimeoutExpired:
        return (category, False, f"Timeout after {timeout}s")
    except Exception as e:
        return (category, False, f"Exception: {str(e)}")


def expand_catalog(target_count: int = 1000) -> bool:
    """Expand catalog to target count."""
    print(f"\n📝 Step 1: Expanding catalog to {target_count} entries...")

    cmd = [sys.executable, str(ROOT / "tools" / "expand_catalog_to_1000.py")]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ Failed to expand catalog: {result.stderr}")
        return False


def build_entries_by_category(
    categories: List[str],
    count_per_category: int,
    max_workers: int = 5,
    overwrite: bool = False
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Build entries in parallel by category."""
    print(f"\n🚀 Step 2: Building entries (max {max_workers} parallel categories)...")

    successes = []
    failures = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_category = {}

        for category in categories:
            cmd = [
                sys.executable,
                str(ROOT / "tools" / "generate_batch_entries.py"),
                "--count", str(count_per_category),
                "--categories", category,
                "--log", f"reports/generated_{category}_entries.csv"
            ]

            if overwrite:
                cmd.append("--overwrite")

            future = executor.submit(run_command, cmd, category)
            future_to_category[future] = category

        # Process results
        completed = 0
        total = len(categories)

        for future in as_completed(future_to_category):
            category, success, message = future.result()
            completed += 1

            if success:
                successes.append(category)
                print(f"✅ [{completed}/{total}] {category}: {message}")
            else:
                failures.append((category, message))
                print(f"❌ [{completed}/{total}] {category}: {message}")

    return successes, failures


def validate_all_entries() -> Tuple[int, int]:
    """Validate all entry artifacts."""
    print("\n🔍 Step 3: Validating all entry artifacts...")

    entries_dir = ROOT / "entries"
    total_validated = 0
    total_failed = 0

    # Find all entry.jsonld files
    entry_files = list(entries_dir.rglob("entry.jsonld"))
    print(f"Found {len(entry_files)} entries to validate")

    for entry_file in entry_files:
        entry_dir = entry_file.parent

        # Check for required files
        required_files = ["entry.jsonld", "simulation.json", "citations.json", "evidence.csv"]
        has_all = all((entry_dir / f).exists() for f in required_files)

        if has_all:
            # Run schema validation
            cmd = [
                sys.executable,
                str(ROOT / "engine" / "schema_validate.py"),
                str(entry_dir)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)

            if result.returncode == 0:
                total_validated += 1
            else:
                total_failed += 1
                print(f"⚠️  Validation failed: {entry_dir.relative_to(ROOT)}")
        else:
            total_failed += 1
            print(f"⚠️  Missing files: {entry_dir.relative_to(ROOT)}")

        # Progress indicator
        if (total_validated + total_failed) % 50 == 0:
            print(f"   Progress: {total_validated + total_failed}/{len(entry_files)}")

    return total_validated, total_failed


def generate_reports() -> None:
    """Generate summary reports."""
    print("\n📊 Step 4: Generating reports...")

    entries_dir = ROOT / "entries"
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Count entries by tier
    tier_counts = {}
    label_counts = {}
    category_counts = {}

    entry_files = list(entries_dir.rglob("entry.jsonld"))

    for entry_file in entry_files:
        try:
            with entry_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            tier = data.get("tier", "unknown")
            label = data.get("label", "unknown")
            category = entry_file.parent.parent.name

            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            label_counts[label] = label_counts.get(label, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1

        except Exception:
            continue

    # Write summary report
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entry_files),
        "tier_distribution": tier_counts,
        "label_distribution": label_counts,
        "category_distribution": category_counts
    }

    summary_path = reports_dir / "entry_summary_1000.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Summary report: {summary_path}")
    print(f"\n📈 Statistics:")
    print(f"   Total entries: {summary['total_entries']}")
    print(f"   Tier distribution: {tier_counts}")
    print(f"   Label distribution: {label_counts}")


def main():
    parser = argparse.ArgumentParser(description="Complete 1,000 entry build pipeline")
    parser.add_argument("--workers", type=int, default=5, help="Parallel category workers")
    parser.add_argument("--count-per-category", type=int, default=100, help="Entries per category")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing entries")
    parser.add_argument("--skip-expand", action="store_true", help="Skip catalog expansion")
    parser.add_argument("--skip-build", action="store_true", help="Skip entry building")
    parser.add_argument("--skip-validate", action="store_true", help="Skip validation")

    args = parser.parse_args()

    start_time = time.time()

    # Step 1: Expand catalog
    if not args.skip_expand:
        if not expand_catalog():
            print("❌ Pipeline failed at catalog expansion")
            return 1

    # Step 2: Build entries
    if not args.skip_build:
        successes, failures = build_entries_by_category(
            CATEGORIES,
            args.count_per_category,
            max_workers=args.workers,
            overwrite=args.overwrite
        )

        if failures:
            print(f"\n⚠️  {len(failures)} categories failed to build:")
            for category, message in failures:
                print(f"   - {category}: {message}")

    # Step 3: Validate
    if not args.skip_validate:
        validated, failed = validate_all_entries()
        print(f"\n✅ Validation complete: {validated} passed, {failed} failed")

        if failed > validated * 0.1:  # More than 10% failure rate
            print("❌ High validation failure rate")
            return 1

    # Step 4: Reports
    generate_reports()

    elapsed = time.time() - start_time
    print(f"\n🎉 Pipeline complete in {elapsed:.1f}s ({elapsed/60:.1f} minutes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
