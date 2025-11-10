#!/usr/bin/env python3
"""
Migration script for TERVYX Protocol v2 taxonomy.

Migrates entries from old structure to intervention_based_v2.yaml taxonomy,
rebuilds all entry artifacts, and validates policy anchors.

Usage:
    python tools/migrate_to_intervention_v2.py --in entries --taxonomy protocol/taxonomy/intervention_based_v2.yaml --workers 8
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_taxonomy(taxonomy_path: Path) -> Dict:
    """Load intervention-based v2 taxonomy."""
    with open(taxonomy_path, 'r') as f:
        return yaml.safe_load(f)


def infer_intervention_type(entry_path: Path, taxonomy: Dict) -> str:
    """
    Infer intervention type from entry path.

    Maps path components to taxonomy intervention types:
    - supplements/* → supplement
    - devices/* → device_noninvasive
    - behavioral/* → behavioral
    - foods/* → food
    - safety/* → (context-dependent)
    """
    parts = entry_path.parts

    # Check first level directory
    if 'supplements' in parts or 'nutrient' in parts:
        return 'supplement'
    elif 'devices' in parts:
        return 'device_noninvasive'
    elif 'behavioral' in parts:
        return 'behavioral'
    elif 'foods' in parts or 'diet' in parts:
        return 'food'
    elif 'safety' in parts:
        # Safety entries may need manual classification
        logger.warning(f"Safety entry detected: {entry_path}. Manual review recommended.")
        return 'supplement'  # Default to supplement for safety assessments
    else:
        logger.warning(f"Could not infer intervention type for {entry_path}. Defaulting to 'supplement'.")
        return 'supplement'


def find_all_entries(root_dir: Path) -> List[Path]:
    """
    Find all entry directories (those containing evidence.csv or entry.jsonld).
    """
    entries = []
    for evidence_csv in root_dir.rglob('evidence.csv'):
        entry_dir = evidence_csv.parent
        entries.append(entry_dir)

    logger.info(f"Found {len(entries)} entry directories")
    return entries


def compute_target_path(entry_path: Path, intervention_type: str, root_dir: Path) -> Path:
    """
    Compute target path based on intervention type and taxonomy.

    Structure: entries/{intervention_type}/{subcategory}/{product}/{outcome}/v{N}
    """
    parts = entry_path.parts

    # Try to extract: subcategory, product, outcome, version
    # Assuming structure like: entries/old_type/subcategory/product/outcome/vN

    # Find outcome (usually second-to-last before version)
    outcome = None
    version = 'v1'

    if len(parts) >= 2 and parts[-1].startswith('v'):
        version = parts[-1]
        outcome = parts[-2] if len(parts) >= 2 else 'unknown'
    else:
        outcome = parts[-1] if len(parts) >= 1 else 'unknown'

    # Extract subcategory and product (heuristic)
    if len(parts) >= 4:
        subcategory = parts[-4] if not parts[-4] in ['entries', 'supplements', 'devices', 'behavioral', 'foods'] else 'general'
        product = parts[-3]
    else:
        subcategory = 'general'
        product = 'unknown'

    # Build target path
    target = root_dir / intervention_type / subcategory / product / outcome / version
    return target


def move_entry(entry_path: Path, target_path: Path) -> bool:
    """
    Move entry directory to target path.
    Returns True if successful.
    """
    try:
        if entry_path == target_path:
            logger.info(f"Entry already at target: {entry_path}")
            return True

        # Create parent directories
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Move directory
        if target_path.exists():
            logger.warning(f"Target already exists: {target_path}. Skipping move.")
            return False

        entry_path.rename(target_path)
        logger.info(f"Moved: {entry_path} → {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to move {entry_path} to {target_path}: {e}")
        return False


def rebuild_entry(entry_path: Path) -> Tuple[bool, str]:
    """
    Rebuild entry artifacts using build_protocol_entry.py.
    Returns (success, message).
    """
    try:
        result = subprocess.run(
            ['python', 'tools/build_protocol_entry.py', str(entry_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return True, f"Built: {entry_path}"
        else:
            return False, f"Build failed for {entry_path}: {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, f"Build timeout for {entry_path}"
    except Exception as e:
        return False, f"Build error for {entry_path}: {e}"


def validate_entry_artifacts(entry_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate that entry has all 3 required artifacts and they conform to schemas.
    Returns (valid, errors).
    """
    errors = []

    # Check for required files
    required_files = ['evidence.csv', 'simulation.json', 'entry.jsonld', 'citations.json']
    for filename in required_files:
        filepath = entry_path / filename
        if not filepath.exists():
            errors.append(f"Missing {filename}")

    if errors:
        return False, errors

    # Validate entry.jsonld structure
    try:
        with open(entry_path / 'entry.jsonld', 'r') as f:
            entry = json.load(f)

        # Check required policy anchors
        required_fields = [
            'policy_refs',
            'policy_fingerprint',
            'audit_hash',
            'tier_label_system'
        ]

        for field in required_fields:
            if field not in entry:
                errors.append(f"Missing field: {field}")

        # Validate policy_refs structure
        if 'policy_refs' in entry:
            required_refs = ['tel5_levels', 'monte_carlo', 'journal_trust']
            for ref in required_refs:
                if ref not in entry['policy_refs']:
                    errors.append(f"Missing policy_refs.{ref}")

        # Validate fingerprint format
        if 'policy_fingerprint' in entry:
            fp = entry['policy_fingerprint']
            if not (fp.startswith('0x') and len(fp) == 18):
                errors.append(f"Invalid policy_fingerprint format: {fp}")

    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in entry.jsonld: {e}")
    except Exception as e:
        errors.append(f"Validation error: {e}")

    return len(errors) == 0, errors


def process_entry(entry_info: Tuple[Path, Path, Dict, Path]) -> Dict:
    """
    Process a single entry: move, rebuild, validate.
    Returns result dict.
    """
    entry_path, root_dir, taxonomy, _ = entry_info

    result = {
        'entry': str(entry_path),
        'success': False,
        'moved': False,
        'rebuilt': False,
        'validated': False,
        'errors': []
    }

    try:
        # Infer intervention type
        intervention_type = infer_intervention_type(entry_path, taxonomy)

        # Compute target path
        target_path = compute_target_path(entry_path, intervention_type, root_dir)

        # Move entry
        if move_entry(entry_path, target_path):
            result['moved'] = True
            entry_path = target_path  # Update to new path
        else:
            result['errors'].append("Failed to move entry")
            return result

        # Rebuild artifacts
        rebuilt, msg = rebuild_entry(entry_path)
        result['rebuilt'] = rebuilt
        if not rebuilt:
            result['errors'].append(msg)
            return result

        # Validate artifacts
        validated, errors = validate_entry_artifacts(entry_path)
        result['validated'] = validated
        if not validated:
            result['errors'].extend(errors)
            return result

        result['success'] = True
        result['target'] = str(entry_path)

    except Exception as e:
        result['errors'].append(f"Unexpected error: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description='Migrate entries to intervention_based_v2 taxonomy')
    parser.add_argument('--in', dest='input_dir', required=True, help='Root entries directory')
    parser.add_argument('--taxonomy', required=True, help='Path to intervention_based_v2.yaml')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    args = parser.parse_args()

    root_dir = Path(args.input_dir)
    taxonomy_path = Path(args.taxonomy)

    if not root_dir.exists():
        logger.error(f"Input directory does not exist: {root_dir}")
        sys.exit(1)

    if not taxonomy_path.exists():
        logger.error(f"Taxonomy file does not exist: {taxonomy_path}")
        sys.exit(1)

    # Load taxonomy
    taxonomy = load_taxonomy(taxonomy_path)
    logger.info(f"Loaded taxonomy: {taxonomy_path}")

    # Find all entries
    entries = find_all_entries(root_dir)
    logger.info(f"Processing {len(entries)} entries with {args.workers} workers")

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        for entry in entries[:5]:  # Show first 5
            intervention_type = infer_intervention_type(entry, taxonomy)
            target = compute_target_path(entry, intervention_type, root_dir)
            logger.info(f"Would move: {entry} → {target}")
        return

    # Process entries in parallel
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(process_entry, (entry, root_dir, taxonomy, taxonomy_path))
            for entry in entries
        ]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if result['success']:
                logger.info(f"✅ {result['entry']}")
            else:
                logger.error(f"❌ {result['entry']}: {', '.join(result['errors'])}")

    # Summary
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    moved = sum(1 for r in results if r['moved'])
    rebuilt = sum(1 for r in results if r['rebuilt'])
    validated = sum(1 for r in results if r['validated'])

    logger.info("\n" + "="*60)
    logger.info("MIGRATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total entries: {total}")
    logger.info(f"Successfully processed: {successful} ({100*successful/total:.1f}%)")
    logger.info(f"Moved: {moved}")
    logger.info(f"Rebuilt: {rebuilt}")
    logger.info(f"Validated: {validated}")

    if successful < total:
        logger.warning(f"\n⚠️  {total - successful} entries failed. Review errors above.")
        sys.exit(1)
    else:
        logger.info("\n✅ All entries migrated successfully!")


if __name__ == '__main__':
    main()
