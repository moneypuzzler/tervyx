# Real-Data TERVYX System

## 🎯 Overview

This directory contains the **production-ready Real-Data TERVYX System** - a complete pipeline for generating TERVYX Protocol v1.0 entries using actual scientific literature instead of synthetic data.

## 🏗️ System Architecture

```
Query (substance + outcome)
    ↓
📚 PubMed Search & Metadata Extraction
    ↓
🤖 AI-Powered Abstract Analysis (Gemini)
    ↓
🏛️ Journal Quality Assessment
    ↓
📊 Real Meta-Analysis (REML + Monte Carlo)
    ↓
🎯 TEL-5 Classification & Entry Generation
```

## 📁 Components

### Core Pipeline Components

1. **`real_tervyx_architecture.py`** - System architecture overview and data models
2. **`pubmed_integration.py`** - PubMed E-utilities API integration for paper search and metadata
3. **`ai_abstract_analyzer.py`** - Gemini AI-powered abstract analysis and gate evaluation
4. **`journal_quality_db.py`** - Comprehensive journal quality assessment database
5. **`real_meta_analysis.py`** - Real evidence extraction and automated meta-analysis
6. **`real_tervyx_pipeline.py`** - **Main integrated pipeline for production use**

### Key Features

- **Real Literature Search**: PubMed E-utilities API with sophisticated query construction
- **AI-Powered Analysis**: Gemini 1.5 Flash for cost-effective abstract analysis
- **Journal Quality Assessment**: Multi-source journal reputation, impact factors, predatory detection
- **Automated Meta-Analysis**: REML + Monte Carlo using real extracted effect sizes
- **Production-Ready**: Error handling, rate limiting, batch processing, validation

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Set required environment variables
export GEMINI_API_KEY="your-gemini-api-key"
export TERVYX_EMAIL="your-email@domain.com"
export NCBI_API_KEY="your-ncbi-key"  # Optional, but recommended
```

### 2. Single Entry Generation

```python
from system.real_tervyx_pipeline import RealTERVYXPipeline

pipeline = RealTERVYXPipeline(
    email="your-email@domain.com",
    gemini_api_key="your-gemini-api-key"
)

# Generate entry for melatonin + sleep
entry = await pipeline.generate_entry("melatonin", "sleep")

if 'error' not in entry:
    print(f"Success: TEL-{entry['tier']} entry generated")
    print(f"Evidence: {entry['evidence_summary']['n_studies']} studies")
else:
    print(f"Failed: {entry['error']}")
```

### 3. Batch Generation

```bash
# Test single entry
cd /home/user/webapp
python -m system.real_tervyx_pipeline

