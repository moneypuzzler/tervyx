#!/usr/bin/env python3
"""
TERVYX Protocol - Scaling CLI Interface
Command-line interface for 1000+ entry scaling operations
"""

from __future__ import annotations

import sys
import argparse
import json
import hashlib
import os
import re
import uuid
from dataclasses import asdict
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

POLICY_PATH = project_root / "policy.yaml"


def _resolve_default_journal_trust_ref() -> str:
    """Derive the journal-trust snapshot date from the active policy."""

    try:
        policy_data = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    except Exception:
        policy_data = None

    if isinstance(policy_data, dict):
        snapshot = (
            policy_data.get("gates", {})
            .get("j", {})
            .get("use_snapshot")
        )
        if isinstance(snapshot, str):
            candidate = Path(snapshot).stem
            if "@" in candidate:
                candidate = candidate.split("@", maxsplit=1)[-1]
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", candidate):
                return candidate

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

component_errors: Dict[str, ImportError] = {}

try:
    from catalog.entry_catalog import CatalogEntry, EntryCatalog
except ImportError as exc:  # pragma: no cover - handled via runtime availability
    CatalogEntry = None  # type: ignore[assignment]
    EntryCatalog = None  # type: ignore[assignment]
    component_errors["catalog"] = exc

try:
    from registry.journal_registry import JournalRegistry
except ImportError as exc:  # pragma: no cover - handled via runtime availability
    JournalRegistry = None  # type: ignore[assignment]
    component_errors["registry"] = exc

try:
    from automation.collection_pipeline import CollectionPipeline
except ImportError as exc:  # pragma: no cover - handled via runtime availability
    CollectionPipeline = None  # type: ignore[assignment]
    component_errors["collection"] = exc

try:
    from scoring.relevance_scorer import RelevanceScorer
except ImportError as exc:  # pragma: no cover - handled via runtime availability
    RelevanceScorer = None  # type: ignore[assignment]
    component_errors["scorer"] = exc

try:
    from workflows.prisma_screening import PRISMAWorkflow
except ImportError as exc:  # pragma: no cover - handled via runtime availability
    PRISMAWorkflow = None  # type: ignore[assignment]
    component_errors["prisma"] = exc

try:
    from system.versioning import EntryVersionManager, slugify
except ImportError as exc:  # pragma: no cover - handled via runtime availability
    EntryVersionManager = None  # type: ignore[assignment]
    slugify = None  # type: ignore[assignment]
    component_errors["versioning"] = exc

CATALOG_AVAILABLE = EntryCatalog is not None
REGISTRY_AVAILABLE = JournalRegistry is not None
COLLECTION_AVAILABLE = CollectionPipeline is not None
SCORER_AVAILABLE = RelevanceScorer is not None
PRISMA_AVAILABLE = PRISMAWorkflow is not None
VERSIONING_AVAILABLE = EntryVersionManager is not None and slugify is not None

if component_errors:
    for name, error in component_errors.items():
        friendly_name = name.capitalize()
        print(f"⚠️  {friendly_name} component not available: {error}")
    print("Install scaling dependencies with: pip install -r requirements_scaling.txt")


def cmd_init_scaling(args):
    """Initialize scaling infrastructure"""

    if not (REGISTRY_AVAILABLE and CATALOG_AVAILABLE):
        missing = []
        if not REGISTRY_AVAILABLE:
            missing.append("journal registry")
        if not CATALOG_AVAILABLE:
            missing.append("entry catalog")
        missing_text = ", ".join(missing) or "core components"
        print(f"❌ Scaling initialization unavailable: {missing_text} missing.")
        print("Install scaling dependencies with: pip install -r requirements_scaling.txt")
        return 1
    
    print("🚀 Initializing TERVYX scaling infrastructure...")
    
    # Initialize journal registry
    print("\n📋 Setting up journal registry...")
    registry = JournalRegistry()
    
    # Add sample journals
    sample_issns = [
        "1389-9457",  # Sleep Medicine
        "1365-2869",  # Journal of Sleep Research
        "0006-3223",  # Biological Psychiatry
        "1529-9430",  # Sleep Medicine Reviews
        "1087-0792",  # Sleep
        "1099-1166",  # Depression and Anxiety
        "0033-2909",  # Psychological Bulletin
        "1073-449X"   # American Journal of Respiratory and Critical Care Medicine
    ]
    
    registry.bulk_update_registry(sample_issns, batch_size=10)
    
    registry_stats = registry.get_registry_stats()
    print(f"✅ Journal registry: {registry_stats['total_journals']} journals")
    
    # Initialize entry catalog
    print("\n📚 Setting up entry catalog...")
    catalog = EntryCatalog()

    catalog_stats = catalog.get_catalog_statistics()
    total_entries = catalog_stats.get('summary', {}).get('total_entries', 0)
    print(f"✅ Entry catalog: {total_entries} curated entries")

    # Display category breakdown
    categories = catalog_stats.get('categories', {}).get('breakdown', {})
    for category, count in categories.items():
        print(f"   {category}: {count} entries")
    
    # Initialize relevance scorer
    print("\n🧠 Setting up relevance scorer...")
    if SCORER_AVAILABLE:
        try:
            scorer = RelevanceScorer()
            print("✅ Relevance scorer initialized with BERT support")
        except Exception as e:
            print(f"⚠️  Relevance scorer initialized with limited functionality: {e}")
    else:
        print("⚠️  Relevance scorer unavailable at import time. Skipping initialization.")
    
    print("\n🎉 Scaling infrastructure ready!")
    completion_rate = catalog_stats.get('summary', {}).get('completion_rate', 0.0)
    print(f"📊 Catalog completion rate: {completion_rate:.1f}%")
    
    return 0

