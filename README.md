# TERVYX Protocol v1.0

**A Reproducible Governance & Labeling Standard for Health-Information Evidence**

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=[[URL]](https://github.com/moneypuzzler/tervyx/))](https://hits.seeyoufarm.com)

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

# Option 1 — manual curation: scaffold and populate evidence.csv
python scripts/tervyx.py new nutrient melatonin sleep
# ... populate entries/nutrient/melatonin/sleep/v1/evidence.csv with real study rows ...
python scripts/tervyx.py build entries/nutrient/melatonin/sleep/v1 --category sleep

# Option 2 — automated ingestion (requires GEMINI_API_KEY and TERVYX_EMAIL)
python scripts/tervyx.py ingest --substance melatonin --category sleep --email you@example.com --gemini-key $GEMINI_API_KEY

# When running inside GitHub Actions, surface repository secrets as env vars
# so the ingestion command can see them:
# env:
#   GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
#   TERVYX_EMAIL: ${{ secrets.TERVYX_EMAIL }}
#   NCBI_API_KEY: ${{ secrets.NCBI_API_KEY }}  # optional but recommended for higher PubMed quotas

### 🔑 Getting a PubMed (NCBI) API key

PubMed requests work as long as you provide a contact email, but adding an
NCBI API key raises your hourly quota ~10×. The process is quick:

1. Create or log in to an [NCBI account](https://account.ncbi.nlm.nih.gov/).
2. Open **Dashboard → API Keys → Create** and copy the generated value.
3. Store it as `NCBI_API_KEY` (for example under **Settings → Secrets → Actions** in GitHub).
4. Export the same key locally when you run `scripts/tervyx.py ingest` so PubMed calls pick it up.

If you skip the key, ingestion still works—it just runs under PubMed’s
default, much lower request limits.

```bash
# Fingerprint current policy configuration
python scripts/tervyx.py fingerprint
```

## 📁 Repository Structure

```
tervyx-protocol/
├── protocol/
│   ├── schemas/                 # JSON-Schema definitions
│   │   ├── esv.schema.json     # Evidence State Vector
│   │   ├── simulation.schema.json
│   │   └── entry.schema.json   # Final output format
│   └── taxonomy/
│       └── tel5_categories@v1.0.0.json
├── entries/                     # Curated TEL-5 entries (blank scaffold by default)
│   └── .gitkeep
├── entries_real/                # (Optional) outputs produced by the ingestion pipeline
│   └── ...
├── engine/                      # Core processing engine
│   ├── mc_meta.py             # REML + Monte Carlo
│   ├── tel5_rules.py          # P(effect>δ) → TEL-5 mapping
│   ├── gates.py               # Φ/R/J/K/L gate logic
│   └── schema_validate.py     # Schema validation
├── snapshots/                   # Journal trust snapshots
│   └── journal_trust@2025-10-05.json
├── scripts/                     # CLI and utilities
└── .github/workflows/          # CI/CD pipeline
```

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
  "tier": "Silver",
  "label": "PASS",
  "P_effect_gt_delta": 0.683,
  "gate_results": {
    "phi": "PASS", 
    "r": "HIGH", 
    "j": 0.78, 
    "k": "PASS", 
    "l": "PASS"
  },
  "llm_hint": "TEL-5=Silver, PASS; Φ/K no violations; sleep δ=0.20; REML+MC",
  "policy_fingerprint": "0x4d3c2b1a0f9e8d7c",
  "audit_hash": "0x2f8a9b1c3d4e5f67"
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

## 🔬 Real-data Ingestion

TERVYX no longer distributes synthetic demonstration entries. Evidence artefacts are generated directly from
primary literature using the ingestion pipeline:

1. Search PubMed and fetch detailed metadata (`system/pubmed_integration.py`).
2. Run tiered Gemini analysis for structured effect extraction (`system/cost_optimized_analyzer.py`).
3. Assess journal trust and safety gates (`system/journal_quality_db.py`).
4. Execute REML + Monte Carlo meta-analysis and TEL-5 labeling (`system/real_meta_analysis.py`).
5. Persist entries under `entries/` (manual) or `entries_real/` (automated) with full audit provenance.

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
