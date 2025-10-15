# TERVYX Protocol v1.0

**A Reproducible Governance & Labeling Standard for Health-Information Evidence**

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.XXXXX-blue)](https://doi.org/10.5281/zenodo.XXXXX)
[![Patent](https://img.shields.io/badge/Patent-KR%2010--2025--0143351-red)](https://doi.org/10.5281/zenodo.XXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data License: CC BY 4.0](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

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

# Create new evidence entry
python scripts/tervyx.py new nutrient magnesium-glycinate sleep

# Build entry with TEL-5 classification
python scripts/tervyx.py build entries/nutrient/magnesium-glycinate/sleep/v1 --category sleep

# Verify reproducibility
python scripts/tervyx.py fingerprint --verify
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
├── entries/                     # Evidence entries
│   └── nutrient/magnesium-glycinate/sleep/v1/
│       ├── evidence.csv        # Input evidence table
│       ├── simulation.json     # REML+MC results  
│       ├── entry.jsonld        # Final TEL-5 output
│       └── citations.json      # Bibliography
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
  "policy_fingerprint": "sha256:..."
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
  "policy_fingerprint": "sha256:...",
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

## 🔬 Pilot Results

| Substance | Category | P(effect>δ) | Tier | Label | Limiting Factor |
|-----------|----------|-------------|------|--------|----------------|
| Magnesium glycinate | Sleep | 0.683 | Silver | **PASS** | Moderate evidence |
| Magnesium glycinate | Cognition | 0.340 | Red | **AMBER** | Low confidence |
| Omega-3 | Cardiovascular | 0.820 | Gold | **PASS** | High-quality evidence |
| Melatonin | Sleep | 0.915 | Gold | **PASS** | Strong evidence |

## 📚 Citation & Attribution

**Paper Citation:**
```bibtex
@article{kim2025tervyx,
  title={TERVYX Protocol v1.0: A Reproducible Governance \& Labeling Standard for Health-Information Evidence},
  author={Kim, Geonyeob},
  journal={Preprint},
  year={2025},
  doi={10.5281/zenodo.XXXXX},
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

- **Paper**: [DOI 10.5281/zenodo.XXXXX](https://doi.org/10.5281/zenodo.XXXXX)
- **Patent**: [KR 10-2025-0143351](https://doi.org/10.5281/zenodo.XXXXX)
- **ORCID**: [0009-0005-7640-2510](https://orcid.org/0009-0005-7640-2510)
- **Contact**: moneypuzzler@gmail.com

---

**TERVYX Protocol v1.0.2** (2025-10-15) — Reproducible governance for the health information age.