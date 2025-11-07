# TERVYX Category Restructuring Proposal for Nature Publication

## Executive Summary

The current category structure has conceptual inconsistencies that may undermine the credibility of a Nature publication. This document proposes a clinically-oriented restructuring aligned with evidence-based medicine principles.

---

## Current Issues

### 1. Domain vs Category Confusion

**Problem**: Directory structure uses academic domains (behavioral, psychological, neurological) while the actual evaluation categories are clinical outcomes (sleep, cognition, mental_health).

**Impact**:
- Confusing for reviewers and users
- "substance" field in entry_requirements.json is semantically incorrect
- Mixed abstraction levels (nutrient is a substance type, not a domain)

### 2. Entry Distribution Imbalance

```
Current (967 entries):
metabolic:      253 (26%) - Overrepresented
physiological:  195 (20%)
immune:         146 (15%)
psychological:  130 (13%)
neurological:   120 (12%)
behavioral:     119 (12%)
nutrient:         1 (<1%) - Critical gap
safety:           3 (<1%) - Critical gap
```

**Critical Gaps**:
- **Nutrient interventions**: Only 1 entry (should be 100+)
- **Safety assessments**: Only 3 entries (should be 80+)

### 3. Category Distribution in Requirements

```
Actual categories (from entry_requirements.json):
mental_health:    30 (15%)
cardiovascular:   29 (14.5%)
metabolic:        28 (14%)
sleep:            20 (10%)
immune:           20 (10%)
cognition:        20 (10%)
inflammation:     15 (7.5%)
longevity:        15 (7.5%)
musculoskeletal:  14 (7%)
immune_health:     6 (3%)
renal_safety:      3 (1.5%)
```

---

## Proposed Restructure

### Option A: Clinical Outcome Categories (Recommended for Nature)

Organize by **clinical endpoints** rather than biological systems:

```
Clinical Categories (12):
1. cardiovascular_health    - BP, lipids, CVD risk
2. metabolic_health         - Glucose, insulin, HbA1c
3. cognitive_function       - Memory, attention, executive function
4. mental_wellbeing         - Depression, anxiety, mood
5. sleep_quality           - Insomnia, sleep architecture
6. immune_resilience       - Infection resistance, immune markers
7. inflammatory_status     - CRP, cytokines, inflammation
8. musculoskeletal_health  - Strength, joint function, pain
9. renal_function          - eGFR, creatinine, kidney safety
10. longevity_biomarkers   - Telomeres, biological age
11. nutrient_status        - Deficiency correction, bioavailability
12. safety_endpoints       - Adverse events, contraindications
```

**Directory Structure:**
```
entries/
├── cardiovascular_health/
│   ├── omega3-cvd-epa-dha/
│   ├── coq10-cvd-ubiquinone/
│   └── ...
├── metabolic_health/
│   ├── berberine-t2d-glucose/
│   ├── chromium-insulin-picolinate/
│   └── ...
├── cognitive_function/
│   ├── bacopa-cognition-bacosides/
│   ├── lions-mane-ngf-hericenones/
│   └── ...
└── ...
```

### Option B: Evidence-Type Categories

Organize by **intervention type** + **outcome**:

```
Evidence Categories (8):
1. dietary_interventions    - Nutrients, supplements, foods
2. behavioral_interventions - Exercise, meditation, sleep hygiene
3. pharmacological         - Drugs, nutraceuticals with drug-like effects
4. lifestyle_modifications - Diet patterns, stress management
5. mind_body_practices     - Yoga, tai chi, mindfulness
6. environmental_factors   - Light exposure, temperature, air quality
7. social_interventions    - Support groups, community engagement
8. safety_assessments      - Contraindications, adverse events
```

---

## Recommended Action Plan

### Phase 1: Restructure Categories (Week 1)

1. **Adopt Option A** (Clinical Outcome Categories)
   - More aligned with medical literature standards
   - Easier for Nature reviewers to evaluate
   - Better for clinician/patient comprehension

2. **Update taxonomy files:**
   ```bash
   protocol/taxonomy/categories_v2.yaml
   ```

3. **Refactor directory structure:**
   ```bash
   entries/cardiovascular_health/
   entries/metabolic_health/
   ...
   ```

4. **Fix semantic errors:**
   - Remove "substance" field from entry_requirements.json
   - Replace with "intervention_type" and "outcome_category"

### Phase 2: Fill Critical Gaps (Week 2)

**Target: 1,200+ entries**

Generate entries for underrepresented categories:

```
Priority Additions:
1. nutrient_status:         150 entries (from 1)
   - Vitamin D, B12, Iron, Magnesium, Zinc, etc.

2. safety_endpoints:        100 entries (from 3)
   - Contraindications, drug interactions, adverse events

3. renal_function:          50 entries (from current 3)
   - Nephrotoxicity, kidney protection

4. immune_resilience:       50 entries
   - Infection prevention, immune support

5. Balance existing:        ~100 entries
   - Redistribute to maintain clinical relevance

Total Target: 1,200 entries (vs current 967)
```

### Phase 3: Enhance Clinical Validity (Week 3)

1. **Add population stratification:**
   - Age groups (pediatric, adult, elderly)
   - Disease states (healthy, at-risk, diseased)
   - Sex/gender considerations

