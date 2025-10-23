"""Utilities for loading Journal-Trust Oracle snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT_DIR / "protocol" / "journal_trust" / "snapshot-2025-10-05.json"


def load_snapshot(path: Path | None = None) -> Dict[str, Any]:
    """Load a journal trust snapshot from disk."""

    snapshot_path = path or DEFAULT_SNAPSHOT
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if "snapshot_date" not in data or "snapshot_hash" not in data:
        raise ValueError(f"Snapshot missing required metadata: {snapshot_path}")
    if "journals" not in data or not isinstance(data["journals"], dict):
        raise ValueError(f"Snapshot missing journals mapping: {snapshot_path}")
    return data


def snapshot_hash(snapshot: Dict[str, Any]) -> str:
    """Return the recorded SHA256 hash for auditing."""

    digest = snapshot.get("snapshot_hash")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise ValueError("Snapshot hash not recorded or invalid")
    return digest
