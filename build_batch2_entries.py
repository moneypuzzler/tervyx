#!/usr/bin/env python3
"""Build all batch 2 entries."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ENTRIES = [
    {
        "dir": "entries/nutraceutical/red-yeast-rice-card-redy-statin/cardiovascular/v1",
        "substance": "Red Yeast Rice",
        "outcome": "cholesterol reduction",
    },
    {
        "dir": "entries/nutraceutical/polyphenol-blend-card-poly-res/cardiovascular/v1",
        "substance": "Polyphenol Blend",
        "outcome": "blood pressure reduction",
    },
    {
        "dir": "entries/nutraceutical/vitamin-c-imm-imm03/immune/v1",
        "substance": "Vitamin C",
        "outcome": "cold symptom reduction",
    },
    {
        "dir": "entries/nutraceutical/vitamin-d-imm-imm04/immune/v1",
        "substance": "Vitamin D",
        "outcome": "respiratory infection prevention",
    },
    {
        "dir": "entries/nutraceutical/beta-glucans-imm-imm07/immune/v1",
        "substance": "Beta-Glucans",
        "outcome": "immune function enhancement",
    },
]


def build_entry(entry_spec):
    """Build a single entry using build_protocol_entry.py."""
    entry_dir = ROOT / entry_spec["dir"]
    claim = f"{entry_spec['substance']} supports {entry_spec['outcome']}"

    cmd = [
        sys.executable,
        str(ROOT / "tools" / "build_protocol_entry.py"),
        str(entry_dir),
        "--claim", claim
    ]

    print(f"🔨 Building: {entry_dir.relative_to(ROOT)}")
    print(f"   Claim: {claim}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"   ✅ Success")
            return True, entry_dir
        else:
            print(f"   ❌ Failed: {result.stderr[:200]}")
            return False, None
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:200]}")
        return False, None


def main():
    print("🔨 Building batch 2 entries (5 entries)\n")

    success_count = 0
    fail_count = 0
    built_dirs = []

    for entry_spec in ENTRIES:
        success, entry_dir = build_entry(entry_spec)
        if success:
            success_count += 1
            built_dirs.append(entry_dir)
        else:
            fail_count += 1
        print()

    print("="*60)
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("="*60)

    if built_dirs:
        print("\nBuilt entries:")
        for entry_dir in built_dirs:
            print(f"  - {entry_dir.relative_to(ROOT)}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