2. **Strengthen safety documentation:**
   - Comprehensive contraindication matrix
   - Drug-nutrient interaction database
   - Pregnancy/lactation safety grades

3. **Improve outcome measures:**
   - Validated clinical scales (MMSE, PHQ-9, etc.)
   - Biomarker ranges with clinical context
   - Minimal clinically important differences (MCID)

---

## Implementation Strategy

### Step 1: Create New Taxonomy

```yaml
# protocol/taxonomy/clinical_categories_v2.yaml

version: "v2.0.0"
taxonomy_type: "clinical_outcomes"
last_updated: "2025-11-07"

categories:
  cardiovascular_health:
    delta: 2.0
    delta_units: "MD (mmHg for BP)"
    primary_outcomes:
      - systolic_blood_pressure
      - ldl_cholesterol
      - triglycerides
      - cardiovascular_events
    population_focus: "Adults with CVD risk"
    safety_priority: "high"

  metabolic_health:
    delta: 0.25
    delta_units: "SMD"
    primary_outcomes:
      - fasting_glucose
      - hba1c
      - insulin_sensitivity
      - body_composition
    population_focus: "Adults with metabolic syndrome"
    safety_priority: "high"

  cognitive_function:
    delta: 0.15
    delta_units: "SMD"
    primary_outcomes:
      - memory_performance
      - attention_span
      - executive_function
      - processing_speed
    population_focus: "Adults with cognitive concerns"
    safety_priority: "medium"

  # ... (continue for all 12 categories)
```

### Step 2: Migration Script

```python
# tools/migrate_to_clinical_categories.py

DOMAIN_TO_CATEGORY_MAP = {
    "behavioral/sleep": "sleep_quality",
    "behavioral/cognition": "cognitive_function",
    "psychological/mental_health": "mental_wellbeing",
    "physiological/cardiovascular": "cardiovascular_health",
    "metabolic/metabolic": "metabolic_health",
    "immune/immune": "immune_resilience",
    "immune/inflammation": "inflammatory_status",
    "physiological/musculoskeletal": "musculoskeletal_health",
    "safety/renal_safety": "renal_function",
    "metabolic/longevity": "longevity_biomarkers",
    "nutrient/*": "nutrient_status",
    "safety/*": "safety_endpoints"
}
```

### Step 3: Generate Missing Entries

Target interventions for new entries:

**Nutrient Status (150 new):**
- Vitamin D (25 entries across deficiency states)
- B-Complex (20 entries)
- Magnesium (15 entries)
- Zinc (12 entries)
- Iron (12 entries)
- Calcium (10 entries)
- Omega-3 (20 entries)
- Vitamin C (10 entries)
- Vitamin E (8 entries)
- Others (18 entries)

**Safety Endpoints (100 new):**
- Hepatotoxicity markers (20 entries)
- Nephrotoxicity markers (20 entries)
- Drug interactions (25 entries)
- Contraindications (20 entries)
- Adverse event profiles (15 entries)

### Step 4: Update Documentation

Files to update:
- README.md
- IMPLEMENTATION_SUMMARY.md (Korean)
- AI-INTEGRATION-GUIDE.md
- policy.yaml (categories section)
- .tervyx-metadata.json
- schema.org.jsonld

---

## Expected Outcomes

### For Nature Publication

✅ **Clinical Credibility**
- Categories align with medical literature
- Outcome-focused organization
- Comprehensive safety coverage

✅ **Methodological Rigor**
- Balanced representation across health domains
- Adequate sample sizes per category
- Population stratification

✅ **Practical Utility**
- Usable by clinicians and patients
- Clear intervention-outcome relationships
- Safety-first emphasis

### Metrics After Restructure

```
Total Entries:          1,200+ (from 967)
Categories:             12 clinical outcomes
Avg per category:       100 entries (min: 50, max: 150)
Safety coverage:        100+ entries (from 3)
Nutrient coverage:      150+ entries (from 1)
Population diversity:   3+ age groups, 2+ disease states per category
```

---

## Timeline

**Week 1**: Category restructure + taxonomy update
**Week 2**: Generate 250+ new entries (focus: nutrient + safety)
**Week 3**: Validate all entries + update documentation
**Week 4**: Final review + prepare Nature submission package

---

## Recommendation

**Proceed with Option A (Clinical Outcome Categories)** for the following reasons:

1. ✅ Aligned with Nature Medicine/Nature Human Behaviour standards
2. ✅ Clinically interpretable for medical reviewers
3. ✅ Practical for end-users (clinicians, patients, AI systems)
4. ✅ Clear mapping from interventions → outcomes → evidence
5. ✅ Enables population-specific sub-analyses

**Critical**: Fill nutrient and safety gaps before Nature submission. 1,200+ entries with balanced distribution will strengthen the manuscript significantly.

---

## Next Steps

Please confirm:
1. Approve Option A (Clinical Outcome Categories)?
2. Target entry count: 1,200+?
3. Priority: Nutrient + Safety entries first?
4. Timeline: 4 weeks to restructure + generate?

Once confirmed, I will:
1. Create new taxonomy (clinical_categories_v2.yaml)
2. Build migration script
3. Generate 250+ new entries
4. Validate entire dataset
5. Update all documentation for Nature submission
