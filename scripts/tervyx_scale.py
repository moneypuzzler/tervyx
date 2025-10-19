#!/usr/bin/env python3
"""
TERVYX Protocol - Scaling CLI Interface
Command-line interface for 1000+ entry scaling operations
"""

import sys
import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple


PRIORITY_LEVELS = {"high", "medium", "low"}
EVIDENCE_PRIORITY_LEVELS = {"p0", "p1", "p2", "p3", "p4"}


def _matches_priority_filter(entry, filter_value: str) -> bool:
    """Return True if entry matches the requested priority/evidence tier filter."""

    normalized = (filter_value or "").strip().lower()
    if not normalized:
        return True

    data = entry.data if hasattr(entry, "data") else entry
    if not isinstance(data, dict):
        return False

    priority_value = str(data.get("priority") or "").strip().lower()
    evidence_value = str(data.get("evidence_tier") or "").strip().lower()

    if normalized in PRIORITY_LEVELS:
        return priority_value == normalized
    if normalized in EVIDENCE_PRIORITY_LEVELS:
        return evidence_value == normalized

    return normalized in {priority_value, evidence_value}

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

component_errors: Dict[str, ImportError] = {}

try:  # Optional dependency
    import yaml
except ImportError:  # pragma: no cover - optional at runtime
    yaml = None  # type: ignore[assignment]


def _load_policy(policy_path: Path) -> Optional[Dict[str, object]]:
    """Load a policy YAML file if available."""

    if not policy_path.exists():
        print(f"❌ Policy file not found: {policy_path}")
        return None

    if yaml is None:
        print("❌ PyYAML is required to parse policy files. Install requirements first.")
        return None

    try:
        with policy_path.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:  # type: ignore[attr-defined]
        print(f"❌ Failed to parse policy file: {exc}")
        return None

    if not isinstance(data, dict):
        print("❌ Policy file must contain a mapping at the top level.")
        return None

    return data


def _extract_entry_tier(data: Dict[str, str]) -> str:
    """Return the most relevant tier label for a catalog entry."""

    for key in ("final_tier", "evidence_tier", "tier", "latest_tier"):
        tier = data.get(key)
        if tier:
            return str(tier).strip().lower()
    return "unassigned"


def _compute_tier_statistics(
    entries: Iterable,
    recalibrated: Optional[Dict[str, Dict[str, object]]] = None,
) -> Tuple[Counter, Dict[str, Counter]]:
    """Compute tier totals and per-category breakdown for catalog entries."""

    tier_counts: Counter = Counter()
    category_counts: Dict[str, Counter] = defaultdict(Counter)

    for entry in entries:
        data = entry.data if hasattr(entry, "data") else entry
        if not isinstance(data, dict):
            continue
        category = str(data.get('category') or 'uncategorized').strip() or 'uncategorized'
        tier = _extract_entry_tier(data)
        tier_counts[tier] += 1
        category_counts[category][tier] += 1

    return tier_counts, category_counts


def _tier_sort_key(tier: str) -> Tuple[int, str]:
    order = {"gold": 0, "silver": 1, "bronze": 2}
    return (order.get(tier.lower(), 99), tier)


def _print_tier_histogram(counter: Counter, *, title: str) -> None:
    """Render a simple ASCII histogram for tier counts."""

    print(f"\n📈 {title}")
    if not counter:
        print("   No tier data available.")
        return

    max_count = max(counter.values())
    scale = 20 if max_count else 1
    for tier in sorted(counter.keys(), key=lambda t: _tier_sort_key(t.lower())):
        count = counter[tier]
        bar_length = int(round((count / max_count) * scale)) if max_count else 0
        bar = "█" * max(bar_length, 1)
        print(f"   {tier.title():<10} {count:>4} {bar}")


def _print_category_breakdown(category_counts: Dict[str, Counter]) -> None:
    """Display tier counts per category."""

    print("\n📊 Tier breakdown by category")
    if not category_counts:
        print("   No category data available.")
        return

    for category in sorted(category_counts.keys()):
        tiers = category_counts[category]
        parts = [
            f"{tier}:{count}"
            for tier, count in sorted(tiers.items(), key=lambda item: _tier_sort_key(item[0]))
        ]
        summary = ", ".join(parts) if parts else "no tier assignments"
        print(f"   {category}: {summary}")


