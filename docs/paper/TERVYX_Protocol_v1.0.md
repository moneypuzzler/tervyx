# TERVYX Protocol v1.0: A Reproducible Governance & Labeling Standard for Health-Information Evidence

**Geonyeob Kim** (Independent Researcher)  
ORCID: [0009-0005-7640-2510](https://orcid.org/0009-0005-7640-2510)

**Patent notice:** Some methods and components presented here are the subject of a pending patent application (see Competing Interests).

## Abstract

Online health information suffers from heterogeneous evidence quality, delayed updates, and inconsistent provenance, leaving no widely trusted standard. We introduce the **TERVYX Protocol** (Tiered Evidence & Risk Verification sYstem), which makes the entire lifecycle of health claims—generation, evaluation, and citation—reproducible and auditable. Its core components are (i) an **Evidence State Vector (ESV)**, (ii) **Gate Governance** with five gates—Natural/Category violation (Φ), Relevance (R), Journal Trust (J), Safety (K), and Exaggeration Language (L)—and (iii) a category-wise probabilistic index, the **TERVYX Evidence Levels (TEL-5)**.

Effects are estimated via random-effects meta-analysis using **REML**, then _Monte Carlo_ simulation yields `P(effect > δ)` mapped to TEL-5 tiers. A _Journal-Trust Oracle_ fuses JCR/SJR percentiles, DOAJ/COPE membership, and Retraction/Predatory/Hijacking signals; critically, Φ or K violations cannot be offset by high J (monotone masking/capping). Each entry is built as `evidence.csv → simulation.json → entry.jsonld`, including DOI, JSON-LD, BibTeX/CSL, and an audit hash. Policy changes are versioned (semver) under RFC-based governance, and only affected subgraphs are recomputed via a **partial re-evaluation DAG**.

We pilot five substances (e.g., magnesium glycinate) across sleep, cognition, mental health and renal safety, and evaluate Label Stability, AUROC, Expected Calibration Error (ECE), rebuild latency, and appeals throughput. By preserving the patent-backed logical skeleton while providing an evolvable, reproducible standard, TERVYX offers an evidence infrastructure that academia, platforms, and LLMs can co-cite.

**Keywords:** health information, meta-analysis, Monte Carlo, journal trust, governance, reproducibility, encyclopedia, LLM

## 1. Introduction

Public health claims online are undermined by conflicting narratives, exaggeration, and opaque sources. Existing assessment systems suffer from (i) _one-dimensional scoring_ of multi-faceted interventions; (ii) _subjective dependence_ on expert judgment; (iii) _information asymmetry_ between meta-analytic complexity and lay accessibility; and (iv) _pseudo-medicine co-mingling_ with scientific evidence. A standard that quantifies evidence strength/uncertainty, safety, and source quality—then distributes labels in an auditable form—is missing. This paper proposes the **TERVYX Protocol** to fill this gap.

### 1.1 Goals

- **Reproducibility:** identical data, policy, and seed yield identical results.
- **Efficiency:** partial re-evaluation via a dependency DAG on data/policy changes.
- **Interoperability:** machine-ready outputs (DOI/JSON-LD/BibTeX) for humans and LLMs.
- **Transparency:** publish all decision rationales and reliability metrics for audit.

## 2. Related Work

Reporting standards such as PRISMA guide systematic reviews but lack live labeling, APIs, and cryptographic auditing. Fact-checking and moderation often remain qualitative. TERVYX combines _probabilistic effect estimation_, _multi-gate governance_, a _Journal-Trust Oracle_, and a _reproducible build pipeline_ into one protocol.

## 3. Core Concepts

### 3.1 Evidence State Vector (ESV)

We normalize the atomic evidence unit as:

```json
{
  "study_id": "string",
  "year": 2020,
  "design": "RCT|cohort|case-control|...",
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

`journal_id` connects to the Journal-Trust Oracle.

### 3.2 Gate Governance (GGP)

We evaluate claim `c` with evidence `E` through five sequential gates: **Φ → R → J → K → L**.

- **Φ (Natural/Category):** physiological impossibility / category misrouting ⇒ FAIL.
- **R (Relevance):** routing fit between claim and category (below threshold ⇒ AMBER↓ or exclude).
- **J (Journal Trust):** J-Oracle score; predatory/hijacked/retracted ⇒ `J-BLACK = 0`.
- **K (Safety):** absolute caps for contraindications and serious adverse events.
- **L (Exaggeration):** "cure/permanent/instant/miracle/risk-free" triggers corrective down-shifts.

**Monotone invariant:** Φ or K violations cannot be offset by J; PASS cannot be upgraded under Φ/K.

#### 3.2.1 Exaggeration Language (L) — bilingual patterns

| Forbidden | Korean patterns | English patterns | Exceptions |
|-----------|----------------|------------------|------------|
| Cure / Complete cure | `완전(히)? (치료\|완치)` | `\b(cure\|completely\s*cured\|permanent\s*cure)\b` | "adjuvant to treatment", "helps with" |
| Instant | `즉시\|바로\|당장` | `\b(instant(ly)?\|immediate(ly)?)\b` | "gradual", "over weeks" |
| Panacea | `모든 질병\|만병통치\|만능` | `\b(cure[-\s]?all\|panacea\|works\s*for\s*everything)\b` | — |
| No side effects | `부작용 (전혀 )?없(음\|다)` | `\b(no\s*side\s*effects\|risk[-\s]?free)\b` | "few side effects", "safety established" |

### 3.3 Probabilistic Effects and TEL-5 (TERVYX Evidence Levels)

We estimate τ² via REML, then draw Monte Carlo samples of the meta-analytic mean. All effects are transformed so that _benefit is positive_ (e.g., PSQI _decrease_ ⇒ multiply by −1).

| P(effect > δ) | TEL-5 tier | Final label | Interpretation |
|---------------|------------|-------------|----------------|
| ≥ 0.80 | **Gold** | **PASS** | High confidence |
| 0.60–0.80 | **Silver** | **PASS** | Moderate confidence |
| 0.40–0.60 | **Bronze** | **AMBER** | Low confidence |
| 0.20–0.40 | **Red** | **AMBER** | Very low confidence |
| < 0.20 or Φ/K violation | **Black** | **FAIL** | Inappropriate/Risky |

### 3.4 Partial Re-evaluation DAG

We define a dependency graph over category thresholds `δ`, journal-trust snapshots, and entry evidence tables; changes propagate only to affected subgraphs.

**Propagation rules (formal):** (i) Δ(journal_trust@t) ⇒ recompute all dependent entries; (ii) Δ(evidence.csv) ⇒ recompute that entry only; (iii) Δ(δ) ⇒ recompute all entries in the category and invalidate upstream caches.

## 4. Journal-Trust Oracle (J*)

### 4.1 Signal Fusion

We fuse normalized JCR/SJR percentiles (`IF_z, SJR_z ∈ [0,1]`) with binary DOAJ/COPE and blacklist signals (Retraction/Predatory/Hijacked).

#### 4.1.1 Normalization and BLACK pre-mask

```python
# Pre-mask (BLACK triggers)
if (Retraction or Predatory or Hijacked):
    J* = 0.0      # BLACK → evidence excluded
else:
    # Raw linear combination (policy-tunable weights)
    J_raw = 0.35*IF_z + 0.35*SJR_z + 0.15*DOAJ + 0.05*COPE \
            - 0.50*Retraction - 0.50*Predatory - 0.30*Hijacked
    # Calibrated squashing + clipping
    J* = clip( sigmoid(a * J_raw + b), 0.0, 1.0 )  # a,b fixed per policy version
```

### 4.2 Snapshot Management

```json
{
  "snapshot_date": "2025-10-05",
  "snapshot_hash": "sha256:... (canonical JSON over sorted journals)",
  "signer": "ed25519:0x...",
  "data_sources": {
    "jcr_update": "2025-06-15",
    "sjr_update": "2025-07-20",
    "doaj_scraped": "2025-10-01",
    "predatory_lists": ["Beall", "Cabell", "Think-Check-Submit"]
  }
}
```

## 5. Data Schema and Interfaces

### 5.1 Input: `evidence.csv`

| Column | Type | Description |
|--------|------|-------------|
| study_id | string | Study identifier |
| year | integer | Publication year |
| design | string | Study design (RCT/cohort/etc.) |
| effect_type | string | Effect size type (SMD/MD/OR/RR) |
| effect_point | float | Point estimate |
| ci_low | float | 95% CI lower bound |
| ci_high | float | 95% CI upper bound |
| n_treat | integer | Treatment sample size |
| n_ctrl | integer | Control sample size |
| risk_of_bias | string | low / some / high |
| doi | string | DOI |
| journal_id | string | Journal identifier (links to J-Oracle) |

### 5.2 Output Artifacts

#### `simulation.json`

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
  "environment": "Python 3.11, NumPy 1.24.0, SciPy 1.11.0",
  "policy_fingerprint": "sha256:REPLACE_WITH_ACTUAL_BUILD_DIGEST"
}
```

#### `entry.jsonld`

```json
{
  "@context": "https://schema.org/",
  "@type": "Dataset",
  "id": "nutrient:magnesium-glycinate:sleep:v1",
  "title": "Magnesium Glycinate — Sleep",
  "category": "sleep",
  "tier": "Silver",
  "label": "PASS",
  "P_effect_gt_delta": 0.683,
  "gate_results": { "phi": "PASS", "r": "HIGH", "j": 0.78, "k": "PASS", "l": "PASS" },
  "evidence_summary": { "n_studies": 3, "total_n": 502, "I2": 12.4, "tau2": 0.009 },
  "policy_refs": { "tel5_levels": "v1.2.0", "monte_carlo": "v1.0.1-reml-grid", "journal_trust": "2025-10-05" },
  "preferred_citation": "Kim, G. (2025). TERVYX Protocol...",
  "bibtex": "@dataset{kim2025tervyx, ...}",
  "csl_json": { "...": "..." },
  "doi": "10.5281/zenodo.XXXXX",
  "version": "v1",
  "audit_hash": "0x2f8a9b1c3d4e5f67",
  "llm_hint": "TEL-5=Silver, PASS; Φ/K no violations; sleep δ=0.20; REML+MC",
  "policy_fingerprint": "sha256:REPLACE_WITH_ACTUAL_BUILD_DIGEST",
  "tier_label_system": "TEL-5"
}
```

All endpoints support content negotiation (`Accept: application/ld+json | x-bibtex | csl+json`).

## 6. Methods

### 6.1 Random-Effects (REML) + Monte Carlo

We prefer **REML** over DerSimonian–Laird for τ² estimation. _Policy–evidence separation_ is enforced: only policy changes (δ, gate rules) or data changes trigger recomputation.

#### Algorithm 1. REML-based MC meta-analysis (unified benefit direction)

```
1) Preprocess: CI→SE, unify direction (benefit = positive)
   - OR/RR: log-transform; SE = (log(CI_high)-log(CI_low)) / (2×1.96)
   - SMD/MD: linear; SE = (CI_high - CI_low) / (2×1.96)
   - Apply benefit_direction ∈ {+1,−1} to y

2. REML τ²
   * w_i = 1/(SE_i² + τ²), μ̂ = Σ(w_i y_i)/Σ(w_i), Var(μ̂) = 1/Σ(w_i)
   * I² = max(0,(Q−df)/Q)×100

3. Monte Carlo (N=10,000)
   * μ^(k) ~ Normal(μ̂, √Var(μ̂)), k=1..N
   * P(μ>δ) = mean[ μ^(k) > δ ]
   * 95% PI = μ̂ ± 1.96 × √(τ² + Var(μ̂))

4. TEL-5 mapping and label
   * P → {Gold, Silver, Bronze, Red, Black}
   * Φ/K/L violations cap label (J cannot offset)
```

### 6.2 Label Rules (5-tier)

- **PASS**: `P ≥ 0.60` (Gold/Silver) and no Φ/K violation; J* threshold met.
- **AMBER**: `0.20 ≤ P < 0.60` (Bronze/Red) or gate warnings.
- **FAIL**: `P < 0.20` (Black) or any Φ/K violation; J-BLACK.

## 7. Implementation

### 7.1 Repository Layout

```
/TERVYX
├─ protocol/
│  ├─ schemas/                # JSON-Schema (entry, simulation, citations)
│  └─ taxonomy/               # tel5_categories@v1.0.0.json (TEL-5 fixed)
├─ entries/
│  └─ nutrient/magnesium-glycinate/sleep/v1/
│     ├─ entry.jsonld         # Final output
│     ├─ simulation.json      # MC summary
│     ├─ evidence.csv         # Evidence table
│     └─ citations.json       # DOI/PMID/bibliography
├─ engine/
│  ├─ mc_meta.py              # Random-effects + Monte Carlo
│  ├─ tel5_rules.py           # P(effect>δ) → TEL-5 tier
│  ├─ gates.py                # Φ/R/J/K/L gates
│  └─ schema_validate.py      # Schema validation
└─ .github/workflows/ci.yml   # CI pipeline
```

### 7.2 CI Pipeline

```yaml
name: TERVYX Build Pipeline
on: [pull_request, workflow_dispatch, schedule]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt

      - name: Validate Schemas
        run: python -m engine.schema_validate

      - name: Monte Carlo Simulation
        run: python -m engine.mc_meta --all

        # TEL-5 rule application
      - name: Apply TEL-5 Rules
        run: python -m engine.tel5_rules --apply

      - name: Journal-Trust Snapshot
        run: python -m engine.journal_trust --snapshot protocol/journal_trust/

      - name: Gate Governance Check
        run: python -m engine.gates --validate-all

      - name: Reproducibility Check
        run: python scripts/repro_check.py

      - name: Build Artifacts (JSON-LD/BibTeX/CSL)
        run: python scripts/build_artifacts.py

      - name: Generate DOI Metadata
        run: python scripts/zenodo_metadata.py

      - name: Audit Hash Chain
        run: python scripts/audit_chain.py --verify
```

### 7.3 Security

No secrets are committed to the public repository. Crawling/extraction runs on private workers; public updates are merged via PR.

## 8. Evaluation

### 8.1 Pilot

**Entries:** magnesium glycinate, omega-3, saw palmetto, melatonin, creatine.  
**Categories:** sleep, cognition, mental health, renal safety, cardiovascular.

### 8.2 Metrics

- Accuracy/AUROC; Macro-F1 (with emphasis on FAIL detection)
- Calibration (ECE/Brier)
- Label stability (±1 volatility)
- Rebuild latency/cost
- Appeals SLA

### 8.3 Expected Outcomes (pilot snapshot)

| Substance | Category | P(effect>δ) | Tier | Label | Limiting factor |
|-----------|----------|-------------|------|-------|----------------|
| Magnesium glycinate | Sleep | 0.683 | Silver | **PASS** | Moderate evidence |
| Magnesium glycinate | Cognition | 0.340 | Red | **AMBER** | Low confidence |
| Magnesium glycinate | Renal improvement | N/A | Black | **FAIL** | Φ violation (category misrouting) |
| Omega-3 | Cardiovascular | 0.820 | Gold | **PASS** | High-quality evidence |
| Melatonin | Sleep | 0.915 | Gold | **PASS** | Strong evidence |

## 9. Limitations and Ethics

- Coverage of non-English literature; observational biases; value choices in MCID δ.
- To prevent misuse, labels/badges (SVG) include DOI signatures and verification scripts.
- Commercial use follows a usage guide; public-interest research gets permissive access.

**Medical disclaimer:** This work does not constitute medical advice; it does not replace clinical diagnosis or treatment.

## 10. Conclusion

TERVYX integrates quantification, labeling, and auditability into a standard that preserves patent-level logic while enabling evolution. The protocol aims to serve as a de facto citation layer for academia, media, platforms, and LLMs—anchored by open governance and reproducible artifacts.

## Data & Code Availability

Protocol, engine, entries, and schemas will be released with DOIs. All `/entry/{id}` responses include `preferred_citation, bibtex, csl_json, doi, version, audit_hash, llm_hint, policy_fingerprint`.

- **Code repository:** GitHub (MIT License)
- **Data repository:** Zenodo (CC BY 4.0)
- **Protocol DOI:** 10.5281/zenodo.XXXXX (pending)
- **Software DOI:** 10.5281/zenodo.YYYYY (pending)

## Competing Interests

The author is the applicant/inventor of "Verification of Non-scientific Health-Information Claims — GGP-based Hybrid Control," filed in Korea.

- **Application no.:** 10-2025-0143351 (KR)
- **Filing date:** 2025-10-01
- **Receipt no.:** 1-1-2025-1119765-45
- **DAS Access:** F05F
- **ORCID:** 0009-0005-7640-2510

This did not unduly influence the interpretation of results.

## Ethics Approval

No human subjects or personal data were collected; only public literature and metadata were used.

## Acknowledgments

We thank the open-access data/journal policies and the broader open ecosystem.

---

**Version:** v1.0.2 (2025-10-15, KST) — Rename to TERVYX; Silver=PASS; direction unification; 5-tier (TEL-5); J* normalization + BLACK pre-mask; English L-rules; formal DAG propagation; policy_fingerprint in artifacts.

**Trademarks:** "TERVYX", "TERVYX Evidence Levels (TEL-5)", and "Journal-Trust Oracle" are pending/registered trademarks.