#!/usr/bin/env python3
"""Utility for selecting catalog entries for batch builds."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


def _normalize_priorities(values: Sequence[str] | None) -> List[str]:
    if not values:
        return []
    return [value.strip().lower() for value in values if value.strip()]


def _matches_category(row_category: str, target: str | None, case_sensitive: bool) -> bool:
    if not target:
        return True
    if not row_category:
        return False
    haystack = row_category if case_sensitive else row_category.lower()
    needle = target if case_sensitive else target.lower()
    return needle in haystack


def _matches_priority(row_priority: str, priorities: Sequence[str]) -> bool:
    if not priorities:
        return True
    if not row_priority:
        return False
    return row_priority.strip().lower() in priorities


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter entries from catalog/entry_catalog.csv for batch workflows.",
    )
    parser.add_argument(
        "--catalog",
        default="catalog/entry_catalog.csv",
        help="Path to the entry catalog CSV (default: %(default)s).",
    )
    parser.add_argument(
        "--category",
        default="sleep",
        help="Substring match against the category column (default: %(default)s).",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Treat category filtering as case-sensitive (default: case-insensitive).",
    )
    parser.add_argument(
        "--priorities",
        nargs="+",
        default=["high", "medium"],
        help="Priority levels to include (default: %(default)s).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Maximum number of entries to emit (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Destination file for the filtered CSV (default: stdout).",
    )
    parser.add_argument(
        "--include-header",
        action="store_true",
        help="Write the CSV header row before the filtered results.",
    )
    return parser.parse_args()


def select_rows(
    rows: Iterable[dict[str, str]],
    *,
    category: str | None,
    priorities: Sequence[str],
    case_sensitive: bool,
    limit: int,
) -> List[dict[str, str]]:
    selected: List[dict[str, str]] = []
    for row in rows:
        if not _matches_category(row.get("category", ""), category, case_sensitive):
            continue
        if not _matches_priority(row.get("priority", ""), priorities):
            continue
        selected.append(row)
        if 0 < limit == len(selected):
            break
    return selected


def main() -> int:
    args = parse_arguments()

    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(f"error: catalog file not found: {catalog_path}", file=sys.stderr)
        return 1

    priorities = _normalize_priorities(args.priorities)

    with catalog_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = select_rows(
            reader,
            category=args.category,
            priorities=priorities,
            case_sensitive=args.case_sensitive,
            limit=args.count,
        )

    if not rows:
        print("warning: no catalog rows matched the provided filters", file=sys.stderr)

    if args.output == "-":
        output_handle = sys.stdout
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_handle = output_path.open("w", newline="", encoding="utf-8")

    try:
        writer = csv.DictWriter(output_handle, fieldnames=fieldnames, lineterminator="\n")
        if args.include_header and fieldnames:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
    finally:
        if output_handle is not sys.stdout:
            output_handle.close()

    print(f"selected {len(rows)} rows", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
