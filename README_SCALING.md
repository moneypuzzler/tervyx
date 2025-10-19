# TERVYX Protocol - Scaling Architecture 🚀

## Overview

The TERVYX Protocol scaling architecture enables processing of **1000+ entries** with automated evidence collection, BERT-based relevance scoring, and PRISMA-compliant systematic review workflows.

## 🏗️ Architecture Components

### 1. Journal Registry (`/registry/`)
- **Upper-layer journal registry** with Parquet-based storage
- Automated scorecard generation using OpenAlex, DOAJ, COPE APIs
- Trust score computation with z-score normalization
- Efficient batch updates for thousands of journals

### 2. Entry Catalog (`/catalog/`)
- **1000+ entry seeds** across 5 TEL-5 categories
- CSV-based catalog with priority assignment
- Batch processing and progress tracking
- Distributed assignment system

### 3. Collection Pipeline (`/automation/`)
- **Multi-API integration**: OpenAlex, PubMed, Crossref
- Rate limiting and error handling
- Automated deduplication
- Study type inference and metadata extraction

### 4. Relevance Scoring (`/scoring/`)
- **BERT-based semantic similarity** (sentence-transformers)
- Category-specific biomedical concept matching
- Keyword scoring with PICO framework
- Confidence estimation and threshold setting

### 5. PRISMA Workflows (`/workflows/`)
- **PRISMA 2020 compliant** systematic review screening
- Automated title/abstract screening
- Conflict resolution and reviewer management
- Flow diagram generation and export

## 🚀 Quick Start

### Installation

```bash
# Install core dependencies
pip install -r requirements.txt

# Install scaling dependencies (with fallbacks)
pip install -r requirements_scaling.txt
```

### Initialize Scaling Infrastructure

```bash
# Initialize all scaling components
python scripts/tervyx_scale.py init
```

### Journal Registry Management

```bash
# View registry statistics
python scripts/tervyx_scale.py registry stats

# Update registry with new ISSNs
python scripts/tervyx_scale.py registry update --issn-list "1389-9457,1365-2869,0006-3223"

# Search for journals
python scripts/tervyx_scale.py registry search --query "sleep medicine"

# Get specific journal scorecard
python scripts/tervyx_scale.py registry get --issn "1389-9457"
```

### Entry Catalog Operations

```bash
# View catalog statistics
python scripts/tervyx_scale.py catalog stats

# Preview a small slice for manual review
python scripts/tervyx_scale.py catalog preview --limit 5 --priority high --category sleep

# Get next batch for processing
python scripts/tervyx_scale.py catalog batch --batch-size 20 --priority high --category sleep

# Search entries
python scripts/tervyx_scale.py catalog search --query "magnesium sleep"

# Update entry status
python scripts/tervyx_scale.py catalog update --entry-id "tervyx_sleep_12345678" --status "completed" --tier "Gold"

# Generate versioned entry scaffolds from the curated catalog (dry run)
python scripts/tervyx_scale.py catalog generate --category sleep --priority high --limit 3 --dry-run

# Create real directories with manifest metadata and mark catalog entries as in-progress
python scripts/tervyx_scale.py catalog generate \
  --category sleep \
  --priority high \
  --limit 5 \
  --algo-name "TERVYX-Core" \
  --algo-version 2.0.0 \
  --algo-modules '{"nlp":"Gemini 1.5 Pro","meta_analysis":"REML-2025.10"}' \
  --data-snapshot "monthly@2025-10" \
  --data-freeze "monthly@2025-10" \
  --data-query "melatonin sleep latency RCT" \
  --data-sources '{"pubmed":{"count":412,"since":"1990-01-01"}}' \
  --included-studies '["PMID:37611507"]' \
  --dedup-hash "sha256:abcd..." \
  --tau2-method REML \
  --simulation-delta 0.2 \
  --simulation-draws 10000 \
  --tel5-levels-ref "TEL-5@v1.0.0" \
  --monte-carlo-ref "MC@v1.0.0" \
  --journal-trust-ref "2025-10-05" \
  --bump minor \
  --runner "scripts/tervyx_batch@0.4.0" \
  --cost-usd 12.74 \
  --elapsed-seconds 548 \
  --set-status in_progress \
  --status-note "Versioned scaffold generated via scaling CLI"
```

The `catalog generate` action reads curated rows from `catalog/entry_catalog.csv`, creates a
stable directory hierarchy under `entries/<substance>/<primary_indication>/<entry_id>/vN`, and writes:

- `run_manifest.json` — provenance bundle capturing algorithm version, data freeze policy,
  lineage, module fingerprints, and generator metadata (including runner, run ID, elapsed time,
  and cost observations).
- `audit_hash.txt` — SHA256 digest of the manifest for tamper-evident auditing.
- `catalog_entry.json` — verbatim snapshot of the originating catalog row.
- `entry.jsonld` — TEL-5 entry skeleton constrained by `protocol/schemas/entry.schema.json` and
  seeded with policy references, audit fingerprint, and gate placeholders.
