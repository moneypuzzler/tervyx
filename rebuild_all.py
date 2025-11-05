#!/usr/bin/env python3
"""Rebuild ALL entries to update policy fingerprint."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def find_all_entries():
    """Find all entry directories."""
    entries = []
    for entry_path in ROOT.glob("entries/**/v1/entry.jsonld"):
        entries.append(entry_path.parent)
    return sorted(entries)

def rebuild_entry(entry_dir):
    """Rebuild a single entry using build_protocol_entry.py."""
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
    print("🔍 Finding all entries...")
    entries = find_all_entries()

    print(f"Found {len(entries)} entries to rebuild")

    success_count = 0
    fail_count = 0

    for i, entry_dir in enumerate(entries, 1):
        print(f"[{i}/{len(entries)}] {entry_dir.relative_to(ROOT)}...", end=" ")

        success, output = rebuild_entry(entry_dir)

        if success:
            print("✅")
            success_count += 1
        else:
            print("❌")
            print(f"  Error: {output[:300]}")
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"{'='*60}")

    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
