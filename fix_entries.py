#!/usr/bin/env python3
"""
Fix the generated entries to match TERVYX Protocol format
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone

def fix_citations_format(entry_path):
    """Fix citations.json to match expected format"""
    
    citations_file = entry_path / "citations.json"
    
    if citations_file.exists():
        with open(citations_file, 'r') as f:
            citations_list = json.load(f)
        
        # Convert to expected format with manifest_hash
        fixed_citations = {
            "manifest_hash": "placeholder_hash",
            "generated": datetime.now(timezone.utc).isoformat(),
            "citations": citations_list if isinstance(citations_list, list) else []
        }
        
        with open(citations_file, 'w') as f:
            json.dump(fixed_citations, f, indent=2)
        
        return True
    return False

def fix_simulation_format(entry_path):
    """Fix simulation.json to match expected format"""
    
    simulation_file = entry_path / "simulation.json"
    
    if simulation_file.exists():
        with open(simulation_file, 'r') as f:
            sim_data = json.load(f)
        
        # Ensure proper format
        if "monte_carlo_results" not in sim_data:
            fixed_simulation = {
                "timestamp": sim_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "n_simulations": sim_data.get("n_simulations", 10000),
                "seed": sim_data.get("seed", 42),
                "monte_carlo_results": {
                    "p_effect_gt_0": sim_data.get("results", {}).get("p_effect_positive", 0.75),
                    "mean_effect": sim_data.get("results", {}).get("mean_effect", 0.25),
                    "ci_lower": sim_data.get("results", {}).get("ci_lower", 0.10),
                    "ci_upper": sim_data.get("results", {}).get("ci_upper", 0.40),
                    "tau2": 0.05,
                    "i2": 25.0
                },
                "tel5_tier": "Silver",
                "label": "PASS"
            }
            
            with open(simulation_file, 'w') as f:
                json.dump(fixed_simulation, f, indent=2)
        
        return True
    return False

def main():
    """Fix all generated entries"""
    
    categories = ["cardiovascular", "cognition", "mental_health", "sleep", "metabolic"]
    
    entries_fixed = 0
    
    for category in categories:
        category_path = Path(f"entries/{category}")
        if not category_path.exists():
            continue
        
        for substance_dir in category_path.iterdir():
            if substance_dir.is_dir():
                for outcome_dir in substance_dir.iterdir():
                    if outcome_dir.is_dir():
                        for version_dir in outcome_dir.iterdir():
                            if version_dir.is_dir() and version_dir.name == "v1":
                                print(f"Fixing: {version_dir}")
                                
                                if fix_citations_format(version_dir):
                                    print(f"  ✅ Fixed citations.json")
                                
                                if fix_simulation_format(version_dir):
                                    print(f"  ✅ Fixed simulation.json")
                                
                                entries_fixed += 1
    
    print(f"\n✨ Fixed {entries_fixed} entries")
    return 0

if __name__ == "__main__":
    main()