# Full production run (15+ entries)
python -m system.real_tervyx_pipeline full
```

## 📊 Pipeline Steps Detailed

### Step 1: PubMed Literature Search

```python
# Sophisticated query construction with synonyms
pmids = await pubmed_api.search_papers(
    substance="melatonin",
    outcome="sleep", 
    max_results=100
)
# Returns: List of PMIDs for relevant papers
```

**Features:**
- Multi-synonym substance name expansion
- Outcome-specific search terms
- Study type filtering (RCT, meta-analysis, systematic review)
- Quality filters (English, recent, human studies, has abstract)

### Step 2: Paper Metadata Extraction

```python
papers = await pubmed_api.fetch_detailed_metadata(pmids)
```

**Extracted Data:**
- Title, abstract, authors, journal
- Publication year, DOI, PMID
- MeSH terms, publication types
- Journal ISSN for quality assessment

### Step 3: AI Abstract Analysis

```python
analyses = await ai_analyzer.analyze_batch(
    papers=papers,
    substance="melatonin",
    outcome_category="sleep"
)
```

**AI Extracts:**
- **Gate Evaluations**: Φ, R, J, K, L scores with reasoning
- **Quantitative Data**: Effect sizes, sample sizes, CIs, p-values
- **Study Characteristics**: Design, population, duration, risk of bias
- **Relevance Assessment**: Inclusion recommendation and confidence

### Step 4: Journal Quality Assessment

```python
assessment = await journal_db.assess_journal(
    issn="1389-9457",
    title="Sleep Medicine"
)
```

**Quality Factors:**
- Impact Factor (JCR 2023, 5-year)
- Predatory journal detection (Beall's list, heuristics)
- Database indexing (PubMed, Scopus, Web of Science)
- Retraction rates and publisher reputation
- **Output**: GOLD/SILVER/BRONZE/QUESTIONABLE/PREDATORY

### Step 5: Real Meta-Analysis

```python
entry = await generate_real_tervyx_entry(
    substance="melatonin",
    outcome_category="sleep", 
    analyses=ai_analyses,
    journal_assessments=journal_quality
)
```

**Meta-Analysis Process:**
1. **Standardization**: Convert various effect sizes to SMD
2. **Quality Filtering**: Remove low-quality/predatory studies  
3. **Effect Harmonization**: Ensure consistent benefit direction
4. **REML + Monte Carlo**: Use existing TERVYX engine
5. **Gate Evaluation**: Aggregate gates based on real studies
6. **TEL-5 Classification**: Apply safety-first monotonicity rules

## 🎯 Output Format

### Generated Entry Structure

```json
{
  "@context": "https://schema.org/",
  "@type": "Dataset",
  "id": "nutrient:melatonin:sleep:v1",
  "title": "Melatonin — Sleep",
  "category": "sleep",
  "tier": "Gold",
  "label": "PASS", 
  "P_effect_gt_delta": 0.847,
  "gate_results": {
    "phi": "PASS",
    "r": "PASS", 
    "j": 0.82,
    "k": "PASS",
    "l": "PASS"
  },
  "evidence_summary": {
    "n_studies": 8,
    "total_n": 1247,
    "I2": 23.4,
    "tau2": 0.018,
    "mu_hat": 0.64,
    "mu_CI95": [0.41, 0.87]
  },
  "real_studies": [
    {
      "study_id": "12345678",
      "effect_size": 0.72,
      "total_n": 156,
      "study_type": "RCT",
      "risk_of_bias": "LOW"
    }
  ],
  "quality_metrics": {
    "rct_percentage": 87.5,
    "mean_journal_quality": 0.78,
    "data_extraction_confidence": 0.85
  },
  "pipeline_metadata": {
    "processing_time_seconds": 342.1,
    "pubmed_search_results": 89,
    "successful_ai_analyses": 12,
    "data_sources": {
      "literature_search": "PubMed E-utilities",
      "ai_analysis": "Gemini 1.5 Flash",
      "journal_quality": "Multi-source aggregated",
      "meta_analysis": "TERVYX REML+MC Engine"
    }
  },
  "data_source": "real_literature"
}
```

## 🔧 Configuration

### API Requirements

1. **Gemini API Key** (Required)
   - Get from: https://aistudio.google.com/app/apikey
   - Model used: `gemini-1.5-flash` (cost-effective)
   - Rate limit: ~60 requests/minute

2. **NCBI API Key** (Optional but recommended)
   - Get from: https://www.ncbi.nlm.nih.gov/account/settings/
   - Increases rate limit from 3/sec to 10/sec
   
3. **Email Address** (Required)
   - Required by PubMed E-utilities API
   - Used for API identification and rate limiting

### System Requirements

```python
# Required packages
aiohttp          # Async HTTP requests
xml.etree.ElementTree  # XML parsing
sqlite3          # Journal quality database
numpy, scipy     # Statistical computations
```

### Performance Configuration

```python
config = {
    'max_papers_search': 100,        # PubMed search limit
    'max_papers_analyze': 30,        # AI analysis limit
    'min_papers_meta_analysis': 3,   # Minimum for meta-analysis
    'analysis_timeout_minutes': 30,  # Per-entry timeout
    'relevance_threshold': 0.6,      # Flash-Lite screening cut-off
    'confidence_threshold': 0.7,     # Flash/Pro inclusion cut-off
    'batch_delay_seconds': 30,       # Cool-down between batch entries
}
```

## 📊 Quality Assurance

### Data Quality Checks

1. **Literature Search Quality**
   - Minimum 2 relevant papers required
   - Sophisticated query with substance synonyms
   - Study type and quality filters applied

2. **AI Analysis Quality**  
   - Relevance screening threshold ≥0.6 (Flash-Lite)
   - Confidence threshold ≥0.7 (Flash → Pro retry)
   - Inclusion requires analyzer recommendation + quality checks
   - Cross-validation with multiple AI assessments

3. **Journal Quality Control**
   - Predatory journal detection and exclusion
   - Impact factor and indexing verification
   - Publisher reputation assessment
   - Only includable PMIDs trigger live journal queries (cost-aware)

4. **Meta-Analysis Quality**
   - Effect size standardization and harmonization
   - Heterogeneity assessment (I² reporting)
   - Sensitivity analysis and bias assessment

### Safety Features

- **Safety-First Monotonicity**: Φ/K violations override positive J scores
- **Predatory Journal Blocking**: Automatic exclusion of known predatory sources
- **Effect Size Validation**: Extreme effects flagged and reviewed
- **Confidence Reporting**: All analyses include confidence metrics

## 🧪 Testing

### Validation Tests

```bash
# Test pipeline configuration
python -c "
from system.real_tervyx_pipeline import RealTERVYXPipeline
pipeline = RealTERVYXPipeline('test@example.com', 'test-key')
print(pipeline.validate_configuration())
"

