#!/usr/bin/env python3
"""Verify determinism and ordering constraints for citations manifests."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.citations import compute_manifest_hash


def load_manifest(path: pathlib.Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Citations manifest must be a JSON object")
    return data


def check_sorted(sequence: list, description: str, key_func) -> None:
    ordered = sorted(sequence, key=key_func)
    if sequence != ordered:
        raise SystemExit(f"{description} must be sorted deterministically")


def check_manifest(path: pathlib.Path) -> None:
    manifest = load_manifest(path)

    stored_hash = manifest.get("manifest_hash")
    if not stored_hash:
        raise SystemExit("manifest_hash missing from citations manifest")

    computed_hash = compute_manifest_hash(manifest)
    if stored_hash != computed_hash:
        raise SystemExit(
            "Manifest hash mismatch: "
            f"stored={stored_hash} computed={computed_hash}"
        )

    studies = manifest.get("studies", [])
    if not isinstance(studies, list):
        raise SystemExit("studies field must be a list")

    check_sorted(studies, "Studies", lambda item: item.get("study_id", "").lower())

    references = manifest.get("references", [])
    if not isinstance(references, list):
        raise SystemExit("references field must be a list")

    check_sorted(references, "References", lambda item: (item.get("type", ""), item.get("identifier", "")))

    for index, reference in enumerate(references):
        study_ids = reference.get("study_ids", [])
        if study_ids != sorted(study_ids):
            raise SystemExit(
                f"Reference #{index} study_ids must be sorted deterministically"
            )

    print(f"✅ Citations manifest verified: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check determinism of citations manifest")
    parser.add_argument("manifest", type=pathlib.Path, help="Path to citations.json")
    args = parser.parse_args()

    check_manifest(args.manifest.resolve())


if __name__ == "__main__":
    main()
