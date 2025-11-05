#!/usr/bin/env python3
"""Rebuild all stub entries with REML method."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def find_stub_entries():
    """Find all entries with stub patterns."""
    stub_entries = []

    for sim_path in ROOT.glob("entries/**/v1/simulation.json"):
        try:
            with open(sim_path) as f:
                data = json.load(f)

            # Check for stub pattern
            if data.get("tau2_method") == "deterministic-stub":
                entry_dir = sim_path.parent
                stub_entries.append(entry_dir)
        except Exception as e:
            print(f"Error reading {sim_path}: {e}", file=sys.stderr)

    return stub_entries

def rebuild_entry(entry_dir):
    """Rebuild a single entry using build_protocol_entry.py."""
    # Default claim text for L-gate analysis
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
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def main():
    print("🔍 Finding stub entries...")
    stub_entries = find_stub_entries()

    print(f"Found {len(stub_entries)} stub entries to rebuild")

    if not stub_entries:
        print("✅ No stub entries found!")
        return 0

    success_count = 0
    fail_count = 0

    for i, entry_dir in enumerate(stub_entries, 1):
        print(f"\n[{i}/{len(stub_entries)}] Rebuilding {entry_dir.relative_to(ROOT)}...", end=" ")

        success, output = rebuild_entry(entry_dir)

        if success:
            print("✅")
            success_count += 1
        else:
            print("❌")
            print(f"  Error: {output[:200]}")
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"{'='*60}")

    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
