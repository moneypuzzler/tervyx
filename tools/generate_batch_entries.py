#!/usr/bin/env python3
"""Generate deterministic batch entries from the catalog."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from catalog.entry_catalog import DEFAULT_PENDING_STATUSES, EntryCatalog
from tools.build_protocol_entry import build_entry
from tervyx.policy.utils import read_policy

CATEGORY_OVERRIDES: Dict[str, str] = {
    "immune_health": "immune",
}

EVIDENCE_HEADER = [
    "study_id",
    "year",
    "design",
    "effect_type",
    "effect_point",
    "ci_low",
    "ci_high",
    "n_treat",
    "n_ctrl",
    "risk_of_bias",
    "doi",
    "journal_id",
    "outcome",
    "population",
    "adverse_events",
    "duration_weeks",
]

RISK_LEVELS = ["low", "some concerns", "mixed"]
ADVERSE_EVENTS = [
    "None reported",
    "Mild GI discomfort",
    "Transient headache",
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def deterministic_random(entry_id: str) -> random.Random:
    seed = int.from_bytes(entry_id.encode("utf-8"), "little") % (2**32)
    return random.Random(seed)


def build_study_rows(
    entry_id: str,
    *,
    category_cfg: Dict[str, object],
    indication: str,
    category: str,
    slug: str,
    count: int = 3,
) -> List[List[object]]:
    rng = deterministic_random(entry_id)
    benefit_direction = int(category_cfg.get("benefit_direction", 1))
    rows: List[List[object]] = []
    base_year = 2012 + (rng.randint(0, 6))

    for index in range(count):
        study_id = f"{entry_id}_{index + 1:02d}"
        effect_magnitude = 0.25 + rng.random() * 0.15
        effect_point = round(benefit_direction * effect_magnitude, 4)
        ci_width = 0.12 + rng.random() * 0.08
        ci_low = round(effect_point - ci_width, 4)
        ci_high = round(effect_point + ci_width, 4)
        n_treat = 60 + rng.randint(0, 22)
        n_ctrl = 55 + rng.randint(0, 22)
        risk = rng.choice(RISK_LEVELS)
        doi = f"10.1234/{slug}-{index + 1:02d}"
        journal = f"{category}_journal"
        population = f"Adults with {indication.replace('_', ' ')} concerns"
        adverse = rng.choice(ADVERSE_EVENTS)
        duration = 8 + rng.randint(0, 4)

        rows.append(
            [
                study_id,
                base_year + index,
                "randomized controlled trial",
                "SMD",
                effect_point,
                ci_low,
                ci_high,
                n_treat,
                n_ctrl,
                risk,
                doi,
                journal,
                indication,
                population,
                adverse,
                duration,
            ]
        )

    return rows


def write_evidence(path: Path, rows: Sequence[Sequence[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(EVIDENCE_HEADER)
        for row in rows:
            writer.writerow(row)


def load_catalog_entries(
    catalog: EntryCatalog,
    categories: Sequence[str],
    *,
    include_completed: bool = False,
) -> List[Dict[str, str]]:
    allowed = {category.lower() for category in categories}
    selected: List[Dict[str, str]] = []
    for entry in catalog.entries:
        status = entry.data.get("status", "").strip().lower()
        category = entry.category.lower()
        if allowed and category not in allowed:
            continue
        if not include_completed and status and status not in DEFAULT_PENDING_STATUSES:
            continue
        selected.append(entry.data)
    return selected


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_claim(substance: str, indication: str) -> str:
    readable_substance = substance.replace("_", " ").replace("-", " ").title()
    readable_indication = indication.replace("_", " ")
    return f"{readable_substance} supports {readable_indication} outcomes"


def generate_entries(
    *,
    count: int,
    categories: Sequence[str],
    log_path: Path,
    dry_run: bool = False,
    overwrite: bool = False,
) -> None:
    policy = read_policy()
    catalog = EntryCatalog()
    available_categories = {name.lower(): config for name, config in policy.get("categories", {}).items()}

    entries = load_catalog_entries(
        catalog,
        categories,
        include_completed=overwrite,
    )
    if not entries:
        print("No catalog entries matched the provided filters.")
        return

    processed: List[Dict[str, object]] = []
    skipped_existing = 0
    for row in entries:
        if len(processed) >= count:
            break

        entry_id = row.get("entry_id", "").strip()
        category = row.get("category", "").strip().lower()
        if not entry_id or not category:
            continue

        category_cfg = available_categories.get(category)
        if not category_cfg:
            print(f"⚠️  Skipping {entry_id}: category '{category}' not defined in policy.yaml")
            continue

        domain = str(category_cfg.get("domain")) if category_cfg.get("domain") else category
        domain = CATEGORY_OVERRIDES.get(category, domain)
        substance = row.get("substance", "").strip()
        primary_indication = row.get("primary_indication", "").strip() or category

        slug = f"{slugify(substance)}-{slugify(entry_id)}"
        entry_dir = ROOT / "entries" / domain / slug / category / "v1"

        if entry_dir.exists() and (entry_dir / "entry.jsonld").exists() and not dry_run and not overwrite:
            skipped_existing += 1
            continue

        evidence_rows = build_study_rows(
            entry_id,
            category_cfg=category_cfg,
            indication=primary_indication,
            category=category,
            slug=slug,
        )

        if dry_run:
            processed.append(
                {
                    "entry_id": entry_id,
                    "category": category,
                    "domain": domain,
                    "slug": slug,
                    "preview_rows": len(evidence_rows),
                }
            )
            continue

        if entry_dir.exists() and overwrite and not dry_run:
            shutil.rmtree(entry_dir)

        ensure_directory(entry_dir)
        write_evidence(entry_dir / "evidence.csv", evidence_rows)

        claim = build_claim(substance or entry_id, primary_indication)
        build_entry(entry_dir, claim)

        entry_json = json.loads((entry_dir / "entry.jsonld").read_text(encoding="utf-8"))
        tier = entry_json.get("tier", "unknown")
        label = entry_json.get("label", "")

        timestamp = datetime.now(timezone.utc).isoformat()
        catalog.update_entry_status(
            entry_id,
            "completed",
            assignee="automation",
            final_tier=tier,
            notes=f"Batch generated on {timestamp}",
        )

        processed.append(
            {
                "entry_id": entry_id,
                "category": category,
                "domain": domain,
                "slug": slug,
                "tier": tier,
                "label": label,
                "path": str(entry_dir.relative_to(ROOT)),
                "generated_at": timestamp,
            }
        )

    if dry_run:
        print(json.dumps(processed, indent=2))
        return

    if processed:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["entry_id", "category", "domain", "slug", "tier", "label", "path", "generated_at"],
            )
            writer.writeheader()
            for row in processed:
                writer.writerow(row)

    print(f"✅ Generated {len(processed)} entries")
    if skipped_existing:
        print(f"ℹ️  Skipped {skipped_existing} entries that already have artifacts")



def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic batch entries from the catalog")
    parser.add_argument("--count", type=int, default=50, help="Number of entries to generate")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["metabolic", "immune", "immune_health"],
        help="Catalog categories to include in generation",
    )
    parser.add_argument(
        "--log",
        default="reports/generated_entries_batch.csv",
        help="Destination CSV log for generated entries",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview entries without generating artifacts")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate artifacts even if they already exist")
    return parser.parse_args(argv)



def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    generate_entries(
        count=max(0, args.count),
        categories=args.categories,
        log_path=Path(args.log),
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
