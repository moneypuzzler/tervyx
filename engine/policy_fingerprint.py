"""Deterministic policy fingerprint computation for TEL-5."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .journal_trust import load_snapshot, snapshot_hash

ROOT_DIR = Path(__file__).resolve().parents[1]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        digest.update(handle.read())
    return digest.hexdigest()


@dataclass(frozen=True)
class PolicyFingerprint:
    compact: str
    full: str
    components: Dict[str, Any]


def compute_policy_fingerprint(overrides: Optional[Dict[str, Any]] = None) -> PolicyFingerprint:
    policy_path = ROOT_DIR / "policy.yaml"
    policy_data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))

    snapshot = load_snapshot()

    components: Dict[str, Any] = {
        "policy_version": policy_data.get("version"),
        "protocol": policy_data.get("protocol"),
        "tier_system": policy_data.get("tier_system"),
        "gate_sequence": policy_data.get("gates", {}).get("sequence"),
        "delta_map": {
            name: details.get("delta")
            for name, details in (policy_data.get("categories") or {}).items()
        },
        "monte_carlo": policy_data.get("monte_carlo"),
        "journal_trust_snapshot_hash": snapshot_hash(snapshot),
        "phi_ruleset_hash": _hash_file(ROOT_DIR / "protocol" / "phi_rules.yaml"),
        "l_gate_ruleset_hash": _hash_file(ROOT_DIR / "protocol" / "L_rules.yaml"),
    }

    if overrides:
        components.update(overrides)

    digest = hashlib.sha256(
        json.dumps(components, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return PolicyFingerprint(compact=f"0x{digest[:16]}", full=digest, components=components)
