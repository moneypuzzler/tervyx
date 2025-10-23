"""
Schema validation for TERVYX Protocol artifacts.

Validates simulation.json and entry.jsonld files against their schemas
to ensure consistency and completeness of generated outputs.
"""

import json
import sys
import pathlib
from typing import Dict, Any, List
from jsonschema import Draft202012Validator, ValidationError

from engine.citations import compute_manifest_hash


# Get the root directory of the project
ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_json(file_path: pathlib.Path) -> Dict[str, Any]:
    """
    Load and parse JSON file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Parsed JSON data
    
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {file_path}: {e.msg}", e.doc, e.pos)


def validate_simulation(entry_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate simulation.json against its schema.
    
    Args:
        entry_path: Path to entry directory containing simulation.json
    
    Returns:
        Validation result dictionary
    
    Raises:
        ValidationError: If validation fails
    """
    sim_file = entry_path / "simulation.json"
    schema_file = ROOT / "protocol" / "schemas" / "simulation.schema.json"
    
    # Load files
    simulation_data = _load_json(sim_file)
    schema = _load_json(schema_file)
    
    # Validate
    try:
        Draft202012Validator(schema).validate(simulation_data)
        return {
            "valid": True,
            "file": str(sim_file),
            "schema": str(schema_file),
            "errors": []
        }
    except ValidationError as e:
        return {
            "valid": False,
            "file": str(sim_file),
            "schema": str(schema_file), 
            "errors": [{"path": list(e.path), "message": e.message}]
        }