# Test individual components
cd /home/user/webapp
python -m system.pubmed_integration      # Test PubMed API
python -m system.ai_abstract_analyzer    # Test AI analysis  
python -m system.journal_quality_db      # Test journal assessment
python -m system.real_meta_analysis      # Test meta-analysis
```

### Known Limitations

1. **AI Analysis Dependency**: Quality depends on Gemini API accuracy
2. **Effect Size Conversion**: Some conversions use approximations
3. **Journal Database**: Requires periodic updates for accuracy
4. **Rate Limiting**: PubMed and Gemini APIs have usage limits
5. **Language**: Currently optimized for English-language papers

## 🔄 Comparison: Fake vs. Real System

| Aspect | Fake System | Real System |
|--------|-------------|-------------|
| **Data Source** | Synthetic generation | PubMed literature |
| **Papers** | Simulated abstracts | Real scientific papers |
| **Effect Sizes** | Random distributions | AI-extracted from abstracts |
| **Journal Quality** | Preset categories | Real impact factors & assessment |
| **Gate Evaluation** | Rule-based simulation | AI analysis of actual content |
| **Processing Time** | ~1 second | ~5-10 minutes per entry |
| **API Costs** | $0 | ~$0.50-2.00 per entry |
| **Accuracy** | Statistically realistic | Based on actual research |
| **Reproducibility** | Perfect (deterministic) | High (real data + audit hashes) |

## 🚀 Production Deployment

### Recommended Usage Pattern

1. **Pilot Phase**: Generate 10-15 high-priority substances
2. **Validation Phase**: Manual review of generated entries
3. **Production Phase**: Automated batch generation with monitoring
4. **Maintenance**: Regular updates to journal quality database

### Cost Estimation

- **Gemini API**: ~$0.50-2.00 per entry (depending on paper count)
- **Processing Time**: 5-10 minutes per entry
- **Success Rate**: Expected 70-80% for well-studied substances

### Monitoring & Quality Control

- All entries include confidence metrics and audit trails
- Failed analyses provide detailed error information
- Journal quality assessments cached to reduce redundant API calls
- Processing metadata enables performance optimization

## 📈 Future Enhancements

1. **Full-Text Analysis**: Beyond abstracts to full papers
2. **Cross-Database Integration**: Scopus, Web of Science, Cochrane
3. **ML Enhancement**: Custom models for health information extraction
4. **Real-Time Updates**: Continuous literature monitoring
5. **Multi-Language Support**: Non-English literature integration

---

## 🎯 Getting Started

To begin using the Real-Data TERVYX System:

1. Set up environment variables (API keys, email)
2. Run validation test: `python -m system.real_tervyx_pipeline`
3. Generate your first real entry with a well-studied substance
4. Review the output for quality and accuracy
5. Scale to batch processing for multiple substances

The Real-Data TERVYX System represents the evolution from prototype to production-ready evidence evaluation platform, providing actual scientific rigor while maintaining the TERVYX Protocol's safety-first approach and patent-protected methodologies.