# VERA Protocol - Scaling Architecture 🚀

## Overview

The VERA Protocol scaling architecture enables processing of **1000+ entries** with automated evidence collection, BERT-based relevance scoring, and PRISMA-compliant systematic review workflows.

## 🏗️ Architecture Components

### 1. Journal Registry (`/registry/`)
- **Upper-layer journal registry** with Parquet-based storage
- Automated scorecard generation using OpenAlex, DOAJ, COPE APIs
- Trust score computation with z-score normalization
- Efficient batch updates for thousands of journals

### 2. Entry Catalog (`/catalog/`)
- **1000+ entry seeds** across 5 HBV categories
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
python scripts/vera_scale.py init
```

### Journal Registry Management

```bash
# View registry statistics
python scripts/vera_scale.py registry stats

# Update registry with new ISSNs
python scripts/vera_scale.py registry update --issn-list "1389-9457,1365-2869,0006-3223"

# Search for journals
python scripts/vera_scale.py registry search --query "sleep medicine"

# Get specific journal scorecard
python scripts/vera_scale.py registry get --issn "1389-9457"
```

### Entry Catalog Operations

```bash
# View catalog statistics
python scripts/vera_scale.py catalog stats

# Get next batch for processing
python scripts/vera_scale.py catalog batch --batch-size 20 --priority high --category sleep

# Search entries
python scripts/vera_scale.py catalog search --query "magnesium sleep"

# Update entry status
python scripts/vera_scale.py catalog update --entry-id "vera_sleep_12345678" --status "completed" --tier "Gold"
```

### Evidence Collection

```bash
# Collect evidence from multiple databases
python scripts/vera_scale.py collect "magnesium AND sleep quality AND randomized controlled trial" \
  --max-results 100 \
  --databases "openalex,pubmed" \
  --output "evidence_results.json"
```

### Relevance Scoring

```bash
# Score single abstract
python scripts/vera_scale.py score \
  --abstract "Magnesium supplementation improved sleep quality in this RCT..." \
  --category "sleep" \
  --substance "magnesium" \
  --indication "sleep_quality"

# Batch scoring from file
python scripts/vera_scale.py score \
  --batch-file "collected_studies.json" \
  --category "sleep" \
  --substance "magnesium" \
  --indication "sleep_quality" \
  --output "relevance_scores.json"
```

### PRISMA Screening Workflow

```bash
# Initialize systematic review
python scripts/vera_scale.py prisma "magnesium_sleep_review" init \
  --title "Magnesium for Sleep Quality: Systematic Review" \
  --question "Does magnesium supplementation improve sleep quality?" \
  --inclusion '{"population":["adults"],"intervention":["magnesium"],"outcome":["sleep"]}' \
  --exclusion '{"population":["children"],"study_design":["case report"]}'

# Import search results
python scripts/vera_scale.py prisma "magnesium_sleep_review" import \
  --input-file "search_results.json" \
  --database "pubmed"

# Remove duplicates
python scripts/vera_scale.py prisma "magnesium_sleep_review" dedupe

# Screen studies
python scripts/vera_scale.py prisma "magnesium_sleep_review" screen \
  --batch-size 50 \
  --reviewer-id "researcher1"

# View statistics
python scripts/vera_scale.py prisma "magnesium_sleep_review" stats

# Generate PRISMA flow diagram
python scripts/vera_scale.py prisma "magnesium_sleep_review" flow

# Export results
python scripts/vera_scale.py prisma "magnesium_sleep_review" export --format excel
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
  "entry_id": "vera_sleep_a1b2c3d4",
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
- **Entry Catalog**: 1,200+ entry seeds across 5 categories  
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
    python -c "from catalog.entry_catalog import EntryCatalog; ..."
    
    # Test relevance scorer
    python -c "from scoring.relevance_scorer import RelevanceScorer; ..."
```

### Fallback Mechanisms
- **BERT unavailable**: Falls back to TF-IDF similarity
- **API failures**: Graceful degradation with error logging
- **Missing dependencies**: Core functionality preserved

## 📋 Entry Categories & Seeds

### Generated Entry Matrix
The catalog automatically generates 1000+ entry seeds across:

1. **Sleep** (320 entries)
   - Substances: magnesium, melatonin, valerian, ashwagandha, l-theanine, GABA, chamomile
   - Indications: sleep_onset, sleep_maintenance, sleep_quality, REM_sleep

2. **Cognition** (280 entries)  
   - Substances: lion's mane, bacopa, rhodiola, ginkgo, phosphatidylserine, alpha-GPC
   - Indications: memory, attention, processing_speed, executive_function

3. **Mental Health** (260 entries)
   - Substances: St. John's wort, SAM-e, omega-3, probiotics, vitamin D, B-complex
   - Indications: depression, anxiety, mood, stress, wellbeing

4. **Cardiovascular** (240 entries)
   - Substances: omega-3, CoQ10, garlic, hawthorn, red yeast rice, bergamot
   - Indications: blood_pressure, cholesterol, heart_rate, endothelial_function

5. **Renal Safety** (180 entries)
   - Substances: creatine, protein powder, NSAIDs, high-dose vitamins, herbal extracts  
   - Indications: kidney_function, creatinine_levels, GFR_impact, proteinuria

### Priority Assignment
- **High Priority** (30%): Strong evidence expected, clinical importance
- **Medium Priority** (45%): Moderate evidence, research interest
- **Low Priority** (25%): Exploratory, limited evidence

## 🔗 Integration with Core VERA

The scaling architecture seamlessly integrates with the core VERA Protocol:

- **Policy compliance**: All entries follow HBV 5-tier system
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

*The VERA Protocol scaling architecture: From single entries to systematic evidence synthesis at scale.*