def validate_entry(entry_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate entry.jsonld against its schema.
    
    Args:
        entry_path: Path to entry directory containing entry.jsonld
    
    Returns:
        Validation result dictionary
    
    Raises:
        ValidationError: If validation fails
    """
    entry_file = entry_path / "entry.jsonld"
    schema_file = ROOT / "protocol" / "schemas" / "entry.schema.json"
    
    # Load files
    entry_data = _load_json(entry_file)
    schema = _load_json(schema_file)
    
    # Validate
    try:
        Draft202012Validator(schema).validate(entry_data)
        return {
            "valid": True,
            "file": str(entry_file),
            "schema": str(schema_file),
            "errors": []
        }
    except ValidationError as e:
        return {
            "valid": False,
            "file": str(entry_file),
            "schema": str(schema_file),
            "errors": [{"path": list(e.path), "message": e.message}]
        }


def validate_citations(entry_path: pathlib.Path) -> Dict[str, Any]:
    """Validate citations.json against its schema."""

    citations_file = entry_path / "citations.json"
    schema_file = ROOT / "protocol" / "schemas" / "citations.schema.json"

    citations_data = _load_json(citations_file)
    schema = _load_json(schema_file)

    errors: List[Dict[str, Any]] = []
    valid = True

    try:
        Draft202012Validator(schema).validate(citations_data)
    except ValidationError as e:
        errors.append({"path": list(e.path), "message": e.message})
        valid = False

    manifest_hash = citations_data.get("manifest_hash")
    if manifest_hash:
        computed_hash = compute_manifest_hash(citations_data)
        if manifest_hash != computed_hash:
            errors.append({
                "path": ["manifest_hash"],
                "message": f"Manifest hash mismatch (expected {computed_hash})"
            })
            valid = False
    else:
        errors.append({"path": ["manifest_hash"], "message": "Manifest hash missing"})
        valid = False

    studies = citations_data.get("studies", [])
    study_ids = [study.get("study_id") for study in studies if study.get("study_id")]
    if len(study_ids) != len({identifier.lower() for identifier in study_ids}):
        errors.append({
            "path": ["studies"],
            "message": "Duplicate study_id entries detected"
        })
        valid = False

    sorted_studies = sorted(studies, key=lambda item: item.get("study_id", "").lower())
    if studies != sorted_studies:
        errors.append({
            "path": ["studies"],
            "message": "Studies must be sorted by study_id"
        })
        valid = False

    references = citations_data.get("references", [])
    sorted_refs = sorted(references, key=lambda item: (item.get("type", ""), item.get("identifier", "")))
    if references != sorted_refs:
        errors.append({
            "path": ["references"],
            "message": "References must be sorted by type then identifier"
        })
        valid = False

    for idx, ref in enumerate(references):
        study_ids_ref = ref.get("study_ids", [])
        if study_ids_ref != sorted(study_ids_ref):
            errors.append({
                "path": ["references", idx, "study_ids"],
                "message": "study_ids must be sorted"
            })
            valid = False

    return {
        "valid": valid,
        "file": str(citations_file),
        "schema": str(schema_file),
        "errors": errors
    }


def validate_policy_yaml(policy_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate policy.yaml structure and content.
    
    Args:
        policy_path: Path to policy.yaml file
    
    Returns:
        Validation result dictionary
    """
    import yaml
    
    try:
        policy_data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return {
            "valid": False,
            "file": str(policy_path),
            "errors": [{"path": [], "message": f"YAML parsing error: {e}"}]
        }
    
    errors = []
    
    # Check required top-level keys
    required_keys = ["version", "tel5_tiers", "categories", "gates", "monte_carlo"]
    for key in required_keys:
        if key not in policy_data:
            errors.append({"path": [key], "message": f"Missing required key: {key}"})
    
    # Validate TEL-5 tiers
    if "tel5_tiers" in policy_data:
        tiers = policy_data["tel5_tiers"]
        expected_tiers = ["gold", "silver", "bronze", "red", "black"]

        for tier in expected_tiers:
            if tier not in tiers:
                errors.append({"path": ["tel5_tiers", tier], "message": f"Missing tier: {tier}"})
            else:
                tier_data = tiers[tier]
                if "min_p" not in tier_data:
                    errors.append({"path": ["tel5_tiers", tier, "min_p"], "message": "Missing min_p"})
                if "label" not in tier_data:
                    errors.append({"path": ["tel5_tiers", tier, "label"], "message": "Missing label"})
    
    # Validate categories
    if "categories" in policy_data:
        for cat_name, cat_data in policy_data["categories"].items():
            if "delta" not in cat_data:
                errors.append({"path": ["categories", cat_name, "delta"], "message": "Missing delta"})
    
    # Validate gates
    if "gates" in policy_data:
        gates = policy_data["gates"]
        expected_gates = ["phi", "r", "j", "k", "l"]
        
        for gate in expected_gates:
            if gate not in gates:
                errors.append({"path": ["gates", gate], "message": f"Missing gate: {gate}"})
    
    return {
        "valid": len(errors) == 0,
        "file": str(policy_path),
        "errors": errors
    }


def validate_journal_snapshot(snapshot_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate journal trust snapshot structure.
    
    Args:
        snapshot_path: Path to journal snapshot JSON file
    
    Returns:
        Validation result dictionary
    """
    try:
        snapshot_data = _load_json(snapshot_path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {
            "valid": False,
            "file": str(snapshot_path),
            "errors": [{"path": [], "message": str(e)}]
        }
    
    errors = []
    
    # Check required top-level keys
    required_keys = ["snapshot_date", "snapshot_hash", "journals"]
    for key in required_keys:
        if key not in snapshot_data:
            errors.append({"path": [key], "message": f"Missing required key: {key}"})
    
    # Validate journal entries
    if "journals" in snapshot_data:
        journals = snapshot_data["journals"]
        required_journal_fields = ["IF_z", "SJR_z", "DOAJ", "COPE", "retracted", "predatory", "hijacked"]
        
        for journal_id, journal_data in journals.items():
            if not isinstance(journal_data, dict):
                errors.append({"path": ["journals", journal_id], "message": "Journal data must be object"})
                continue
                
            for field in required_journal_fields:
                if field not in journal_data:
                    errors.append({"path": ["journals", journal_id, field], "message": f"Missing field: {field}"})
    
    return {
        "valid": len(errors) == 0,
        "file": str(snapshot_path),
        "errors": errors
    }


def validate_all_artifacts(entry_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate all artifacts in an entry directory.
    
    Args:
        entry_path: Path to entry directory
    
    Returns:
        Combined validation results
    """
    results = {
        "entry_path": str(entry_path),
        "overall_valid": True,
        "validations": {}
    }
    
    # Validate simulation.json
    if (entry_path / "simulation.json").exists():
        sim_result = validate_simulation(entry_path)
        results["validations"]["simulation"] = sim_result
        if not sim_result["valid"]:
            results["overall_valid"] = False
    
    # Validate entry.jsonld
    if (entry_path / "entry.jsonld").exists():
        entry_result = validate_entry(entry_path)
        results["validations"]["entry"] = entry_result
        if not entry_result["valid"]:
            results["overall_valid"] = False

    # Validate citations.json
    if (entry_path / "citations.json").exists():
        citations_result = validate_citations(entry_path)
        results["validations"]["citations"] = citations_result
        if not citations_result["valid"]:
            results["overall_valid"] = False
    
    # Validate policy.yaml (at project root)
    policy_path = ROOT / "policy.yaml"
    if policy_path.exists():
        policy_result = validate_policy_yaml(policy_path)
        results["validations"]["policy"] = policy_result
        if not policy_result["valid"]:
            results["overall_valid"] = False
    
    return results


def print_validation_report(results: Dict[str, Any]) -> None:
    """
    Print a formatted validation report.
    
    Args:
        results: Validation results from validate_all_artifacts
    """
    print(f"Validation Report: {results['entry_path']}")
    print("=" * 50)
    
    overall_status = "✅ PASS" if results["overall_valid"] else "❌ FAIL"
    print(f"Overall Status: {overall_status}")
    print()
    
    for artifact, result in results["validations"].items():
        status = "✅ PASS" if result["valid"] else "❌ FAIL"
        print(f"{artifact.upper()}: {status}")
        
        if not result["valid"]:
            print(f"  File: {result['file']}")
            for error in result["errors"]:
                path_str = " -> ".join(str(p) for p in error["path"]) if error["path"] else "root"
                print(f"  Error at {path_str}: {error['message']}")
        print()


def main():
    """Command-line interface for schema validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate TERVYX Protocol artifacts")
    parser.add_argument("entry_path", 
                       help="Path to entry directory", 
                       type=pathlib.Path,
                       nargs="?",
                       default=".")
    parser.add_argument("--quiet", "-q", 
                       action="store_true",
                       help="Only print errors")
    parser.add_argument("--json", 
                       action="store_true", 
                       help="Output results as JSON")
    
    args = parser.parse_args()
    
    try:
        results = validate_all_artifacts(args.entry_path)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not args.quiet or not results["overall_valid"]:
                print_validation_report(results)
        
        # Exit with error code if validation failed
        sys.exit(0 if results["overall_valid"] else 1)
        
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()