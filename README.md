# The VERA Archives

**Reproducible, auditable health-claim entries built with the VERA Protocol v1.0**

This repository implements the **semi-automated** pipeline described in the VERA Protocol paper:
- ESV → Gate Governance (Φ→R→J→K→L) → REML + Monte Carlo → HBV 5-tier label
- Reproducible artifacts: `simulation.json`, `entry.jsonld`
- Journal-Trust Oracle snapshot (J*) and a conservative L-gate text filter
- Policy fingerprint + audit hash chain (minimal, v1.0.1)

## Features

- **Gate Governance Protocol (GGP)**: Five gates ensuring safety-first monotonicity
- **HBV 5-tier System**: Gold/Silver/Bronze/Red/Black labeling based on evidence strength
- **Monte Carlo Meta-Analysis**: REML-based effect size estimation with uncertainty quantification
- **Journal Trust Oracle**: Combines JCR/SJR percentiles, DOAJ/COPE membership, predatory journal detection
- **Audit Trail**: Complete reproducibility with policy fingerprints and audit hashes
- **Partial Re-evaluation DAG**: Efficient updates when data or policies change

## Quickstart

```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Scaffold a sample entry and build
make new
make build
```

## Outputs

- `entries/.../v1/simulation.json` — REML + MC summary
- `entries/.../v1/entry.jsonld` — HBV 5-tier label + gate results
- Complete audit trail and reproducibility artifacts

## CLI Usage

```bash
# Create a new entry skeleton
python scripts/vera.py new nutrient magnesium-glycinate sleep

# Build an entry
python scripts/vera.py build entries/nutrient/magnesium-glycinate/sleep/v1 --category sleep

# Compute current policy fingerprint
python scripts/vera.py fingerprint
```

## Policy & Governance

- `policy.yaml` — categories, δ (MCID), gate rules, MC settings
- `snapshots/journal_trust@YYYY-MM-DD.json` — dated J* snapshot
- `policy_fingerprint = SHA256(canonical(policy.yaml) || SHA256(canonical(journal_trust)))`

**Safety-first monotonicity**: Φ/K violations cannot be offset by high J*.

## Data Entry (Semi-automated)

1. Human screening with PRISMA-style logging (`prisma_log.csv`)
2. Enter rows in `evidence.csv` (effect_type, effect_point, ci_low, ci_high, etc.)
3. Run `vera build` → HBV label

## Schemas & Standards

- `protocol/schemas/simulation.schema.json`
- `protocol/schemas/entry.schema.json`
- `protocol/taxonomy/hbv_categories@v1.0.0.json`

## CI/CD

See `.github/workflows/ci.yml`. It:
- Installs dependencies
- Builds sample entries
- Validates JSON against schemas
- Appends to `AUDIT_LOG.jsonl`

## Licensing

- **Code**: MIT License
- **Data & Documentation**: CC BY 4.0

## Related Work

- **VERA Protocol Paper**: [DOI to be assigned]
- **Patent Application**: Gate Governance Protocol for Health Claim Verification (pending)

---

**VERA®, HBV 5-tier System™, Journal-Trust Oracle™** — trademarks and filings pending