def cmd_registry(args):
    """Manage journal registry"""

    if not REGISTRY_AVAILABLE:
        error = component_errors.get("registry")
        detail = f" ({error})" if error else ""
        print(f"❌ Registry not available{detail}. Install dependencies first.")
        return 1
    
    registry = JournalRegistry()
    
    if args.action == 'stats':
        stats = registry.get_registry_stats()
        print("📋 Journal Registry Statistics:")
        print(f"   Total journals: {stats['total_journals']}")
        print(f"   DOAJ members: {stats['doaj_members']}")
        print(f"   COPE members: {stats['cope_members']}")
        print(f"   Average trust score: {stats['avg_trust_score']:.3f}")
        print(f"   Last updated: {stats['last_updated']}")
        
    elif args.action == 'update':
        if args.issn_list:
            issns = args.issn_list.split(',')
            print(f"Updating registry with {len(issns)} ISSNs...")
            registry.bulk_update_registry(issns)
            print("✅ Registry updated")
        else:
            print("Please provide --issn-list")
            return 1
    
    elif args.action == 'search':
        if args.query:
            results = registry.search_journals(args.query, limit=10)
            print(f"🔍 Search results for '{args.query}':")
            for result in results:
                print(f"   {result['journal_name']} ({result['issn']})")
                print(f"   Trust score: {result.get('trust_score', 0):.3f}")
        else:
            print("Please provide --query")
            return 1
    
    elif args.action == 'get':
        if args.issn:
            scorecard = registry.get_journal_scorecard(args.issn)
            if scorecard:
                print(f"📄 Scorecard for {args.issn}:")
                for key, value in scorecard.items():
                    if not key.startswith('raw_'):
                        print(f"   {key}: {value}")
            else:
                print(f"❌ No scorecard found for {args.issn}")
        else:
            print("Please provide --issn")
            return 1
    
    return 0