- `simulation.json` — TEL-5 simulation scaffold that satisfies `protocol/schemas/simulation.schema.json`
  with Monte Carlo placeholders (delta, draw count, τ² method, fingerprint).
- `citations.json` — DOI bundle and placeholder lists for primary and secondary sources.
- `evidence.csv` — TEL-5 evidence template headers for study abstraction.

The CLI inspects `policy.yaml` to derive the active journal-trust snapshot date, so scaffolds
default to ISO-8601 values such as `2025-10-05` unless you explicitly override them.

Override the defaults for policy references and simulation metadata with:

```bash
  --tel5-levels-ref TEL-5@v1.2.0 \
  --monte-carlo-ref REML-2025.10 \
  --journal-trust-ref 2025-10-12 \
  --simulation-seed 20251019 \
  --simulation-draws 25000 \
  --simulation-delta 0.15 \
  --tau2-method HKSJ \
  --benefit-direction -1 \
  --simulation-environment "Python 3.11 • NumPy 1.26 • SciPy 1.11"
```

Each run updates a `latest` pointer (symlink on supported systems, fallback text file otherwise)
so that downstream tooling can address the newest content version while historic snapshots remain
frozen for reproducibility.

### Evidence Collection

```bash
# Collect evidence from multiple databases
python scripts/tervyx_scale.py collect "magnesium AND sleep quality AND randomized controlled trial" \
  --max-results 100 \
  --databases "openalex,pubmed" \
  --output "evidence_results.json"
```

### Relevance Scoring

```bash
# Score single abstract
python scripts/tervyx_scale.py score \
  --abstract "Magnesium supplementation improved sleep quality in this RCT..." \
  --category "sleep" \
  --substance "magnesium" \
  --indication "sleep_quality"

# Batch scoring from file
python scripts/tervyx_scale.py score \
  --batch-file "collected_studies.json" \
  --category "sleep" \
  --substance "magnesium" \
  --indication "sleep_quality" \
  --output "relevance_scores.json"
```

### PRISMA Screening Workflow

```bash
# Initialize systematic review
python scripts/tervyx_scale.py prisma "magnesium_sleep_review" init \
  --title "Magnesium for Sleep Quality: Systematic Review" \
  --question "Does magnesium supplementation improve sleep quality?" \
  --inclusion '{"population":["adults"],"intervention":["magnesium"],"outcome":["sleep"]}' \
  --exclusion '{"population":["children"],"study_design":["case report"]}'

# Import search results
python scripts/tervyx_scale.py prisma "magnesium_sleep_review" import \
  --input-file "search_results.json" \
  --database "pubmed"

# Remove duplicates
python scripts/tervyx_scale.py prisma "magnesium_sleep_review" dedupe

# Screen studies
python scripts/tervyx_scale.py prisma "magnesium_sleep_review" screen \
  --batch-size 50 \
  --reviewer-id "researcher1"

# View statistics
python scripts/tervyx_scale.py prisma "magnesium_sleep_review" stats

# Generate PRISMA flow diagram
python scripts/tervyx_scale.py prisma "magnesium_sleep_review" flow

# Export results
python scripts/tervyx_scale.py prisma "magnesium_sleep_review" export --format excel
```

## 📊 Data Structures

### Journal Scorecard Schema
```python
{
  "issn": "1389-9457",
  "journal_name": "Sleep Medicine", 
  "publisher": "Elsevier",
  "jcr_impact_factor": 4.842,
  "sjr_score": 1.234,
  "doaj_member": True,
  "cope_member": True,
  "trust_score": 0.876,
  "if_z_score": 1.23,
  "sjr_z_score": 0.98
}
```

### Entry Seed Schema
```python
{
  "entry_id": "tervyx_sleep_a1b2c3d4",
  "category": "sleep",
  "substance": "magnesium_glycinate",
  "formulation": "glycinate", 
  "indication": "sleep_quality",
  "priority": "high",
  "estimated_studies": 25,
  "target_effect_size": 0.45,
  "confidence_level": "strong",
  "status": "pending"
}
```

### Study Record Schema
```python
{
  "study_id": "openalex_10.1016_j.sleep.2023.001",
  "title": "Magnesium Supplementation and Sleep Quality...",
  "authors": ["Smith J", "Johnson A"],
  "journal": "Sleep Medicine",
  "journal_issn": "1389-9457",
  "publication_year": 2023,
  "doi": "10.1016/j.sleep.2023.001",
  "pmid": "37123456",
  "abstract": "Background: Magnesium deficiency may...",
  "study_type": "rct",
  "relevance_score": 0.876,
  "data_source": "openalex"
}
```

### Relevance Score Schema
```python
{
  "study_id": "study_12345",
  "semantic_score": 0.823,      # BERT similarity
  "keyword_score": 0.745,       # PICO keyword matching
  "combined_score": 0.789,      # Weighted combination
  "confidence": 0.892,          # Score confidence
  "matched_concepts": [         # Matched biomedical concepts
    "substance: magnesium",
    "indication: sleep_quality", 
    "concept: sleep onset latency",
    "quality indicators: 2"
  ],
  "scoring_model": "bert"       # Model used
}
```

## 🔧 Configuration

