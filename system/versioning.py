"""Utilities for managing versioned TERVYX entry directories."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

VERSION_PATTERN = re.compile(r"^v\d+(?:\.\d+)*$")


def slugify(value: str) -> str:
    """Convert arbitrary text into a filesystem-safe slug."""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "entry"


def _parse_version(version: str) -> Tuple[int, ...]:
    if not VERSION_PATTERN.match(version):
        raise ValueError(f"Invalid content version: {version}")
    parts = tuple(int(part) for part in version[1:].split("."))
    if not parts:
        raise ValueError("Content version must include at least one numeric component")
    return parts


def _trim_parts(parts: List[int]) -> List[int]:
    trimmed = list(parts)
    while len(trimmed) > 1 and trimmed[-1] == 0:
        trimmed.pop()
    return trimmed


def _format_version(parts: List[int]) -> str:
    return "v" + ".".join(str(part) for part in parts)


@dataclass(frozen=True)
class VersionResolution:
    """Result of resolving the next content version for an entry."""

    version: str
    previous: Optional[str]


class EntryVersionManager:
    """Manage versioned directories for a single entry."""

    def __init__(self, entry_root: Path) -> None:
        self.entry_root = entry_root

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def list_versions(self) -> List[str]:
        if not self.entry_root.exists():
            return []

        versions: List[str] = []
        for child in self.entry_root.iterdir():
            if child.is_dir() and VERSION_PATTERN.match(child.name):
                versions.append(child.name)

        return sorted(versions, key=_parse_version)

    def latest_version(self) -> Optional[str]:
        versions = self.list_versions()
        return versions[-1] if versions else None

    def version_exists(self, version: str) -> bool:
        return version in self.list_versions()

    # ------------------------------------------------------------------
    # Version resolution
    # ------------------------------------------------------------------
    def resolve_version(
        self,
        explicit: Optional[str],
        bump: Optional[str],
    ) -> VersionResolution:
        existing = self.list_versions()

        if explicit:
            if not VERSION_PATTERN.match(explicit):
                raise ValueError(
                    f"Explicit content version must match pattern 'vN[.N]…' (got {explicit!r})"
                )
            if explicit in existing:
                raise ValueError(f"Content version {explicit} already exists")
            previous = existing[-1] if existing else None
            return VersionResolution(explicit, previous)

        bump_strategy = (bump or "minor").lower()
        if bump_strategy not in {"major", "minor", "patch"}:
            raise ValueError(f"Unsupported bump strategy: {bump_strategy}")

        if not existing:
            return VersionResolution("v1", None)

        latest = existing[-1]
        next_version = self._bump(latest, bump_strategy)
        return VersionResolution(next_version, latest)

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------
    def create_version_dir(self, version: str) -> Path:
        if not VERSION_PATTERN.match(version):
            raise ValueError(f"Invalid content version name: {version}")

        self.entry_root.mkdir(parents=True, exist_ok=True)
        version_path = self.entry_root / version
        version_path.mkdir(exist_ok=False)
        return version_path

    def update_latest_pointer(self, version: str) -> None:
        latest_path = self.entry_root / "latest"
        if latest_path.exists() or latest_path.is_symlink():
            if latest_path.is_symlink() or latest_path.is_file():
                latest_path.unlink()
            else:
                shutil.rmtree(latest_path)

        try:
            latest_path.symlink_to(version, target_is_directory=True)
        except OSError:
            latest_path.write_text(f"{version}\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _bump(self, version: str, strategy: str) -> str:
        parts = list(_parse_version(version))
        while len(parts) < 3:
            parts.append(0)

        if strategy == "major":
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif strategy == "minor":
            parts[1] += 1
            parts[2] = 0
        elif strategy == "patch":
            parts[2] += 1
        else:  # pragma: no cover - guarded earlier
            raise ValueError(f"Unsupported bump strategy: {strategy}")

        trimmed = _trim_parts(parts)
        return _format_version(trimmed)


__all__ = [
    "EntryVersionManager",
    "VersionResolution",
    "slugify",
    "VERSION_PATTERN",
]
