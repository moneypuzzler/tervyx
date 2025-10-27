#!/usr/bin/env python3
"""Normalize policy_fingerprint across all entries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

EXPECTED = "0xbe3a798944b1c64b"
ROOT = Path(__file__).resolve().parents[1]


def canonical_bytes(data: Dict[str, object]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def manifest_hash(payload: Dict[str, object]) -> str:
    content = dict(payload)
    content.pop("manifest_hash", None)
    return "sha256:" + hashlib.sha256(canonical_bytes(content)).hexdigest()


def update_entry(entry_dir: Path) -> bool:
    entry_path = entry_dir / "entry.jsonld"
    simulation_path = entry_dir / "simulation.json"
    citations_path = entry_dir / "citations.json"
    if not entry_path.exists() or not simulation_path.exists() or not citations_path.exists():
        return False

    entry_data = json.loads(entry_path.read_text(encoding="utf-8"))
    if entry_data.get("policy_fingerprint") == EXPECTED:
        return False

    simulation_data = json.loads(simulation_path.read_text(encoding="utf-8"))
    citations_data = json.loads(citations_path.read_text(encoding="utf-8"))

    entry_data["policy_fingerprint"] = EXPECTED
    simulation_data["policy_fingerprint"] = EXPECTED
    citations_data["policy_fingerprint"] = EXPECTED

    citations_data["manifest_hash"] = manifest_hash(citations_data)
    entry_data["citations_manifest_hash"] = citations_data["manifest_hash"]

    payload = {key: value for key, value in entry_data.items() if key != "audit_hash"}
    digest = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    entry_data["audit_hash"] = f"0x{digest[:16]}"

    entry_path.write_text(json.dumps(entry_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    simulation_path.write_text(json.dumps(simulation_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    citations_path.write_text(json.dumps(citations_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> int:
    updated = 0
    for entry_path in ROOT.rglob("entry.jsonld"):
        if update_entry(entry_path.parent):
            updated += 1
    print(f"Updated {updated} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
