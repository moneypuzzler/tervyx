#!/usr/bin/env python3
"""Expand entry catalog to 1,000 entries for scaling test."""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[1]

# Categories with their target distribution
CATEGORY_DISTRIBUTION = {
    "sleep": 100,
    "cognition": 100,
    "mental_health": 100,
    "cardiovascular": 100,
    "metabolic": 100,
    "inflammation": 100,
    "longevity": 100,
    "musculoskeletal": 100,
    "immune": 100,
    "endocrine": 100,
}

# Common substances by category
SUBSTANCES_BY_CATEGORY = {
    "sleep": [
        "magnesium", "melatonin", "ashwagandha", "glycine", "l_theanine",
        "chamomile", "tart_cherry", "lavender", "cbd", "lemon_balm",
        "passionflower", "gaba", "5htp", "kava", "tryptophan",
        "inositol", "matcha", "magnesium_threonate", "valerian", "hops"
    ],
    "cognition": [
        "bacopa", "lions_mane", "ginkgo", "phosphatidylserine", "alpha_gpc",
        "rhodiola", "acetyl_l_carnitine", "citicoline", "lutein", "resveratrol",
        "curcumin", "omega_3", "nootropic_blend", "cerebrolysin_peptide", "methyl_b12",
        "methylfolate", "nicotinamide_riboside", "caffeine_l_theanine", "panax_ginseng", "vinpocetine"
    ],
    "mental_health": [
        "omega_3", "sam_e", "st_johns_wort", "saffron", "probiotics",
        "vitamin_d", "b_complex", "zinc", "n_acetyl_cysteine", "inositol",
        "l_tyrosine", "l_tryptophan", "magnesium", "folate", "vitamin_b6",
        "lithium_orotate", "sulforaphane", "curcumin", "lavender", "passionflower"
    ],
    "cardiovascular": [
        "omega_3", "coq10", "garlic", "hawthorn", "l_arginine",
        "l_citrulline", "beetroot", "potassium", "magnesium", "vitamin_k2",
        "niacin", "berberine", "red_yeast_rice", "grape_seed_extract", "nattokinase",
        "hibiscus", "aged_garlic", "policosanol", "plant_sterols", "psyllium"
    ],
    "metabolic": [
        "berberine", "chromium", "alpha_lipoic_acid", "cinnamon", "gymnema",
        "bitter_melon", "fenugreek", "inositol", "carnitine", "coq10",
        "omega_3", "vitamin_d", "magnesium", "green_tea", "resveratrol",
        "curcumin", "milk_thistle", "n_acetyl_cysteine", "taurine", "vanadium"
    ],
    "inflammation": [
        "curcumin", "omega_3", "boswellia", "ginger", "quercetin",
        "resveratrol", "green_tea", "bromelain", "devil_s_claw", "white_willow",
        "msm", "sam_e", "glucosamine", "chondroitin", "collagen",
        "vitamin_d", "vitamin_c", "zinc", "n_acetyl_cysteine", "spirulina"
    ],
    "longevity": [
        "resveratrol", "nmn", "nicotinamide_riboside", "pterostilbene", "fisetin",
        "quercetin", "curcumin", "omega_3", "coq10", "pqq",
        "astaxanthin", "alpha_lipoic_acid", "carnosine", "taurine", "glutathione",
        "vitamin_d", "vitamin_k2", "spermidine", "rapamycin_alternative", "metformin_alternative"
    ],
    "musculoskeletal": [
        "creatine", "hmb", "leucine", "collagen", "vitamin_d",
        "calcium", "magnesium", "vitamin_k2", "boron", "strontium",
        "protein_blend", "whey_protein", "casein", "bcaa", "glucosamine",
        "chondroitin", "msm", "hyaluronic_acid", "curcumin", "omega_3"
    ],
    "immune": [
        "vitamin_c", "vitamin_d", "zinc", "elderberry", "echinacea",
        "beta_glucan", "probiotics", "colostrum", "quercetin", "n_acetyl_cysteine",
        "selenium", "vitamin_a", "andrographis", "astragalus", "mushroom_blend",
        "olive_leaf", "garlic", "ginger", "turmeric", "propolis"
    ],
    "endocrine": [
        "myo_inositol", "d_chiro_inositol", "berberine", "cinnamon", "spearmint",
        "vitex", "ashwagandha", "rhodiola", "maca", "fenugreek",
        "selenium", "iodine", "l_tyrosine", "zinc", "vitamin_d",
        "magnesium", "dhea", "pregnenolone", "dim", "calcium_d_glucarate"
    ],
}

