#!/usr/bin/env python3
"""Validate generated entry artifacts in deterministic shards."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

EXPECTED_POLICY_REFS = {
    "tel5_levels": "v1.2.0",
    "monte_carlo": "v1.0.1-reml-grid",
    "journal_trust": "2025-10-05",
}
EXPECTED_POLICY_FINGERPRINT = "0xbe3a798944b1c64b"

ROOT = Path(__file__).resolve().parents[1]


def iter_entry_dirs(root: Path) -> List[Path]:
    return sorted(path.parent for path in root.rglob("entry.jsonld"))


def select_shard(paths: Iterable[Path], shard_index: int, shard_count: int) -> List[Path]:
    selected: List[Path] = []
    for idx, path in enumerate(sorted(paths)):
        if shard_count <= 0:
            selected.append(path)
        elif idx % shard_count == shard_index:
            selected.append(path)
    return selected


def validate_entry(entry_dir: Path) -> None:
    entry_path = entry_dir / "entry.jsonld"
    simulation_path = entry_dir / "simulation.json"
    citations_path = entry_dir / "citations.json"
    evidence_path = entry_dir / "evidence.csv"

    if not entry_path.exists() or not simulation_path.exists() or not citations_path.exists():
        raise RuntimeError(f"Missing artifact in {entry_dir}")

    entry_data = json.loads(entry_path.read_text(encoding="utf-8"))
    sim_data = json.loads(simulation_path.read_text(encoding="utf-8"))
    citations_data = json.loads(citations_path.read_text(encoding="utf-8"))

    policy_refs = entry_data.get("policy_refs", {})
    for key, expected in EXPECTED_POLICY_REFS.items():
        if policy_refs.get(key) != expected:
            raise AssertionError(f"{entry_path}: policy_refs[{key!r}] != {expected!r}")

    if entry_data.get("policy_fingerprint") != EXPECTED_POLICY_FINGERPRINT:
        raise AssertionError(f"{entry_path}: unexpected policy_fingerprint")

    if sim_data.get("policy_fingerprint") != EXPECTED_POLICY_FINGERPRINT:
        raise AssertionError(f"{simulation_path}: unexpected policy_fingerprint")

    if citations_data.get("policy_fingerprint") != EXPECTED_POLICY_FINGERPRINT:
        raise AssertionError(f"{citations_path}: unexpected policy_fingerprint")

    manifest_entry = entry_data.get("citations_manifest_hash")
    manifest_citations = citations_data.get("manifest_hash")
    if manifest_entry != manifest_citations:
        raise AssertionError(
            f"{entry_path}: citations_manifest_hash {manifest_entry} != citations manifest {manifest_citations}"
        )

    source_evidence = citations_data.get("source_evidence")
    if source_evidence:
        evidence_full = ROOT / source_evidence
        if not evidence_full.exists():
            raise AssertionError(f"Evidence CSV missing: {evidence_full}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate entry artifacts for a shard")
    parser.add_argument("--shard-index", type=int, default=0, help="Shard index (0-based)")
    parser.add_argument("--shard-count", type=int, default=1, help="Total number of shards")
    args = parser.parse_args()

    if args.shard_index < 0 or args.shard_count <= 0 or args.shard_index >= args.shard_count:
        print("error: shard-index must be in [0, shard-count)", file=sys.stderr)
        return 1

    entry_dirs = iter_entry_dirs(ROOT / "entries")
    shard_dirs = select_shard(entry_dirs, args.shard_index, args.shard_count)

    for entry_dir in shard_dirs:
        validate_entry(entry_dir)

    print(f"✅ shard {args.shard_index + 1}/{args.shard_count}: validated {len(shard_dirs)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