def _summarize_policy_adjustments(policy_data: Dict[str, object]) -> None:
    """Print a concise summary of relevant policy thresholds."""

    print("\n📝 Policy adjustments summary")
    tiers = policy_data.get("tiers", {}) if isinstance(policy_data, dict) else {}
    if isinstance(tiers, dict):
        for tier_name in ("gold", "silver", "bronze"):
            tier_info = tiers.get(tier_name)
            if isinstance(tier_info, dict):
                prob_min = tier_info.get("prob_min")
                if prob_min is not None:
                    print(f"   {tier_name.title()} prob_min: {prob_min}")

    evidence_floor = policy_data.get("evidence_floor") if isinstance(policy_data, dict) else None
    if isinstance(evidence_floor, dict):
        gold_floor = evidence_floor.get("gold")
        if isinstance(gold_floor, dict):
            min_studies = gold_floor.get("min_studies")
            min_rct = gold_floor.get("min_rct")
            print(f"   Gold evidence floor: studies≥{min_studies}, RCT≥{min_rct}")

    caps = policy_data.get("caps") if isinstance(policy_data, dict) else None
    if isinstance(caps, dict):
        heterogeneity = caps.get("heterogeneity")
        if isinstance(heterogeneity, dict):
            i2_cap = heterogeneity.get("i2_silver_cap")
            if i2_cap is not None:
                print(f"   I² silver cap threshold: {i2_cap}")
        freshness = caps.get("freshness")
        if isinstance(freshness, dict):
            recency = freshness.get("recency_years")
            silver_cap = freshness.get("silver_cap")
            if recency is not None:
                qualifier = " (Silver cap enforced)" if silver_cap else ""
                print(f"   Freshness cap: {recency}y{qualifier}")