# Common indications by category
INDICATIONS_BY_CATEGORY = {
    "sleep": [
        "sleep_quality", "sleep_onset", "sleep_duration", "sleep_maintenance",
        "sleep_latency", "sleep_anxiety", "stress_insomnia", "rem_quality"
    ],
    "cognition": [
        "memory", "attention", "executive_function", "processing_speed",
        "cognitive_decline", "learning", "mental_clarity", "focus"
    ],
    "mental_health": [
        "depression", "anxiety", "mood_stability", "stress_resilience",
        "emotional_wellbeing", "social_anxiety", "panic_disorder", "ocd"
    ],
    "cardiovascular": [
        "blood_pressure", "lipid_profile", "endothelial_function", "arterial_health",
        "heart_rate_variability", "circulation", "cholesterol", "triglycerides"
    ],
    "metabolic": [
        "blood_sugar", "insulin_sensitivity", "metabolic_syndrome", "weight_management",
        "glucose_control", "fat_oxidation", "energy_metabolism", "hba1c"
    ],
    "inflammation": [
        "systemic_inflammation", "joint_pain", "arthritis", "crp_reduction",
        "inflammatory_markers", "autoimmune_support", "chronic_inflammation", "pain_relief"
    ],
    "longevity": [
        "cellular_aging", "mitochondrial_function", "nad_boosting", "senescence",
        "oxidative_stress", "telomere_support", "autophagy", "healthspan"
    ],
    "musculoskeletal": [
        "muscle_strength", "bone_density", "recovery", "protein_synthesis",
        "sarcopenia", "osteoporosis", "joint_health", "muscle_mass"
    ],
    "immune": [
        "immune_function", "infection_resistance", "cold_prevention", "flu_prevention",
        "immune_modulation", "upper_respiratory", "viral_defense", "immune_recovery"
    ],
    "endocrine": [
        "pcos", "thyroid_function", "hormone_balance", "insulin_resistance",
        "testosterone", "estrogen_metabolism", "adrenal_support", "menopause"
    ],
}

PRIORITY_LEVELS = ["high", "medium", "low"]
EVIDENCE_TIERS = ["P0", "P1", "P2", "P3"]


def generate_entry_id(category: str, index: int) -> str:
    """Generate deterministic entry ID."""
    cat_short = category.upper()[:4]
    return f"{cat_short}-GEN-{index:04d}"


def generate_entries(target_count: int = 1000) -> List[Dict[str, str]]:
    """Generate catalog entries to reach target count."""
    entries = []
    entry_counter = 1

    for category, count in CATEGORY_DISTRIBUTION.items():
        substances = SUBSTANCES_BY_CATEGORY.get(category, [])
        indications = INDICATIONS_BY_CATEGORY.get(category, [])

        for i in range(count):
            entry_id = generate_entry_id(category, entry_counter)
            substance = substances[i % len(substances)]
            indication = indications[i % len(indications)]

            # Distribute priorities
            if i < count * 0.3:
                priority = "high"
                evidence_tier = "P0"
            elif i < count * 0.7:
                priority = "medium"
                evidence_tier = "P1"
            else:
                priority = "low"
                evidence_tier = "P2"

            formulation_policy = "merge" if i % 3 != 0 else "split"
            formulation_detail = f"Generated formulation detail for {substance}"

            entries.append({
                "entry_id": entry_id,
                "category": category,
                "substance": substance,
                "formulation_policy": formulation_policy,
                "formulation_detail": formulation_detail,
                "primary_indication": indication,
                "priority": priority,
                "evidence_tier": evidence_tier,
                "source_hint": f"Generated entry {entry_counter}",
                "status": "pending",
                "assignee": "automation",
                "final_tier": "",
                "notes": f"Auto-generated for 1000-entry scaling test on {datetime.now(timezone.utc).isoformat()}",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "algo_version_pinned": "",
                "data_freeze_policy": "",
                "deprecation_policy": "",
            })

            entry_counter += 1

    return entries


def main():
    catalog_path = ROOT / "catalog" / "entry_catalog.csv"

    # Read existing entries
    existing_entries = []
    if catalog_path.exists():
        with catalog_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_entries.append(row)

    print(f"📊 Existing entries: {len(existing_entries)}")

    # Calculate how many more we need
    target = 1000
    existing = len(existing_entries)
    needed = target - existing

    if needed <= 0:
        print(f"✅ Catalog already has {existing} entries (target: {target})")
        return 0

    print(f"📝 Generating {needed} new entries to reach {target} total...")

    # Generate new entries
    new_entries = generate_entries(needed)[:needed]

    # Combine and write
    all_entries = existing_entries + new_entries

    # Backup original
    backup_path = catalog_path.with_suffix(".csv.backup")
    if catalog_path.exists():
        import shutil
        shutil.copy(catalog_path, backup_path)
        print(f"💾 Backed up original to {backup_path}")

    # Write expanded catalog
    fieldnames = [
        "entry_id", "category", "substance", "formulation_policy", "formulation_detail",
        "primary_indication", "priority", "evidence_tier", "source_hint", "status",
        "assignee", "final_tier", "notes", "last_updated", "algo_version_pinned",
        "data_freeze_policy", "deprecation_policy"
    ]

    with catalog_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in all_entries:
            writer.writerow(entry)

    print(f"✅ Expanded catalog to {len(all_entries)} entries")
    print(f"📊 Category distribution:")
    for category, count in CATEGORY_DISTRIBUTION.items():
        print(f"   {category}: {count} entries")

    return 0


if __name__ == "__main__":
    sys.exit(main())
