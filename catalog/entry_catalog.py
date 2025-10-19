"""Manual entry catalog loader for the TERVYX protocol."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


CATALOG_FILENAME = "entry_catalog.csv"
DEFAULT_PENDING_STATUSES = {"pending", "ready"}
COMPLETED_STATUSES = {"completed", "archived"}


@dataclass
class CatalogEntry:
    """Representation of a single catalog entry."""

    data: Dict[str, str]

    @property
    def entry_id(self) -> str:
        return self.data.get("entry_id", "").strip()

    @property
    def category(self) -> str:
        return self.data.get("category", "").strip()

    @property
    def priority(self) -> str:
        return self.data.get("priority", "").strip()

    @property
    def evidence_tier(self) -> str:
        return self.data.get("evidence_tier", "").strip()

    @property
    def status(self) -> str:
        return self.data.get("status", "").strip()

    def matches(self, text: str) -> bool:
        """Case-insensitive search across core fields."""

        haystack = " ".join(
            self.data.get(field, "") for field in (
                "entry_id",
                "category",
                "substance",
                "primary_indication",
                "notes",
            )
        ).lower()
        return text.lower() in haystack


class EntryCatalog:
    """Catalog backed by a manually curated CSV file."""

    def __init__(self, catalog_dir: Optional[Path] = None) -> None:
        base_path = Path(catalog_dir) if catalog_dir else Path(__file__).parent
        self.catalog_path = base_path / CATALOG_FILENAME
        if not self.catalog_path.exists():
            raise FileNotFoundError(
                f"Entry catalog CSV not found at {self.catalog_path}. "
                "Create the file before using the catalog."
            )

        self.fieldnames: List[str] = []
        self.entries: List[CatalogEntry] = []
        self._load_entries()

    def _load_entries(self) -> None:
        with self.catalog_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.fieldnames = reader.fieldnames or []
            self.entries = [CatalogEntry(row) for row in reader]

    def _write_entries(self) -> None:
        if not self.fieldnames:
            return
        with self.catalog_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
            for entry in self.entries:
                writer.writerow(entry.data)

    def reload(self) -> None:
        """Refresh entries from disk."""

        self._load_entries()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_catalog_statistics(self) -> Dict[str, Dict[str, float]]:
        total_entries = len(self.entries)
        category_counts = Counter(entry.category for entry in self.entries if entry.category)
        priority_counts = Counter(entry.priority for entry in self.entries if entry.priority)
        status_counts = Counter(entry.status for entry in self.entries if entry.status)

        completed = sum(status_counts.get(status, 0) for status in COMPLETED_STATUSES)
        completion_rate = (completed / total_entries * 100.0) if total_entries else 0.0

        completion_by_category: Dict[str, Dict[str, float]] = {}
        for category in sorted(category_counts):
            category_entries = [entry for entry in self.entries if entry.category == category]
            cat_total = len(category_entries)
            cat_completed = sum(
                1 for entry in category_entries if entry.status in COMPLETED_STATUSES
            )
            completion_by_category[category] = {
                "total": cat_total,
                "completed": cat_completed,
                "rate": (cat_completed / cat_total * 100.0) if cat_total else 0.0,
            }

        pending_high_priority = sum(
            1
            for entry in self.entries
            if entry.priority.lower() == "high" and entry.status in DEFAULT_PENDING_STATUSES
        )

        return {
            "summary": {
                "total_entries": total_entries,
                "completion_rate": completion_rate,
            },
            "categories": {
                "breakdown": dict(category_counts),
                "completion_by_category": completion_by_category,
            },
            "priorities": dict(priority_counts),
            "statuses": dict(status_counts),
            "progress": {
                "pending_high_priority": pending_high_priority,
            },
        }

    def get_next_batch(
        self,
        batch_size: int = 10,
        priority: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        filtered: Iterable[CatalogEntry] = (
            entry
            for entry in self.entries
            if entry.status in DEFAULT_PENDING_STATUSES
        )

        if priority:
            normalized = priority.strip().lower()
            if normalized in {"high", "medium", "low"}:
                filtered = (
                    entry for entry in filtered if entry.priority.lower() == normalized
                )
            elif normalized in {"p0", "p1", "p2", "p3", "p4"}:
                filtered = (
                    entry
                    for entry in filtered
                    if entry.evidence_tier.lower() == normalized
                )
            else:
                filtered = (
                    entry
                    for entry in filtered
                    if entry.priority.lower() == normalized
                    or entry.evidence_tier.lower() == normalized
                )
        if category:
            filtered = (entry for entry in filtered if entry.category.lower() == category.lower())

        batch: List[Dict[str, str]] = []
        for entry in filtered:
            batch.append(entry.data)
            if len(batch) >= batch_size:
                break
        return batch

    def export_entries(self, entries: List[Dict[str, str]], output_file: str) -> None:
        if not entries:
            return
        fieldnames = self.fieldnames or list(entries[0].keys())
        with Path(output_file).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in entries:
                writer.writerow(entry)

    def search_entries(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        for entry in self.entries:
            if entry.matches(query):
                results.append(entry.data)
            if len(results) >= limit:
                break
        return results

    def update_entry_status(
        self,
        entry_id: str,
        status: str,
        *,
        assignee: Optional[str] = None,
        final_tier: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        updated = False
        timestamp = datetime.utcnow().isoformat()

        for entry in self.entries:
            if entry.entry_id == entry_id:
                entry.data["status"] = status
                if assignee is not None:
                    entry.data["assignee"] = assignee
                if final_tier is not None:
                    entry.data["final_tier"] = final_tier
                if notes is not None and notes.strip():
                    existing_notes = entry.data.get("notes", "").strip()
                    entry.data["notes"] = (
                        f"{existing_notes}\n{notes.strip()}" if existing_notes else notes.strip()
                    )
                entry.data["last_updated"] = timestamp
                updated = True
                break

        if updated:
            self._write_entries()
        return updated


__all__ = ["EntryCatalog", "CatalogEntry"]
