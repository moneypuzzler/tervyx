"""Helpers for interacting with ``policy.yaml`` and related artifacts."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Dict, NamedTuple, Optional

import yaml

from ..core import settings


class Fingerprint(NamedTuple):
    """Reproducibility fingerprint derived from ``policy.yaml``."""

    compact: str
    full: str


class PolicyError(RuntimeError):
    """Raised when policy data cannot be loaded or validated."""


def _load_yaml(path: pathlib.Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PolicyError("Policy file must contain a mapping at the top level")
    return data


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compact_hex(full_digest: str, length: int = 16) -> str:
    return f"0x{full_digest[:length]}"


def read_policy(path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    policy_path = path or settings.policy_path
    if not policy_path.exists():
        raise PolicyError(f"policy.yaml not found at {policy_path}")
    return _load_yaml(policy_path)


def load_journal_snapshot(relative_path: Optional[str]) -> Dict[str, Any]:
    if not relative_path:
        return {}

    snapshot_path = (settings.root / relative_path).resolve()
    if not snapshot_path.exists():
        raise PolicyError(
            f"Journal snapshot referenced in policy not found: {snapshot_path}"
        )
    snapshot_data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot_data, dict):
        raise PolicyError("Snapshot file must contain a JSON object")
    return snapshot_data


def compute_policy_fingerprint(policy: Optional[Dict[str, Any]] = None) -> Fingerprint:
    policy_data = policy or read_policy()

    gates_cfg = policy_data.get("gates", {})
    j_cfg = gates_cfg.get("j", {})
    snapshot_rel = j_cfg.get("use_snapshot")

    snapshot_data = load_journal_snapshot(snapshot_rel)

    minimal_policy = {
        "version": policy_data.get("version"),
        "protocol": policy_data.get("protocol"),
        "tel5_tiers": policy_data.get("tel5_tiers"),
        "categories": policy_data.get("categories"),
        "gates": {
            "sequence": gates_cfg.get("sequence"),
            "phi": gates_cfg.get("phi"),
            "r": {"threshold": gates_cfg.get("r", {}).get("threshold")},
            "j": {
                "threshold": j_cfg.get("threshold"),
                "use_snapshot": snapshot_rel,
                "weights": j_cfg.get("weights"),
            },
            "k": gates_cfg.get("k"),
            "l": gates_cfg.get("l", {}).get("patterns"),
        },
        "monte_carlo": policy_data.get("monte_carlo"),
    }

    policy_hash = sha256_digest(canonical_json(minimal_policy))
    snapshot_hash = sha256_digest(canonical_json(snapshot_data.get("journals", {})))
    combined = sha256_digest(f"{policy_hash}{snapshot_hash}".encode("utf-8"))
    return Fingerprint(compact=compact_hex(combined), full=combined)