def cmd_catalog(args):
    """Manage entry catalog"""

    if not CATALOG_AVAILABLE:
        error = component_errors.get("catalog")
        detail = f" ({error})" if error else ""
        print(f"❌ Catalog not available{detail}. Install dependencies first.")
        return 1
    
    catalog = EntryCatalog()
    
    if args.action == 'stats':
        stats = catalog.get_catalog_statistics()
        summary = stats.get('summary', {})
        progress = stats.get('progress', {})

        print("📚 Entry Catalog Statistics:")
        print(f"   Total entries: {summary.get('total_entries', 0)}")
        print(f"   Completion rate: {summary.get('completion_rate', 0.0):.1f}%")
        print(f"   Pending high priority: {progress.get('pending_high_priority', 0)}")

        print("\n📊 Categories:")
        for category, breakdown in stats.get('categories', {}).get('completion_by_category', {}).items():
            print(
                f"   {category}: {breakdown['completed']}/{breakdown['total']} "
                f"({breakdown['rate']:.1f}%)"
            )
        
    elif args.action == 'batch':
        batch_size = args.batch_size or 10
        priority = args.priority
        category = args.category
        
        batch = catalog.get_next_batch(batch_size, priority, category)

        print(f"📦 Next batch ({len(batch)} entries):")
        for entry in batch:
            indication = entry.get('primary_indication', 'n/a')
            print(f"   {entry.get('entry_id', 'unknown')}: {entry.get('substance', 'n/a')} → {indication}")
            print(f"      Priority: {entry.get('priority', 'n/a')}, Status: {entry.get('status', 'n/a')}")

        if args.export:
            output_file = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            catalog.export_entries(batch, output_file)
            print(f"📄 Batch exported to {output_file}")
    
    elif args.action == 'search':
        if args.query:
            results = catalog.search_entries(args.query, limit=10)
            print(f"🔍 Search results for '{args.query}':")
            for result in results:
                print(
                    f"   {result.get('entry_id', 'unknown')}: "
                    f"{result.get('substance', 'n/a')} → {result.get('primary_indication', 'n/a')}"
                )
                print(
                    f"      Category: {result.get('category', 'n/a')}, "
                    f"Status: {result.get('status', 'n/a')}"
                )
        else:
            print("Please provide --query")
            return 1

    elif args.action == 'preview':
        limit = args.limit or 5
        priority = args.priority
        category = args.category

        filtered_entries = catalog.entries

        if priority:
            filtered_entries = [
                entry for entry in filtered_entries
                if entry.priority.lower() == priority.lower()
            ]

        if category:
            filtered_entries = [
                entry for entry in filtered_entries
                if entry.category.lower() == category.lower()
            ]

        limited_entries = filtered_entries[:limit]

        if not limited_entries:
            print("❌ No entries matched the preview criteria.")
            return 1

        print(f"👀 Previewing {len(limited_entries)} catalog entries:")
        for entry in limited_entries:
            data = entry.data
            entry_id = data.get('entry_id', 'unknown')
            substance = data.get('substance', 'n/a')
            indication = data.get('primary_indication', 'n/a')
            policy = data.get('formulation_policy', 'n/a')
            policy_detail = data.get('formulation_detail', '').strip()
            status = data.get('status', 'n/a')
            priority_value = data.get('priority', 'n/a')
            source = data.get('source_hint', 'n/a')

            print(f"   {entry_id} [{priority_value} / {status}]")
            print(f"      Category: {data.get('category', 'n/a')} → {indication}")
            print(f"      Substance: {substance}")
            print(f"      Evidence source: {source}")
            if policy_detail:
                print(f"      Formulation: {policy} – {policy_detail}")
            else:
                print(f"      Formulation: {policy}")
            notes = data.get('notes', '').strip()
            if notes:
                print(f"      Notes: {notes}")

    elif args.action == 'update':
        if args.entry_id and args.status:
            success = catalog.update_entry_status(
                args.entry_id,
                args.status,
                assignee=args.assignee,
                final_tier=args.tier,
                notes=args.notes or ""
            )
            if success:
                print(f"✅ Updated {args.entry_id} status to {args.status}")
            else:
                print(f"❌ Failed to update {args.entry_id}")
        else:
            print("Please provide --entry-id and --status")
            return 1

    elif args.action == 'generate':
        if not VERSIONING_AVAILABLE:
            error = component_errors.get("versioning")
            detail = f" ({error})" if error else ""
            print(f"❌ Versioning utilities unavailable{detail}.")
            return 1

        output_root = Path(args.output_dir or project_root / "entries")
        if args.dry_run:
            print(f"🧪 Dry run — entries will be previewed but not written (target {output_root})")
        else:
            output_root.mkdir(parents=True, exist_ok=True)

        entry_ids = None
        if args.entry_id:
            entry_ids = {entry.strip() for entry in args.entry_id.split(',') if entry.strip()}

        status_filter = None
        if args.status_filter:
            status_filter = {status.strip().lower() for status in args.status_filter.split(',') if status.strip()}

        try:
            algo_params = json.loads(args.algo_params) if args.algo_params else {}
            if algo_params is None:
                algo_params = {}
        except json.JSONDecodeError as exc:
            print(f"❌ Failed to decode --algo-params: {exc}")
            return 1

        try:
            algo_modules = json.loads(args.algo_modules) if args.algo_modules else {}
            if algo_modules is None:
                algo_modules = {}
            if isinstance(algo_modules, list):
                algo_modules = {
                    str(index): value for index, value in enumerate(algo_modules)
                }
            if not isinstance(algo_modules, dict):
                raise TypeError("Expected an object for --algo-modules")
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"❌ Failed to decode --algo-modules: {exc}")
            return 1

        try:
            data_sources = json.loads(args.data_sources) if args.data_sources else {}
            if data_sources is None:
                data_sources = {}
            if isinstance(data_sources, list):
                data_sources = {
                    str(index): value for index, value in enumerate(data_sources)
                }
            if not isinstance(data_sources, dict):
                raise TypeError("Expected an object for --data-sources")
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"❌ Failed to decode --data-sources: {exc}")
            return 1

        try:
            included_studies = (
                json.loads(args.included_studies)
                if args.included_studies
                else []
            )
        except json.JSONDecodeError as exc:
            print(f"❌ Failed to decode --included-studies: {exc}")
            return 1
        if included_studies is None:
            included_studies = []
        if not isinstance(included_studies, list):
            print("❌ --included-studies must decode to a list")
            return 1

        try:
            excluded_studies = (
                json.loads(args.excluded_studies)
                if args.excluded_studies
                else []
            )
        except json.JSONDecodeError as exc:
            print(f"❌ Failed to decode --excluded-studies: {exc}")
            return 1
        if excluded_studies is None:
            excluded_studies = []
        if not isinstance(excluded_studies, list):
            print("❌ --excluded-studies must decode to a list")
            return 1

        selected: List[CatalogEntry] = []
        for entry in catalog.entries:
            if entry_ids and entry.entry_id not in entry_ids:
                continue
            if args.category and entry.category.lower() != args.category.lower():
                continue
            if args.priority and entry.priority.lower() != args.priority.lower():
                continue
            if status_filter and entry.status.lower() not in status_filter:
                continue
            selected.append(entry)

        if args.limit:
            selected = selected[: args.limit]

        if not selected:
            print("❌ No catalog entries matched the generation criteria.")
            return 1

        created = 0
        skipped = 0
        run_started_at = datetime.now(timezone.utc)
        run_id = (
            args.run_id
            or f"RUN-{run_started_at.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        )
        runner = args.runner or "scripts/tervyx_scale.py@catalog-generate"
        generator_id = runner
        executor = args.executor or os.getenv("USER") or os.getenv("USERNAME") or "unknown"

        for entry in selected:
            substance_slug = slugify(entry.data.get("substance") or entry.entry_id)
            outcome_source = entry.data.get("primary_indication") or entry.category or "unspecified"
            outcome_slug = slugify(outcome_source)
            entry_slug = slugify(entry.entry_id)
            entry_root = output_root / substance_slug / outcome_slug / entry_slug
            manager = EntryVersionManager(entry_root)

            try:
                resolution = manager.resolve_version(args.content_version, args.bump)
            except ValueError as exc:
                print(f"❌ {entry.entry_id}: {exc}")
                skipped += 1
                continue

            version = resolution.version
            previous = resolution.previous
            try:
                relative_target = entry_root.relative_to(project_root)
            except ValueError:
                relative_target = entry_root

            if args.dry_run:
                print(f"📝 {entry.entry_id}: would create {relative_target}/{version}")
                continue

            try:
                version_dir = manager.create_version_dir(version)
            except FileExistsError:
                print(f"⚠️  {entry.entry_id}: {relative_target}/{version} already exists — skipping")
                skipped += 1
                continue

            entry_now = datetime.now(timezone.utc)
            timestamp = entry_now.isoformat(timespec="seconds").replace("+00:00", "Z")

            existing_notes = entry.data.get("notes", "").strip()
            note_appendix_raw = (args.status_note or args.notes or "").strip()
            note_appendix = ""
            if note_appendix_raw:
                existing_lines = {line.strip() for line in existing_notes.splitlines() if line.strip()}
                if note_appendix_raw not in existing_lines:
                    note_appendix = note_appendix_raw

            if args.set_status:
                catalog.update_entry_status(
                    entry.entry_id,
                    args.set_status,
                    assignee=args.assignee,
                    notes=note_appendix or None,
                    timestamp=timestamp,
                )

            catalog_payload = dict(entry.data)
            catalog_payload.setdefault("generated_version", version)
            catalog_payload["last_updated"] = catalog_payload.get("last_updated", timestamp)
            if args.set_status:
                catalog_payload["status"] = catalog_payload.get("status") or args.set_status
            if args.assignee:
                catalog_payload["assignee"] = args.assignee

            manifest = {
                "entry_id": entry.entry_id,
                "content_version": version,
                "created_at": timestamp,
                "catalog_entry": catalog_payload,
                "algo": {
                    "name": args.algo_name or "TERVYX-Core",
                    "version": args.algo_version or catalog_payload.get("algo_version_pinned") or "0.0.0",
                    "policy_commit": args.policy_commit or "",
                    "modules": algo_modules,
                    "parameters": algo_params,
                },
                "data_snapshot": {
                    "label": args.data_snapshot or catalog_payload.get("data_freeze_policy") or "unfrozen",
                    "freeze_policy": args.data_freeze or catalog_payload.get("data_freeze_policy", ""),
                    "source": args.data_source or "",
                    "query": args.data_query or "",
                    "dedup_hash": args.dedup_hash or "",
                    "notes": args.snapshot_note or "",
                    "sources": data_sources,
                    "included_studies": included_studies,
                    "excluded_studies": excluded_studies,
                },
                "provenance": {
                    "runner": runner,
                    "generator": generator_id,
                    "run_id": run_id,
                    "executor": executor,
                    "cost_usd": args.cost_usd,
                    "elapsed_seconds": args.elapsed_seconds,
                    "started_at": run_started_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "completed_at": timestamp,
                    "dry_run": False,
                },
                "lineage": {
                    "previous_content_version": previous,
                    "bump_type": args.bump or ("initial" if previous is None else "minor"),
                    "breaking_change": bool(args.breaking_change),
                    "change_note": args.change_note or "",
                    "change_log": args.change_log or "",
                },
                "artifacts": {
                    "catalog_snapshot": "catalog_entry.json",
                    "entry_schema": "entry.jsonld",
                    "evidence": "evidence.csv",
                    "simulation": "simulation.json",
                    "citations": "citations.json",
                    "audit_log": "audit_hash.txt",
                },
            }

            manifest_serialized = json.dumps(manifest, sort_keys=True)
            manifest_hash = hashlib.sha256(manifest_serialized.encode("utf-8")).hexdigest()
            compact_hash = f"0x{manifest_hash[:16]}"
            policy_fingerprint = compact_hash
            manifest["audit_hash"] = manifest_hash

            with (version_dir / "run_manifest.json").open("w", encoding="utf-8") as handle:
                json.dump(manifest, handle, indent=2, sort_keys=True)

            (version_dir / "audit_hash.txt").write_text(f"{manifest_hash}\n", encoding="utf-8")

            with (version_dir / "catalog_entry.json").open("w", encoding="utf-8") as handle:
                json.dump(catalog_payload, handle, indent=2, sort_keys=True)

            title_parts = []
            substance_name = entry.data.get("substance", "").strip()
            indication_name = entry.data.get("primary_indication", "").strip()
            if substance_name:
                title_parts.append(substance_name.title())
            if entry.category:
                title_parts.append(entry.category.replace("_", " ").title())
            if indication_name and indication_name.lower() != entry.category.lower():
                title_parts.append(indication_name.replace("_", " ").title())
            title = " — ".join(title_parts) or entry.entry_id

            tel5_levels_ref = getattr(args, "tel5_levels_ref", None) or "TEL-5@v1.0.0"
            monte_carlo_ref = getattr(args, "monte_carlo_ref", None) or (
                args.algo_version or "MC@v1.0.0"
            )
            journal_trust_ref = (
                getattr(args, "journal_trust_ref", None)
                or _resolve_default_journal_trust_ref()
            )

            tier_value = (entry.data.get("final_tier") or "").strip()
            valid_tiers = {"Gold", "Silver", "Bronze", "Red", "Black"}
            if tier_value not in valid_tiers:
                tier_value = "Bronze"

            tier_to_label = {
                "Gold": "PASS",
                "Silver": "PASS",
                "Bronze": "AMBER",
                "Red": "AMBER",
                "Black": "FAIL",
            }
            label_value = (entry.data.get("label") or "").strip()
            if label_value not in {"PASS", "AMBER", "FAIL"}:
                label_value = tier_to_label.get(tier_value, "AMBER")

            entry_identifier = f"{entry.category}:{substance_slug}:{outcome_slug}:{version}"

            entry_stub = {
                "@context": "https://schema.org/",
                "@type": "Dataset",
                "id": entry_identifier,
                "title": title,
                "category": entry.category,
                "tier": tier_value,
                "label": label_value,
                "P_effect_gt_delta": 0.0,
                "gate_results": {
                    "phi": entry.data.get("gate_phi", "PASS"),
                    "r": entry.data.get("gate_r", "LOW"),
                    "j": float(entry.data.get("gate_j", 0.0) or 0.0),
                    "k": entry.data.get("gate_k", "PASS"),
                    "l": entry.data.get("gate_l", "PASS"),
                },
                "evidence_summary": {
                    "n_studies": int(entry.data.get("n_studies") or 0),
                    "total_n": int(entry.data.get("total_n") or 0),
                    "I2": None,
                    "tau2": None,
                    "mu_hat": 0.0,
                    "mu_CI95": [0.0, 0.0],
                },
                "policy_refs": {
                    "tel5_levels": tel5_levels_ref,
                    "monte_carlo": monte_carlo_ref,
                    "journal_trust": journal_trust_ref,
                },
                "version": version,
                "audit_hash": compact_hash,
                "policy_fingerprint": policy_fingerprint,
                "tier_label_system": "TEL-5",
                "created": timestamp,
            }

            with (version_dir / "entry.jsonld").open("w", encoding="utf-8") as handle:
                json.dump(entry_stub, handle, indent=2, sort_keys=True)

            simulation_seed = getattr(args, "simulation_seed", None) or int(
                manifest_hash[:8], 16
            )
            simulation_draws = getattr(args, "simulation_draws", None) or 10000
            simulation_delta = getattr(args, "simulation_delta", None) or 0.2
            tau2_method = getattr(args, "tau2_method", None) or "REML"
            tau2_method = str(tau2_method).upper()
            if tau2_method not in {"REML", "DL", "ML", "HKSJ"}:
                tau2_method = "REML"
            simulation_environment = (
                getattr(args, "simulation_environment", None)
                or "TERVYX scaffold — populate with REML/MC outputs"
            )
            benefit_direction = getattr(args, "benefit_direction", None) or 1

            simulation_template = {
                "seed": int(simulation_seed),
                "n_draws": int(simulation_draws),
                "tau2_method": tau2_method,
                "delta": float(simulation_delta),
                "P_effect_gt_delta": 0.0,
                "mu_hat": 0.0,
                "mu_CI95": [0.0, 0.0],
                "var_mu": 0.0,
                "mu_se": 0.0,
                "I2": None,
                "tau2": None,
                "tau": None,
                "Q": None,
                "prediction_interval_95": [0.0, 0.0],
                "n_studies": int(entry.data.get("n_studies") or 0),
                "total_n": int(entry.data.get("total_n") or 0),
                "benefit_direction": int(benefit_direction),
                "benefit_note": "Placeholder — update after simulation run",
                "environment": simulation_environment,
                "policy_fingerprint": policy_fingerprint,
                "gate_terminated": False,
                "termination_gate": "none",
                "warnings": ["Simulation pending — populate with REML/MC outputs"],
            }

            with (version_dir / "simulation.json").open("w", encoding="utf-8") as handle:
                json.dump(simulation_template, handle, indent=2, sort_keys=True)

            citations_template = {
                "primary_sources": [],
                "secondary_sources": [],
                "notes": "Populate with structured citation metadata (paper, dataset, patent).",
                "doi_bundle": {
                    "paper": entry.data.get("doi_paper", ""),
                    "dataset": entry.data.get("doi_dataset", ""),
                    "patent": entry.data.get("doi_patent", ""),
                },
            }

            with (version_dir / "citations.json").open("w", encoding="utf-8") as handle:
                json.dump(citations_template, handle, indent=2, sort_keys=True)

            evidence_header = (
                "study_id,year,design,effect_type,effect_point,ci_low,ci_high,"  # noqa: B950
                "n_treat,n_ctrl,risk_of_bias,doi,journal_id\n"
            )
            evidence_path = version_dir / "evidence.csv"
            evidence_path.write_text(evidence_header, encoding="utf-8")

            manager.update_latest_pointer(version)

            created += 1
            print(f"✅ {entry.entry_id}: created {relative_target}/{version}")

        if args.dry_run:
            print(f"👁️  Previewed {len(selected)} entries for generation")
        else:
            print(f"🎯 Generation complete: {created} created, {skipped} skipped")

    return 0

def cmd_collect(args):
    """Run evidence collection pipeline"""

    if not COLLECTION_AVAILABLE:
        error = component_errors.get("collection")
        detail = f" ({error})" if error else ""
        print(f"❌ Collection pipeline not available{detail}. Install dependencies first.")
        return 1
    
    pipeline = CollectionPipeline()
    
    query = args.query
    max_results = args.max_results or 100
    databases = args.databases.split(',') if args.databases else ['openalex', 'pubmed']
    
    print(f"🔍 Collecting evidence for: {query}")
    print(f"📊 Max results: {max_results}")
    print(f"🗄️  Databases: {', '.join(databases)}")
    
    studies = pipeline.collect_evidence(query, max_results, databases)
    
    print(f"\n✅ Collected {len(studies)} unique studies")
    
    # Show sample results
    for i, study in enumerate(studies[:3]):
        print(f"\n{i+1}. {study.title}")
        print(f"   Authors: {', '.join(study.authors[:2])}{'...' if len(study.authors) > 2 else ''}")
        print(f"   Journal: {study.journal} ({study.publication_year})")
        print(f"   DOI: {study.doi}")
        print(f"   Source: {study.data_source}")
        print(f"   Type: {study.study_type}")
    
    # Save results
    if args.output:
        pipeline.save_collection_results(studies, args.output)
        print(f"\n💾 Results saved to {args.output}")
    
    return 0

def cmd_score(args):
    """Run relevance scoring"""

    if not SCORER_AVAILABLE:
        error = component_errors.get("scorer")
        detail = f" ({error})" if error else ""
        print(f"❌ Relevance scorer not available{detail}. Install dependencies first.")
        return 1
    
    scorer = RelevanceScorer()
    
    if args.abstract and args.category and args.substance and args.indication:
        # Single abstract scoring
        score = scorer.compute_relevance_score(
            args.abstract,
            args.category,
            args.substance, 
            args.indication
        )
        
        print(f"🧠 Relevance Score Results:")
        print(f"   Semantic Score: {score.semantic_score:.3f}")
        print(f"   Keyword Score: {score.keyword_score:.3f}")
        print(f"   Combined Score: {score.combined_score:.3f}")
        print(f"   Confidence: {score.confidence:.3f}")
        print(f"   Model: {score.scoring_model}")
        print(f"   Matched Concepts: {score.matched_concepts}")
        
        # Get relevance level
        thresholds = scorer.get_category_relevance_thresholds()
        category_thresholds = thresholds.get(args.category, thresholds['sleep'])
        
        if score.combined_score >= category_thresholds['high_relevance']:
            level = "High"
        elif score.combined_score >= category_thresholds['medium_relevance']:
            level = "Medium"  
        elif score.combined_score >= category_thresholds['low_relevance']:
            level = "Low"
        else:
            level = "Very Low"
        
        print(f"   Relevance Level: {level}")
        
    elif args.batch_file:
        # Batch scoring from file
        try:
            with open(args.batch_file, 'r') as f:
                if args.batch_file.endswith('.json'):
                    studies_data = json.load(f)
                else:
                    print("❌ Only JSON batch files supported currently")
                    return 1
            
            scores = scorer.batch_score_studies(
                studies_data,
                args.category,
                args.substance,
                args.indication
            )
            
            print(f"🧠 Batch scoring complete: {len(scores)} studies scored")
            
            # Show distribution
            high_count = sum(1 for s in scores if s.combined_score >= 0.7)
            medium_count = sum(1 for s in scores if 0.4 <= s.combined_score < 0.7)
            low_count = len(scores) - high_count - medium_count
            
            print(f"   High relevance: {high_count}")
            print(f"   Medium relevance: {medium_count}")  
            print(f"   Low relevance: {low_count}")
            
            if args.output:
                # Save scores
                scores_data = [asdict(score) for score in scores]
                with open(args.output, 'w') as f:
                    json.dump(scores_data, f, indent=2)
                print(f"💾 Scores saved to {args.output}")
                
        except FileNotFoundError:
            print(f"❌ Batch file not found: {args.batch_file}")
            return 1
        except Exception as e:
            print(f"❌ Error processing batch file: {e}")
            return 1
    
    else:
        print("❌ Provide either --abstract with PICO parameters, or --batch-file")
        return 1
    
    return 0

def cmd_prisma(args):
    """Run PRISMA screening workflow"""

    if not PRISMA_AVAILABLE:
        error = component_errors.get("prisma")
        detail = f" ({error})" if error else ""
        print(f"❌ PRISMA workflow not available{detail}. Install dependencies first.")
        return 1
    
    workflow = PRISMAWorkflow(args.review_id)
    
    if args.action == 'init':
        if not all([args.title, args.question, args.inclusion, args.exclusion]):
            print("❌ Please provide --title, --question, --inclusion, and --exclusion")
            return 1
        
        # Parse criteria (simplified - expects JSON strings)
        try:
            inclusion_criteria = json.loads(args.inclusion)
            exclusion_criteria = json.loads(args.exclusion)
        except json.JSONDecodeError:
            print("❌ Inclusion and exclusion criteria must be valid JSON")
            return 1
        
        workflow.initialize_review(
            args.title,
            args.question,
            inclusion_criteria,
            exclusion_criteria
        )
        
        print(f"✅ PRISMA review initialized: {args.title}")
    
    elif args.action == 'import':
        if not args.input_file:
            print("❌ Please provide --input-file")
            return 1
        
        try:
            with open(args.input_file, 'r') as f:
                search_results = json.load(f)
            
            workflow.import_search_results(search_results, args.database or "unknown")
            print(f"✅ Imported {len(search_results)} records")
            
        except FileNotFoundError:
            print(f"❌ Input file not found: {args.input_file}")
            return 1
        except Exception as e:
            print(f"❌ Error importing data: {e}")
            return 1
    
    elif args.action == 'dedupe':
        removed = workflow.remove_duplicates()
        print(f"✅ Removed {removed} duplicate records")
    
    elif args.action == 'screen':
        batch_size = args.batch_size or 50
        batch = workflow.title_abstract_screening(batch_size, args.reviewer_id or "auto")
        print(f"✅ Screened {len(batch)} records")
    
    elif args.action == 'stats':
        stats = workflow.get_screening_statistics()
        print("📊 PRISMA Screening Statistics:")
        print(f"   Total records: {stats['total_records']}")
        print(f"   Title/abstract screened: {stats['screening_progress']['abstract_screened']}")
        print(f"   Included: {stats['decisions']['included']}")
        print(f"   Excluded: {stats['decisions']['excluded']}")
        print(f"   Pending: {stats['decisions']['pending']}")
        print(f"   Overall completion: {stats['completion_rate']['overall']:.1f}%")
    
    elif args.action == 'flow':
        flow_data = workflow.generate_prisma_flow_diagram()
        print("📈 PRISMA Flow Diagram:")
        for key, value in flow_data.items():
            if isinstance(value, (int, str)) and not key.startswith('generated'):
                print(f"   {key}: {value}")
    
    elif args.action == 'export':
        output_format = args.format or 'csv'
        output_file = workflow.export_screening_results(output_format)
        print(f"💾 Screening results exported to {output_file}")
    
    return 0

def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="TERVYX Protocol - Scaling Operations CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Initialize scaling
    init_parser = subparsers.add_parser('init', help='Initialize scaling infrastructure')
    init_parser.set_defaults(func=cmd_init_scaling)
    
    # Journal registry
    registry_parser = subparsers.add_parser('registry', help='Manage journal registry')
    registry_parser.add_argument('action', choices=['stats', 'update', 'search', 'get'])
    registry_parser.add_argument('--issn-list', help='Comma-separated ISSN list')
    registry_parser.add_argument('--issn', help='Single ISSN')
    registry_parser.add_argument('--query', help='Search query')
    registry_parser.set_defaults(func=cmd_registry)
    
    # Entry catalog  
    catalog_parser = subparsers.add_parser('catalog', help='Manage entry catalog')
    catalog_parser.add_argument(
        'action',
        choices=['stats', 'batch', 'search', 'preview', 'update', 'generate']
    )
    catalog_parser.add_argument('--batch-size', type=int, help='Batch size')
    catalog_parser.add_argument('--priority', choices=['high', 'medium', 'low'])
    catalog_parser.add_argument('--category', help='Filter by category')
    catalog_parser.add_argument('--export', action='store_true', help='Export batch')
    catalog_parser.add_argument('--query', help='Search query')
    catalog_parser.add_argument('--entry-id', help='Entry ID to update')
    catalog_parser.add_argument('--status', help='New status')
    catalog_parser.add_argument('--assignee', help='Assignee')
    catalog_parser.add_argument('--tier', help='Final tier')
    catalog_parser.add_argument('--notes', help='Notes')
    catalog_parser.add_argument('--limit', type=int, help='Preview limit')
    catalog_parser.add_argument('--output-dir', help='Output directory for generated entries')
    catalog_parser.add_argument('--status-filter', help='Comma-separated status filter for generation')
    catalog_parser.add_argument('--dry-run', action='store_true', help='Preview generation without writing files')
    catalog_parser.add_argument('--content-version', help='Explicit content version to create')
    catalog_parser.add_argument('--bump', choices=['major', 'minor', 'patch'], help='Version bump strategy')
    catalog_parser.add_argument('--algo-version', help='Algorithm version for manifest metadata')
    catalog_parser.add_argument('--algo-name', help='Algorithm name for manifest metadata')
    catalog_parser.add_argument('--policy-commit', help='Policy commit hash or reference for manifest metadata')
    catalog_parser.add_argument('--algo-params', help='JSON-encoded algorithm parameters')
    catalog_parser.add_argument('--algo-modules', help='JSON-encoded algorithm module metadata')
    catalog_parser.add_argument('--data-snapshot', help='Data snapshot label for manifest metadata')
    catalog_parser.add_argument('--data-freeze', help='Data freeze policy for manifest metadata')
    catalog_parser.add_argument('--data-source', help='Data source identifier for manifest metadata')
    catalog_parser.add_argument('--data-sources', help='JSON object describing contributing data sources')
    catalog_parser.add_argument('--data-query', help='Primary literature query used for the run')
    catalog_parser.add_argument('--included-studies', help='JSON array of included study identifiers')
    catalog_parser.add_argument('--excluded-studies', help='JSON array of excluded study descriptors')
    catalog_parser.add_argument('--dedup-hash', help='Deduplication hash for the data snapshot')
    catalog_parser.add_argument('--snapshot-note', help='Additional notes to store in data snapshot metadata')
    catalog_parser.add_argument('--executor', help='Executor identifier recorded in manifests')
    catalog_parser.add_argument('--runner', help='Runner identifier stored in provenance metadata')
    catalog_parser.add_argument('--run-id', help='Override run identifier stored in provenance metadata')
    catalog_parser.add_argument('--cost-usd', type=float, help='Recorded generation cost in USD')
    catalog_parser.add_argument('--elapsed-seconds', type=float, help='Recorded wall time in seconds')
    catalog_parser.add_argument('--change-note', help='Change note recorded in manifest lineage')
    catalog_parser.add_argument('--change-log', help='Detailed change log recorded in manifest lineage')
    catalog_parser.add_argument('--breaking-change', action='store_true', help='Mark lineage as a breaking change')
    catalog_parser.add_argument('--simulation-model', help='Simulation model identifier stored in scaffolds')
    catalog_parser.add_argument('--simulation-seed', type=int, help='Seed recorded in simulation scaffold metadata')
    catalog_parser.add_argument('--simulation-draws', type=int, help='Draw count recorded in simulation scaffold metadata')
    catalog_parser.add_argument('--simulation-delta', type=float, help='Delta threshold stored in simulation scaffold metadata')
    catalog_parser.add_argument('--tau2-method', help='Tau-squared estimation method stored in simulation scaffolds')
    catalog_parser.add_argument('--benefit-direction', type=int, choices=[-1, 1], help='Benefit direction multiplier stored in simulation scaffolds')
    catalog_parser.add_argument('--simulation-environment', help='Computation environment note stored in simulation scaffolds')
    catalog_parser.add_argument('--tel5-levels-ref', help='TEL-5 policy reference stored in entry scaffolds')
    catalog_parser.add_argument('--monte-carlo-ref', help='Monte Carlo policy reference stored in entry scaffolds')
    catalog_parser.add_argument('--journal-trust-ref', help='Journal trust policy reference stored in entry scaffolds')
    catalog_parser.add_argument('--set-status', help='Update catalog status after generation')
    catalog_parser.add_argument('--status-note', help='Append note when updating status')
    catalog_parser.set_defaults(func=cmd_catalog)
    
    # Collection pipeline
    collect_parser = subparsers.add_parser('collect', help='Run evidence collection')
    collect_parser.add_argument('query', help='Search query')
    collect_parser.add_argument('--max-results', type=int, default=100)
    collect_parser.add_argument('--databases', help='Comma-separated database list')
    collect_parser.add_argument('--output', help='Output file')
    collect_parser.set_defaults(func=cmd_collect)
    
    # Relevance scoring
    score_parser = subparsers.add_parser('score', help='Run relevance scoring')
    score_parser.add_argument('--abstract', help='Abstract text')
    score_parser.add_argument('--category', help='Target category')
    score_parser.add_argument('--substance', help='Target substance')
    score_parser.add_argument('--indication', help='Target indication')
    score_parser.add_argument('--batch-file', help='Batch file (JSON)')
    score_parser.add_argument('--output', help='Output file')
    score_parser.set_defaults(func=cmd_score)
    
    # PRISMA workflow
    prisma_parser = subparsers.add_parser('prisma', help='Run PRISMA screening')
    prisma_parser.add_argument('review_id', help='Review identifier')
    prisma_parser.add_argument('action', choices=['init', 'import', 'dedupe', 'screen', 'stats', 'flow', 'export'])
    prisma_parser.add_argument('--title', help='Review title')
    prisma_parser.add_argument('--question', help='Research question')
    prisma_parser.add_argument('--inclusion', help='Inclusion criteria (JSON)')
    prisma_parser.add_argument('--exclusion', help='Exclusion criteria (JSON)')
    prisma_parser.add_argument('--input-file', help='Input file')
    prisma_parser.add_argument('--database', help='Database name')
    prisma_parser.add_argument('--batch-size', type=int)
    prisma_parser.add_argument('--reviewer-id', help='Reviewer ID')
    prisma_parser.add_argument('--format', choices=['csv', 'excel', 'json'])
    prisma_parser.set_defaults(func=cmd_prisma)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
