# TERVYX Protocol v1.0

**A Reproducible Governance & Labeling Standard for Health-Information Evidence**


[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.17364486-blue)](https://doi.org/10.5281/zenodo.17364486)
[![Patent](https://img.shields.io/badge/Patent-KR%2010--2025--0143351-red)](https://doi.org/10.5281/zenodo.17364486)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data License: CC BY 4.0](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![AI Ready](https://img.shields.io/badge/AI-Ready-brightgreen.svg)](./AI-INTEGRATION-GUIDE.md)
[![Schema.org](https://img.shields.io/badge/Schema.org-Compliant-blue.svg)](./schema.org.jsonld)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-green.svg)](./api-schema.json)

TERVYX (Tiered Evidence & Risk Verification sYstem) makes the entire lifecycle of health claims—generation, evaluation, and citation—reproducible and auditable. It combines probabilistic meta-analysis with multi-gate governance to produce standardized evidence labels for humans and LLMs.

## 🎯 Core Features

### 📊 Evidence State Vector (ESV)
Normalized atomic evidence units with standardized schema:
```json
{
  "study_id": "string",
  "year": 2020,
  "design": "RCT|cohort|case-control",
  "effect_type": "SMD|MD|OR|RR",
  "effect_point": 0.18,
  "ci_low": 0.02,
  "ci_high": 0.34,
  "n_treat": 60,
  "n_ctrl": 58,
  "risk_of_bias": "low|some|high",
  "doi": "10.xxxx/abc",
  "journal_id": "sleep_med"
}
```

### 🚪 Gate Governance Protocol (GGP)
Five sequential gates ensuring **safety-first monotonicity**:
- **Φ (Natural/Category)**: Physiological impossibility / category misrouting → `FAIL`
- **R (Relevance)**: Routing fit between claim and category
- **J (Journal Trust)**: J-Oracle score; predatory/hijacked/retracted → `J-BLACK = 0`
- **K (Safety)**: Absolute caps for contraindications and serious adverse events
- **L (Exaggeration)**: "cure/permanent/instant/miracle" triggers corrective down-shifts

**Monotone invariant**: Φ or K violations cannot be offset by high J scores.

### 🏆 TEL-5 (TERVYX Evidence Levels)
5-tier classification based on `P(effect > δ)`:

| P(effect > δ) | TEL-5 Tier | Final Label | Interpretation |
|---------------|------------|-------------|----------------|
| ≥ 0.80 | 🥇 **Gold** | **PASS** | High confidence |
| 0.60–0.80 | 🥈 **Silver** | **PASS** | Moderate confidence |
| 0.40–0.60 | 🥉 **Bronze** | **AMBER** | Low confidence |
| 0.20–0.40 | 🔴 **Red** | **AMBER** | Very low confidence |
| < 0.20 or Φ/K | ⚫ **Black** | **FAIL** | Inappropriate/Risky |

### 🔬 REML + Monte Carlo Meta-Analysis
- **Estimation**: Random-effects meta-analysis using REML for τ² estimation
- **Simulation**: Monte Carlo sampling (N=10,000) for uncertainty quantification
- **Unified direction**: All effects transformed so benefit is positive
- **Reproducible**: Fixed seeds and deterministic builds

### 🏛️ Journal-Trust Oracle (J*)
Fuses multiple signals with safety-first masking:
- **Quantitative**: JCR/SJR percentiles (normalized to [0,1])
- **Qualitative**: DOAJ/COPE membership
- **Safety**: Retraction/Predatory/Hijacking blacklists → hard J-BLACK

### 📈 Partial Re-evaluation DAG
Efficient updates via dependency tracking:
- Only affected subgraphs recomputed on policy/data changes
- Versioned snapshots for full reproducibility
- Minimal rebuild latency with maximum audit transparency

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/tervyx-protocol.git
cd tervyx-protocol
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Scaffold a deterministic TEL-5 entry (creates evidence.csv, citations.json stub, etc.)
python scripts/tervyx.py new nutrient magnesium-glycinate sleep

# Populate the evidence.csv with real study rows that satisfy ESV schema
$EDITOR entries/nutrient/magnesium-glycinate/sleep/v1/evidence.csv

# Build the full artifact bundle (simulation.json, entry.jsonld, citations.json)
python tools/build_protocol_entry.py entries/nutrient/magnesium-glycinate/sleep/v1

# Inspect structured outputs
cat entries/nutrient/magnesium-glycinate/sleep/v1/entry.jsonld
cat entries/nutrient/magnesium-glycinate/sleep/v1/citations.json

# Fingerprint current policy configuration (captures gate rules + journal snapshot)
python scripts/tervyx.py fingerprint
```

## 🧮 Batch Entry Targeting Helper

Large batch builds often start from a filtered slice of `catalog/entry_catalog.csv`.
Instead of stringing together `awk`/`tail` invocations, use the curated helper below
to emit a deterministic target list for Codex or other automation clients:

```bash
python tools/select_catalog_entries.py \
  --category sleep \
  --priorities high medium \
  --count 100 \
  --output /tmp/targets.csv
```

Key details:

- `--category` performs a substring match (case-insensitive by default).
- `--priorities` accepts one or more priority tiers; omit the flag to include all rows.
- `--count` controls how many matches are emitted (use `0` to disable the cap).
- `--include-header` preserves the CSV header when downstream tooling requires it.

The script mirrors the pilot batch instructions shared with Codex, producing
`/tmp/targets.csv` suitable for looping over `build_protocol_entry.py` executions
or seeding additional deterministic workflows.

## 📁 Repository Structure

```
tervyx-protocol/
├── protocol/
│   ├── schemas/                 # JSON-Schema definitions
│   │   ├── citations.schema.json  # Citations manifest
│   │   ├── entry.schema.json      # Final TEL-5 entry format
│   │   ├── esv.schema.json        # Evidence State Vector
│   │   └── simulation.schema.json # Monte Carlo outputs
│   ├── journal_trust/
│   │   └── snapshot-2025-10-05.json
│   └── taxonomy/
│       └── tel5_categories@v1.0.0.json
├── entries/                     # Deterministic TEL-5 entries (evidence + artifacts)
│   └── nutrient/magnesium-glycinate/sleep/v1/
│       ├── evidence.csv
│       ├── simulation.json
│       ├── entry.jsonld
│       └── citations.json
├── engine/                      # Core processing engine
│   ├── citations.py             # Citations exporter
│   ├── gates.py                 # Φ/R/J/K/L gate logic
│   ├── mc_meta.py               # REML + Monte Carlo
│   ├── policy_fingerprint.py    # Policy digest construction
│   ├── schema_validate.py       # Schema validation helpers
│   └── tel5_rules.py            # P(effect>δ) → TEL-5 mapping
├── scripts/                     # CLI and utilities
└── .github/workflows/          # CI/CD pipeline
```

> **Pilot scope**: the public repository currently ships only the
> magnesium-glycinate sleep entry as the canonical TEL-5 exemplar. The
> other protocol pilot entries (omega-3, saw palmetto, melatonin, creatine)
> remain archived internally until their evidence bundles finish the new
> deterministic audit trail migration. Non-pilot entries **must not** be
> checked in until we cut the `pilot-1` tag, so the tree stays auditably
> clean for magnesium-only validation runs.

## 🔧 Core Engine Implementation

### REML Meta-Analysis
```python
def reml_tau2(y: np.ndarray, v: np.ndarray) -> float:
    """REML estimation of between-study variance τ²"""
    # Grid search + local refinement for optimal τ²
    # Returns τ² that minimizes restricted negative log-likelihood
```

### Monte Carlo Simulation  
```python
def monte_carlo_analysis(mu_hat: float, var_mu: float, delta: float, n_draws: int = 10000):
    """Generate MC samples and compute P(effect > δ)"""
    draws = np.random.normal(mu_hat, np.sqrt(var_mu), n_draws)
    return np.mean(draws > delta)
```

### TEL-5 Classification
```python
def classify_tel5(P: float, phi_violation: bool, k_violation: bool) -> tuple:
    """Map P(effect > δ) to TEL-5 tier and final label"""
    if phi_violation or k_violation:
        return "Black", "FAIL"
    elif P >= 0.80:
        return "Gold", "PASS"
    # ... additional tiers
```

## 📊 Example Output

### simulation.json
```json
{
  "seed": 20251005,
  "n_draws": 10000,
  "tau2_method": "REML", 
  "delta": 0.20,
  "P_effect_gt_delta": 0.683,
  "mu_CI95": [0.122, 0.318],
  "I2": 12.4,
  "tau2": 0.009,
  "policy_fingerprint": "0x4d3c2b1a0f9e8d7c"
}
```

### entry.jsonld
```json
{
  "@context": "https://schema.org/",
  "@type": "Dataset",
  "id": "nutrient:magnesium-glycinate:sleep:v1",
  "title": "Magnesium Glycinate — Sleep",
  "category": "sleep",
  "tier": "Gold",
  "label": "PASS",
  "P_effect_gt_delta": 0.9804,
  "gate_results": {
    "phi": "PASS",
    "r": 1.0,
    "j": 0.577,
    "k": "PASS",
    "l": "PASS"
  },
  "policy_refs": {
    "tel5_levels": "v1.2.0",
    "monte_carlo": "v1.0.1-reml-grid",
    "journal_trust": "2025-10-05"
  },
  "policy_fingerprint": "0xbe3a798944b1c64b",
  "references": [
    {
      "study_id": "Nguyen2022",
      "citation": "Nguyen2022 (2022); Journal: ISSN:1389-9457; Design: randomized controlled trial; Population: adults with primary insomnia; Outcome: psqi_total; DOI: 10.1001/jama.2022.12345; Adverse Events: None reported.",
      "doi": "10.1001/jama.2022.12345"
    }
  ],
  "audit_hash": "0xb938c5882b2a9324"
}
```

### citations.json
```json
{
  "generated": "2025-10-23T04:39:02.082585+00:00",
  "policy_fingerprint": "0xbe3a798944b1c64b",
  "source_evidence": "entries/nutrient/magnesium-glycinate/sleep/v1/evidence.csv",
  "preferred_citation": "Kim G. TERVYX Protocol v1.0 (2025).",
  "studies": [
    {
      "study_id": "Nguyen2022",
      "year": 2022,
      "design": "randomized controlled trial",
      "journal": "ISSN:1389-9457",
      "outcome": "psqi_total",
      "population": "adults with primary insomnia",
      "doi": "10.1001/jama.2022.12345",
      "citation": "Nguyen2022 (2022); Journal: ISSN:1389-9457; Design: randomized controlled trial; Population: adults with primary insomnia; Outcome: psqi_total; DOI: 10.1001/jama.2022.12345."
    }
  ],
  "references": [
    {
      "type": "doi",
      "identifier": "10.1001/jama.2022.12345",
      "study_id": "Nguyen2022",
      "url": "https://doi.org/10.1001/jama.2022.12345"
    }
  ]
}
```

## 🔒 Policy & Governance

Policy configuration in `policy.yaml`:
```yaml
tel5_levels:
  version: "v1.2.0"
  thresholds:
    sleep: { delta: 0.20, benefit_direction: -1 }  # PSQI decrease
    cognition: { delta: 0.15, benefit_direction: 1 }

monte_carlo:
  version: "v1.0.1-reml-grid"
  n_draws: 10000
  seed: 20251005

gates:
  phi:
    version: "v1.1.0"
    category_routing_threshold: 0.7
  
  journal_trust:
    snapshot_date: "2025-10-05"
    weights: { if_z: 0.35, sjr_z: 0.35, doaj: 0.15, cope: 0.05 }
```

**Policy Fingerprint**: `SHA256(policy || journal_trust_snapshot)` ensures reproducible builds.

## 🧪 CI/CD Pipeline

Automated workflow in `.github/workflows/ci.yml`:

```yaml
name: TERVYX Build Pipeline
on: [pull_request, workflow_dispatch]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Validate Schemas
        run: python -m engine.schema_validate
      
      - name: Monte Carlo Simulation  
        run: python -m engine.mc_meta --all
        
      - name: Apply TEL-5 Rules
        run: python -m engine.tel5_rules --apply
        
      - name: Reproducibility Check
        run: python scripts/repro_check.py
```

## 📝 Entry Creation Workflow

1. **Evidence Collection**: Systematic literature search following PRISMA guidelines
2. **Data Entry**: Populate `evidence.csv` with study metadata and effect sizes
3. **Build**: Run `tervyx build` to generate simulation.json and entry.jsonld
4. **Validation**: Schema validation and gate governance checks
5. **Audit**: Policy fingerprint and audit hash generation

## 🔬 Deterministic Build Pipeline

Every TEL-5 artifact is generated from reproducible steps with no LLM involvement in final labels:

1. Curate evidence rows in `evidence.csv` that conform to `protocol/schemas/esv.schema.json`.
2. Compute REML + Monte Carlo statistics via `engine/mc_meta.py`.
3. Evaluate Φ/R/J/K/L gates using deterministic rules (`engine/gates.py`, `protocol/phi_rules.yaml`, `protocol/L_rules.yaml`, and `protocol/journal_trust/`).
4. Assign TEL-5 tier/label using `engine/tel5_rules.py`.
5. Emit JSON-LD, simulation summary, and citations manifest through `tools/build_protocol_entry.py`.
6. Validate artifacts against schemas and record `policy_fingerprint` + `audit_hash` for auditability.

## 📦 Zenodo Release Checklist

1. Run `make zenodo-bundle` to generate `TERVYX_v1.0_artifact.tar.gz` with `.git/`, `.venv/`, `__pycache__/`, `node_modules/`, and secret material excluded.
2. Upload the archive to Zenodo and verify the record resolves to DOI **10.5281/zenodo.17364486**.
3. Confirm `CITATION.cff`, `.zenodo.json`, and the README badges reference the published DOI before publishing.

## 📚 Citation & Attribution

**Paper Citation:**
```bibtex
@article{kim2025tervyx,
  title={TERVYX Protocol v1.0: A Reproducible Governance \& Labeling Standard for Health-Information Evidence},
  author={Kim, Geonyeob},
  journal={Preprint},
  year={2025},
  doi={10.5281/zenodo.17364486},
  note={Patent: KR 10-2025-0143351}
}
```

**Software Citation:**
```bibtex
@software{tervyx_protocol_software,
  author={Kim, Geonyeob},
  title={TERVYX Protocol Implementation},
  url={https://github.com/your-org/tervyx-protocol},
  version={v1.0.2},
  year={2025}
}
```

## 🛡️ Patent Information

Core methods protected under:
- **Application No.**: KR 10-2025-0143351
- **Filing Date**: 2025-10-01  
- **Title**: "Verification of Non-scientific Health-Information Claims — GGP-based Hybrid Control"
- **Inventor**: Geonyeob Kim (ORCID: 0009-0005-7640-2510)

Commercial use requires licensing. Academic and public-interest research encouraged under permissive terms.

## 📄 Licensing

- **Source Code**: MIT License
- **Documentation**: CC BY 4.0
- **Data**: CC BY 4.0 (see `DATA_LICENSE`)
- **Trademarks**: TERVYX®, TEL-5®, Journal-Trust Oracle® (pending)

## 🚨 Medical Disclaimer

This protocol does not constitute medical advice and cannot replace clinical diagnosis or treatment. All outputs are for informational and research purposes only.

## 🔗 Links

- **Paper**: [DOI 10.5281/zenodo.17364486](https://doi.org/10.5281/zenodo.17364486)
- **Patent**: [KR 10-2025-0143351](https://doi.org/10.5281/zenodo.17364486)
- **ORCID**: [0009-0005-7640-2510](https://orcid.org/0009-0005-7640-2510)
- **Contact**: moneypuzzler@gmail.com

## 🤖 AI & Machine Learning Integration

### For AI Developers & Researchers

TERVYX is designed for seamless AI integration with structured metadata and standardized schemas:

- **[AI Integration Guide](./AI-INTEGRATION-GUIDE.md)**: Complete guide for AI systems
- **[Schema.org JSON-LD](./schema.org.jsonld)**: Machine-readable metadata  
- **[OpenAPI Schema](./api-schema.json)**: RESTful API specification
- **[CodeMeta](./codemeta.json)**: Software metadata for discovery
- **[Citation File Format](./CITATION.cff)**: Standardized citation data

### Machine-Readable Formats

All TERVYX entries include:
```json
{
  "llm_hint": "TEL-5=Gold, PASS; strong evidence for sleep improvement",
  "@context": "https://schema.org/",
  "@type": "Dataset",
  "tier": "Gold",
  "label": "PASS",
  "P_effect_gt_delta": 0.847
}
```

### AI Training & Usage

- **Training Data**: Generated on demand from real PubMed evidence (repository ships without synthetic samples)
- **Validation Sets**: Built dynamically alongside each TEL-5 entry with audit trails and confidence metrics
- **API Access**: RESTful endpoints for programmatic access
- **Schema Validation**: JSON Schema definitions for all data types

### Repository Metadata Files

| File | Purpose | AI Usage |
|------|---------|----------|
| `.tervyx-metadata.json` | Complete protocol metadata | System understanding |
| `CITATION.cff` | Citation File Format | Academic attribution |  
| `codemeta.json` | Software metadata | Tool discovery |
| `schema.org.jsonld` | Structured data | Knowledge graphs |
| `.zenodo.json` | Research data metadata | Dataset discovery |

---

**TERVYX Protocol v1.0** (2025-10-15) — Reproducible governance for the health information age.
