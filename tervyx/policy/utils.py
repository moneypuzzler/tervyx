"""Helpers for interacting with ``policy.yaml`` and related artifacts."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Dict, NamedTuple, Optional

import yaml

from engine.journal_trust import load_snapshot as engine_load_snapshot
from engine.policy_fingerprint import compute_policy_fingerprint as engine_compute_policy_fingerprint

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
        return engine_load_snapshot()

    snapshot_path = (settings.root / relative_path).resolve()
    if not snapshot_path.exists():
        raise PolicyError(
            f"Journal snapshot referenced in policy not found: {snapshot_path}"
        )
    return engine_load_snapshot(snapshot_path)


def compute_policy_fingerprint(policy: Optional[Dict[str, Any]] = None) -> Fingerprint:
    if policy is None:
        fp = engine_compute_policy_fingerprint()
        return Fingerprint(compact=fp.compact, full=fp.full)

    overrides = {
        "policy_version": policy.get("version"),
        "protocol": policy.get("protocol"),
        "tier_system": policy.get("tier_system"),
        "gate_sequence": policy.get("gates", {}).get("sequence"),
        "delta_map": {
            name: details.get("delta")
            for name, details in (policy.get("categories") or {}).items()
        },
        "monte_carlo": policy.get("monte_carlo"),
    }

    gates_cfg = policy.get("gates", {})
    j_cfg = gates_cfg.get("j", {})
    snapshot_rel = j_cfg.get("use_snapshot")
    snapshot_data = load_journal_snapshot(snapshot_rel)
    overrides["journal_trust_snapshot_hash"] = snapshot_data.get("snapshot_hash")

    fp = engine_compute_policy_fingerprint(overrides=overrides)
    return Fingerprint(compact=fp.compact, full=fp.full)
