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
from dataclasses import asdict
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        generator_id = "tervyx_scale catalog generate"
        executor = args.executor or os.getenv("USER") or os.getenv("USERNAME") or "unknown"

        for entry in selected:
            category_slug = slugify(entry.category or "uncategorized")
            substance_slug = slugify(entry.data.get("substance") or entry.entry_id)
            entry_slug = slugify(entry.entry_id)
            entry_root = output_root / category_slug / substance_slug / entry_slug
            manager = EntryVersionManager(entry_root)

            try:
                resolution = manager.resolve_version(args.content_version, args.bump)
            except ValueError as exc:
                print(f"❌ {entry.entry_id}: {exc}")
                skipped += 1
                continue

            version = resolution.version
            previous = resolution.previous
            relative_target = entry_root.relative_to(project_root)

            if args.dry_run:
                print(f"📝 {entry.entry_id}: would create {relative_target}/{version}")
                continue

            try:
                version_dir = manager.create_version_dir(version)
            except FileExistsError:
                print(f"⚠️  {entry.entry_id}: {relative_target}/{version} already exists — skipping")
                skipped += 1
                continue

            catalog_payload = dict(entry.data)
            catalog_payload.setdefault("generated_version", version)

            manifest = {
                "entry_id": entry.entry_id,
                "content_version": version,
                "created_at": timestamp,
                "catalog_entry": catalog_payload,
                "algo": {
                    "name": args.algo_name or "TERVYX-Core",
                    "version": args.algo_version or "0.0.0",
                    "policy_commit": args.policy_commit or "",
                    "parameters": algo_params,
                },
                "data_snapshot": {
                    "label": args.data_snapshot or "unfrozen",
                    "freeze_policy": args.data_freeze or "",
                    "source": args.data_source or "",
                },
                "provenance": {
                    "generator": generator_id,
                    "executor": executor,
                    "dry_run": False,
                },
                "lineage": {
                    "previous_content_version": previous,
                    "bump_type": args.bump or ("initial" if previous is None else "minor"),
                    "change_note": args.change_note or "",
                },
            }

            manifest_serialized = json.dumps(manifest, sort_keys=True)
            manifest_hash = hashlib.sha256(manifest_serialized.encode("utf-8")).hexdigest()
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

            entry_stub = {
                "@context": "https://schema.org/",
                "@type": "Dataset",
                "identifier": entry.entry_id,
                "name": title,
                "category": entry.category,
                "primary_indication": entry.data.get("primary_indication"),
                "formulation_policy": entry.data.get("formulation_policy"),
                "status": entry.status or "pending",
                "priority": entry.priority or "",
                "notes": entry.data.get("notes", ""),
                "version": version,
                "manifest": "run_manifest.json",
                "catalog_snapshot": "catalog_entry.json",
                "audit_hash": manifest_hash,
                "created": timestamp,
                "tier": None,
                "label": None,
                "P_effect_gt_delta": None,
            }

            with (version_dir / "entry.jsonld").open("w", encoding="utf-8") as handle:
                json.dump(entry_stub, handle, indent=2, sort_keys=True)

            evidence_header = (
                "study_id,year,design,effect_type,effect_point,ci_low,ci_high,"  # noqa: B950
                "n_treat,n_ctrl,risk_of_bias,doi,journal_id\n"
            )
            evidence_path = version_dir / "evidence.csv"
            evidence_path.write_text(evidence_header, encoding="utf-8")

            manager.update_latest_pointer(version)

            created += 1
            print(f"✅ {entry.entry_id}: created {relative_target}/{version}")

            if args.set_status:
                catalog.update_entry_status(
                    entry.entry_id,
                    args.set_status,
                    assignee=args.assignee,
                    notes=args.status_note or args.notes or "",
                )

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
    catalog_parser.add_argument('--data-snapshot', help='Data snapshot label for manifest metadata')
    catalog_parser.add_argument('--data-freeze', help='Data freeze policy for manifest metadata')
    catalog_parser.add_argument('--data-source', help='Data source identifier for manifest metadata')
    catalog_parser.add_argument('--executor', help='Executor identifier recorded in manifests')
    catalog_parser.add_argument('--change-note', help='Change note recorded in manifest lineage')
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