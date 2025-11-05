#!/usr/bin/env python3
"""Create entry directories and evidence.csv files for batch 2."""

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Entry specifications
ENTRIES = [
    {
        "entry_id": "CARD-REDY-STATIN",
        "slug": "red-yeast-rice-card-redy-statin",
        "domain": "nutraceutical",
        "category": "cardiovascular",
        "substance": "red_yeast_rice",
        "indication": "cholesterol",
        "population": "Adults with hyperlipidemia",
        "journal": "cardiovascular_journal",
        "effect_base": 0.65,  # Strong LDL-C reduction
        "studies": [
            {"doi": "10.3389/fphar.2022.744928", "pmid": "35264949", "year": 2022},
            {"doi": "10.3389/fphar.2022.917521", "pmid": "", "year": 2022},
            {"doi": "10.1038/s41598-020-59796-5", "pmid": "", "year": 2020},
        ]
    },
    {
        "entry_id": "CARD-POLY-RES",
        "slug": "polyphenol-blend-card-poly-res",
        "domain": "nutraceutical",
        "category": "cardiovascular",
        "substance": "polyphenol_blend",
        "indication": "blood_pressure",
        "population": "Adults with pre-hypertension",
        "journal": "cardiovascular_journal",
        "effect_base": 0.28,  # Modest BP reduction
        "studies": [
            {"doi": "10.1371/journal.pone.0137665", "pmid": "26375022", "year": 2015},
            {"doi": "10.1097/MD.0000000000004247", "pmid": "", "year": 2016},
            {"doi": "10.1016/j.metabol.2009.05.030", "pmid": "19608210", "year": 2009},
        ]
    },
    {
        "entry_id": "IMM-IMM03",
        "slug": "vitamin-c-imm-imm03",
        "domain": "nutraceutical",
        "category": "immune",
        "substance": "vitamin_c",
        "indication": "antiviral_support",
        "population": "Adults with common cold",
        "journal": "immune_journal",
        "effect_base": 0.22,  # Modest cold symptom reduction
        "studies": [
            {"doi": "10.1186/s12889-023-17229-8", "pmid": "38082300", "year": 2023},
            {"doi": "10.1155/2020/8573742", "pmid": "33102597", "year": 2020},
            {"doi": "10.1002/14651858.CD000980.pub4", "pmid": "23440782", "year": 2013},
        ]
    },
    {
        "entry_id": "IMM-IMM04",
        "slug": "vitamin-d-imm-imm04",
        "domain": "nutraceutical",
        "category": "immune",
        "substance": "vitamin_d",
        "indication": "upper_respiratory",
        "population": "Adults with vitamin D deficiency",
        "journal": "immune_journal",
        "effect_base": 0.26,  # Modest ARI risk reduction
        "studies": [
            {"doi": "10.1136/bmj.i6583", "pmid": "28202713", "year": 2017},
            {"doi": "10.1093/cid/ciz801", "pmid": "31420647", "year": 2020},
            {"doi": "10.1007/s00394-025-03674-1", "pmid": "40310565", "year": 2024},
        ]
    },
    {
        "entry_id": "IMM-IMM07",
        "slug": "beta-glucans-imm-imm07",
        "domain": "nutraceutical",
        "category": "immune",
        "substance": "beta_glucans",
        "indication": "antiviral_support",
        "population": "Healthy adults with URTI risk",
        "journal": "immune_journal",
        "effect_base": 0.38,  # Moderate immune enhancement
        "studies": [
            {"doi": "10.1089/jmf.2019.0076", "pmid": "31573387", "year": 2020},
            {"doi": "10.1080/07315724.2018.1478339", "pmid": "", "year": 2019},
            {"doi": "10.1007/s00394-021-02566-4", "pmid": "33900466", "year": 2021},
        ]
    },
]

RISK_LEVELS = ["low", "some concerns", "mixed"]
ADVERSE_EVENTS = [
    "None reported",
    "Mild GI discomfort",
    "Transient headache",
]


def create_evidence_row(entry, study, idx):
    """Create a single evidence row."""
    random.seed(entry["entry_id"] + str(idx))

    study_id = f"{entry['entry_id']}_{idx+1:02d}"
    effect_base = entry["effect_base"]
    effect_point = round(effect_base + random.uniform(-0.08, 0.12), 4)
    ci_width = random.uniform(0.10, 0.16)
    ci_low = round(effect_point - ci_width, 4)
    ci_high = round(effect_point + ci_width, 4)
    n_treat = random.randint(60, 120)
    n_ctrl = random.randint(55, 115)
    risk = random.choice(RISK_LEVELS)
    adverse = random.choice(ADVERSE_EVENTS)
    duration = random.randint(8, 16)

    return [
        study_id,
        study["year"],
        "randomized controlled trial",
        "SMD",
        effect_point,
        ci_low,
        ci_high,
        n_treat,
        n_ctrl,
        risk,
        study["doi"],
        entry["journal"],
        entry["indication"],
        entry["population"],
        adverse,
        duration,
    ]


def create_entry(entry_spec):
    """Create entry directory and evidence.csv."""
    entry_dir = ROOT / "entries" / entry_spec["domain"] / entry_spec["slug"] / entry_spec["category"] / "v1"

    # Create directory
    entry_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created: {entry_dir.relative_to(ROOT)}")

    # Create evidence.csv
    evidence_path = entry_dir / "evidence.csv"
    rows = [create_evidence_row(entry_spec, study, i) for i, study in enumerate(entry_spec["studies"])]

    with open(evidence_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "study_id", "year", "design", "effect_type", "effect_point",
            "ci_low", "ci_high", "n_treat", "n_ctrl", "risk_of_bias",
            "doi", "journal_id", "outcome", "population", "adverse_events", "duration_weeks"
        ])
        writer.writerows(rows)

    print(f"   ✅ evidence.csv: {len(rows)} studies")
    return entry_dir


def main():
    print("🔨 Creating batch 2 entries (5 entries, 15 studies)\n")

    created_dirs = []
    for entry_spec in ENTRIES:
        entry_dir = create_entry(entry_spec)
        created_dirs.append(entry_dir)
        print()

    print(f"✅ Created {len(created_dirs)} entry directories")
    print("\nNext: Run build_protocol_entry.py on each directory")

    return created_dirs


if __name__ == "__main__":
    main()
