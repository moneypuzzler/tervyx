"""Centralised runtime configuration for the TERVYX toolchain."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import pathlib
import sys
from typing import Iterable, Iterator, Optional


def _iter_unique_paths(paths: Iterable[pathlib.Path]) -> Iterator[pathlib.Path]:
    """Yield existing paths while preserving order and removing duplicates."""

    seen = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        if resolved.exists():
            seen.add(resolved)
            yield resolved


def _detect_project_root() -> pathlib.Path:
    """Return the repository root based on this file's location."""

    env_root = os.getenv("TERVYX_ROOT")
    if env_root:
        return pathlib.Path(env_root).resolve()
    return pathlib.Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Resolved filesystem locations used across the project."""

    root: pathlib.Path = field(default_factory=_detect_project_root)
    engine_path: pathlib.Path = field(init=False)
    entries_path: pathlib.Path = field(init=False)
    snapshots_path: pathlib.Path = field(init=False)
    policy_path: pathlib.Path = field(init=False)
    audit_log_path: pathlib.Path = field(init=False)

    def __post_init__(self) -> None:  # pragma: no cover - trivial setters
        object.__setattr__(self, "engine_path", self.root / "engine")
        object.__setattr__(self, "entries_path", self.root / "entries")
        object.__setattr__(self, "snapshots_path", self.root / "snapshots")
        object.__setattr__(self, "policy_path", self.root / "policy.yaml")
        object.__setattr__(self, "audit_log_path", self.root / "AUDIT_LOG.jsonl")

    def ensure_runtime_paths(self) -> None:
        """Inject core module locations into ``sys.path`` for scripts."""

        ensure_paths_on_sys_path((self.root, self.engine_path))


def ensure_paths_on_sys_path(paths: Optional[Iterable[pathlib.Path]] = None) -> None:
    """Ensure the provided paths are present on ``sys.path``."""

    to_register = paths if paths is not None else (settings.root, settings.engine_path)
    for path in _iter_unique_paths(to_register):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


settings = Settings()