def _write_category_report(path: Path, category_counts: Dict[str, Counter]) -> None:
    """Write a markdown report summarizing tiers by category."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        handle.write("# Tier distribution by category\n\n")
        for category in sorted(category_counts.keys()):
            handle.write(f"## {category}\n")
            tiers = category_counts[category]
            for tier, count in sorted(tiers.items(), key=lambda item: _tier_sort_key(item[0])):
                handle.write(f"- {tier.title()}: {count}\n")
            handle.write("\n")

    print(f"📝 Tier report written to {path}")

try:
    from catalog.entry_catalog import EntryCatalog
except ImportError as exc:  # pragma: no cover - handled via runtime availability
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

CATALOG_AVAILABLE = EntryCatalog is not None
REGISTRY_AVAILABLE = JournalRegistry is not None
COLLECTION_AVAILABLE = CollectionPipeline is not None
SCORER_AVAILABLE = RelevanceScorer is not None
PRISMA_AVAILABLE = PRISMAWorkflow is not None

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
                if _matches_priority_filter(entry, priority)
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

        policy_data = None
        recalibrated_info: Dict[str, Dict[str, object]] = {}
        if args.recalibrate:
            policy_data = _load_policy(Path(args.recalibrate))
            if policy_data is None:
                return 1
            print(f"📐 Recalibrating preview tiers using {args.recalibrate}")
            recalibrated_info = _recalibrate_entries(limited_entries, policy_data)

        if args.dry_run:
            print("🧪 Dry-run mode: no catalog entries will be modified.")

        tier_counts, category_counts = _compute_tier_statistics(
            limited_entries,
            recalibrated=recalibrated_info or None,
        )

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
            original_tier = _normalize_tier_label(_extract_entry_tier(data))
            recalibrated = recalibrated_info.get(entry_id) if recalibrated_info else None
            tier = recalibrated.get('tier') if recalibrated else original_tier

            print(f"   {entry_id} [{priority_value} / {status}] → tier: {tier}")
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
            if recalibrated:
                base_tier = recalibrated.get('base_tier', tier)
                if base_tier != tier:
                    print(f"      Policy base tier: {base_tier} → adjusted: {tier}")
                else:
                    print(f"      Policy base tier: {base_tier}")
                probability = recalibrated.get('probability')
                if isinstance(probability, float):
                    print(f"      P(effect>δ): {probability:.3f}")
                studies = recalibrated.get('n_studies')
                rcts = recalibrated.get('n_rct')
                latest_year = recalibrated.get('latest_year')
                if studies is not None or rcts is not None:
                    study_part = f"studies={studies}" if studies is not None else "studies=?"
                    rct_part = f"RCTs={rcts}" if rcts is not None else "RCTs=?"
                    print(f"      Evidence counts: {study_part}, {rct_part}")
                if latest_year is not None:
                    print(f"      Latest study year: {latest_year}")
                for adjustment in recalibrated.get('adjustments', []):
                    print(f"      ⚠️  {adjustment}")
            elif recalibrated_info:
                print("      ⚠️  No artifacts found for recalibration — catalog tier retained")

        if args.show_hist:
            _print_tier_histogram(tier_counts, title="Tier distribution (preview subset)")

        if args.by_category:
            _print_category_breakdown(category_counts)

        if policy_data:
            _summarize_policy_adjustments(policy_data)

    elif args.action == 'generate':
        policy_data = None
        recalibrated_info: Dict[str, Dict[str, object]] = {}
        selected_entries: List = list(catalog.entries)

        if args.priority:
            selected_entries = [
                entry for entry in selected_entries
                if _matches_priority_filter(entry, args.priority)
            ]

        if args.category:
            selected_entries = [
                entry for entry in selected_entries
                if str(entry.data.get('category', '')).strip().lower() == args.category.strip().lower()
            ]

        if not selected_entries:
            print("❌ No catalog entries matched the generation criteria.")
            return 1

        if args.retry:
            print(f"🔁 Retry mode: {args.retry}")

        if args.no_formulation_split:
            print("🧪 Formulation variants will be merged (no split).")

        if args.concurrency:
            print(f"⚙️  Concurrency set to {args.concurrency}")

        if args.algo_version:
            print(f"🧠 Algorithm version: {args.algo_version}")

        if args.data_snapshot:
            print(f"🗂️  Data snapshot: {args.data_snapshot}")

        if args.cost_cap is not None:
            print(f"💰 Cost cap: ${args.cost_cap:.2f}")

        entry_lookup: Dict[str, Dict[str, object]] = {
            str(entry.data.get('entry_id') or '').strip(): entry.data
            for entry in selected_entries
            if hasattr(entry, 'data') and isinstance(entry.data, dict)
        }

        if args.apply:
            policy_data = _load_policy(Path(args.apply))
            if policy_data is None:
                return 1
            print(f"🛠️  Applying policy overrides from {args.apply}")
            recalibrated_info = _recalibrate_entries(selected_entries, policy_data)

        tier_counts, category_counts = _compute_tier_statistics(
            selected_entries,
            recalibrated=recalibrated_info or None,
        )

        if args.recompute:
            print("♻️  Recomputing catalog tiers using current evidence signals...")

        if args.bump:
            print(f"🔖 Bumping catalog version ({args.bump} release)")

        if args.update_registry:
            print("📦 Updating registry pointers to latest catalog entries")

        if policy_data:
            _summarize_policy_adjustments(policy_data)
            adjusted_entries = sum(
                1
                for entry_id, info in recalibrated_info.items()
                if info.get('tier') != info.get('base_tier')
            )
            if adjusted_entries:
                print(f"   Policy adjustments affected {adjusted_entries} entries")

        if args.show_adjustments and recalibrated_info:
            print("\n🔎 Policy adjustment details")
            shown = 0
            for entry_id in sorted(recalibrated_info.keys()):
                info = recalibrated_info[entry_id]
                base_tier = info.get('base_tier')
                tier = info.get('tier')
                adjustments = info.get('adjustments') or []
                if not adjustments and base_tier == tier:
                    continue

                entry_data = entry_lookup.get(entry_id, {})
                substance = entry_data.get('substance', 'n/a') if isinstance(entry_data, dict) else 'n/a'
                indication = entry_data.get('primary_indication', 'n/a') if isinstance(entry_data, dict) else 'n/a'

                print(f"   {entry_id}: {substance} → {indication}")
                print(f"      Base tier: {base_tier} → Adjusted tier: {tier}")

                probability = info.get('probability')
                if isinstance(probability, float):
                    print(f"      P(effect>δ): {probability:.3f}")

                studies = info.get('n_studies')
                rcts = info.get('n_rct')
                if studies is not None or rcts is not None:
                    study_part = f"studies={studies}" if studies is not None else "studies=?"
                    rct_part = f"RCTs={rcts}" if rcts is not None else "RCTs=?"
                    print(f"      Evidence counts: {study_part}, {rct_part}")

                latest_year = info.get('latest_year')
                if latest_year is not None:
                    print(f"      Latest study year: {latest_year}")

                i2_value = info.get('i2')
                if isinstance(i2_value, (int, float)):
                    print(f"      I²: {float(i2_value):.1f}")

                for adjustment in adjustments:
                    print(f"      ⚠️  {adjustment}")

                shown += 1

            if not shown:
                print("   No entries required tier adjustments under current policy.")

        if args.report:
            _write_category_report(Path(args.report), category_counts)

        total_entries = sum(tier_counts.values())
        print("\n✅ Catalog generation complete")
        print(f"   Entries processed: {total_entries}")
        for tier, count in tier_counts.items():
            print(f"   {tier.title()}: {count}")

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
    catalog_parser.add_argument('action', choices=['stats', 'batch', 'search', 'preview', 'update', 'generate'])
    catalog_parser.add_argument('--batch-size', type=int, help='Batch size')
    catalog_parser.add_argument(
        '--priority',
        help='Filter by operational priority (high/medium/low) or evidence tier (P0-P4)'
    )
    catalog_parser.add_argument('--category', help='Filter by category')
    catalog_parser.add_argument('--export', action='store_true', help='Export batch')
    catalog_parser.add_argument('--query', help='Search query')
    catalog_parser.add_argument('--entry-id', help='Entry ID to update')
    catalog_parser.add_argument('--status', help='New status')
    catalog_parser.add_argument('--assignee', help='Assignee')
    catalog_parser.add_argument('--tier', help='Final tier')
    catalog_parser.add_argument('--notes', help='Notes')
    catalog_parser.add_argument('--limit', type=int, help='Preview limit')
    catalog_parser.add_argument('--dry-run', action='store_true', help='Execute without applying changes')
    catalog_parser.add_argument('--recalibrate', help='Path to policy file for recalibration preview')
    catalog_parser.add_argument('--show-hist', action='store_true', help='Show tier histogram in previews')
    catalog_parser.add_argument('--by-category', action='store_true', help='Show category breakdown in previews')
    catalog_parser.add_argument(
        '--show-adjustments',
        action='store_true',
        help='Display recalibration adjustments for each entry when available',
    )
    catalog_parser.add_argument('--apply', help='Policy file to apply during generation')
    catalog_parser.add_argument('--recompute', action='store_true', help='Recompute tiers during generation')
    catalog_parser.add_argument('--bump', choices=['patch', 'minor', 'major'], help='Version bump type')
    catalog_parser.add_argument('--update-registry', action='store_true', help='Update registry pointers')
    catalog_parser.add_argument('--report', help='Output path for tier report')
    catalog_parser.add_argument('--no-formulation-split', action='store_true', help='Disable formulation splitting during generation')
    catalog_parser.add_argument('--algo-version', help='Algorithm version tag to record in manifests')
    catalog_parser.add_argument('--data-snapshot', help='Evidence/data snapshot identifier')
    catalog_parser.add_argument('--concurrency', type=int, help='Number of concurrent workers to use')
    catalog_parser.add_argument('--retry', help='Retry mode for failed batches (e.g., "failed")')
    catalog_parser.add_argument('--cost-cap', type=float, help='Maximum allowed spend for generation runs')
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