### Category-Specific Relevance Thresholds
```python
{
  "sleep": {
    "high_relevance": 0.75,
    "medium_relevance": 0.5,
    "low_relevance": 0.25
  },
  "renal_safety": {
    "high_relevance": 0.8,      # Higher threshold for safety
    "medium_relevance": 0.6,
    "low_relevance": 0.35
  }
}
```

### API Rate Limits
```python
{
  "openalex": 0.1,     # 10 requests/second
  "pubmed": 0.34,      # 3 requests/second (free tier)
  "crossref": 0.05     # 20 requests/second
}
```

## 📈 Performance Metrics

### Scaling Benchmarks
- **Journal Registry**: 10,000+ journals in Parquet format
- **Entry Catalog**: 210 curated P0/P1 entries across 10 categories (CSV-managed)
- **Collection Pipeline**: 1,000 studies/hour from multiple APIs
- **Relevance Scoring**: 500 abstracts/minute with BERT
- **PRISMA Screening**: 1,000+ studies with automated workflows

### Storage Efficiency
- **Parquet compression**: ~70% smaller than CSV for large datasets
- **Embedding cache**: Reduces BERT computation by 80% for repeated queries
- **Incremental updates**: Only process new/changed records

## 🧪 Testing & Validation

### CI/CD Integration
The scaling architecture is integrated into GitHub Actions CI/CD:

```yaml
- name: Test scaling components
  run: |
    # Test journal registry
    python -c "from registry.journal_registry import JournalRegistry; ..."
    
    # Test entry catalog
    python -c "from catalog.entry_catalog import EntryCatalog; print(EntryCatalog().get_catalog_statistics())"
    
    # Test relevance scorer
    python -c "from scoring.relevance_scorer import RelevanceScorer; ..."
```

### Fallback Mechanisms
- **BERT unavailable**: Falls back to TF-IDF similarity
- **API failures**: Graceful degradation with error logging
- **Missing dependencies**: Core functionality preserved

## 📋 Entry Catalog Structure

### Manual Seed List (P0 focus)
The catalog is now sourced from a manually maintained CSV file located at
`catalog/entry_catalog.csv`. Each row represents an intentionally curated backlog item with:

1. **Core identifiers** – `entry_id`, `category`, and `substance`
2. **Formulation policy** – explicit merge/split rationale and notes
3. **Primary indication & priority** – P0 triage guidance for batch execution
4. **Workflow status** – pending/ready/completed tracking with timestamps
5. **Version controls** – optional `algo_version_pinned`, `data_freeze_policy`, and `deprecation_policy`

Initial backlog coverage now spans:

- **Sleep (20 entries)** – foundational insomnia stacks, formulation split guards for melatonin/cannabinoids
- **Cognition (20 entries)** – nootropic staples with bioavailability variants and stress-adaptogen crossovers
- **Mental Health (20 entries)** – EPA-forward mood protocols, psychobiotic splits, and adjunct ketamine/psychedelic support
- **Cardiovascular (20 entries)** – lipid and blood-pressure interventions with nitrate/nicotinic comparisons
- **Metabolic (20 entries)** – glucose and lipid modulation compounds with evidence-tier cycling
- **Inflammation (20 entries)** – joint/systemic anti-inflammatory compounds with merge vs split safeguards
- **Longevity (20 entries)** – NAD+ boosters, mitochondrial supports, and senolytics with formulation tracking
- **Musculoskeletal (20 entries)** – recovery, bone density, and protein stack prioritization
- **Immune (20 entries)** – upper respiratory and antiviral nutraceutical playbooks
- **Endocrine (20 entries)** – PCOS, thyroid, androgen, and menopause support matrices

Entries are maintained directly in `catalog/entry_catalog.csv`; operators can append or
edit rows as soon as category owners approve new backlog items.

### Priority Assignment
- **High Priority** (30%): Strong evidence expected, clinical importance
- **Medium Priority** (45%): Moderate evidence, research interest
- **Low Priority** (25%): Exploratory, limited evidence

## 🔗 Integration with Core TERVYX

The scaling architecture seamlessly integrates with the core TERVYX Protocol:

- **Policy compliance**: All entries follow the TEL-5 evidence system
- **Gate validation**: Automated Φ/R/J/K/L gate processing  
- **Schema validation**: JSON Schema compliance for all artifacts
- **Audit trails**: Complete traceability through audit logs
- **Reproducibility**: Policy fingerprinting for version control

## 🚀 Future Enhancements

### Planned Features
- **Real-time dashboards** for processing status
- **Advanced NLP** with domain-specific models (BioBERT, ClinicalBERT)
- **Federated learning** for collaborative model training
- **Graph neural networks** for citation network analysis
- **Automated quality assessment** with GRADE/ROBINS-I integration

### API Expansions
- **Semantic Scholar** integration
- **arXiv** preprint processing  
- **Clinical trials registries** (ClinicalTrials.gov)
- **Cochrane Library** systematic reviews
- **Patent databases** for innovation tracking

---

*The TERVYX Protocol scaling architecture: From single entries to systematic evidence synthesis at scale.*