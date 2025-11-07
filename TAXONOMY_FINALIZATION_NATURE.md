# TERVYX Taxonomy Finalization for Nature Submission

**Document Version:** v1.0.0
**Date:** 2025-11-07
**Status:** Structure finalized, ready for entry generation
**Target Journal:** Nature Methods / Nature Human Behaviour

---

## Executive Summary

TERVYX implements a **2-axis intervention-outcome taxonomy** that enables automated quality control of commercial health claims through policy-as-code governance. Unlike manual systematic review methods (GRADE, PRISMA), TERVYX uses deterministic gate protocols to reject pseudoscience automatically while preserving transparency and reproducibility.

**Key Innovation:**
- **Automated pseudoscience rejection** via global forbidden patterns in Φ gate
- **Intervention-based product categorization** aligned with commercial reality
- **Policy-as-code governance** ensuring reproducible, auditable decisions
- **1,000+ entry target** with priority-weighted distribution

---

## 1. Taxonomy Architecture

### 1.1 Two-Axis Design

```
┌─────────────────────────────────────────────────┐
│         OUTCOME AXIS (Clinical Effects)         │
├─────────────────────────────────────────────────┤
│  • sleep                                        │
│  • cognition                                    │
│  • mental_health (anxiety, depression, stress)  │
│  • cardiovascular                               │
│  • metabolic                                    │
│  • musculoskeletal                              │
│  • immune                                       │
│  • renal_safety (contraindications)             │
└─────────────────────────────────────────────────┘
                      ×
┌─────────────────────────────────────────────────┐
│      INTERVENTION AXIS (Product Types)          │
├─────────────────────────────────────────────────┤
│  • supplement         (oral, herbal)            │
│  • device_noninvasive (EMS, TENS, light, etc.)  │
│  • behavioral         (exercise, meditation)    │
│  • food               (whole foods, diets)      │
│  • pharmaceutical     (Rx, OTC)                 │
│  • procedure          (acupuncture, manual)     │
└─────────────────────────────────────────────────┘
```

**Rationale:**
- **Outcome axis** captures clinical intent (what condition is being addressed)
- **Intervention axis** captures product mechanism (how the treatment operates)
- **Cross-tabulation** enables population-specific analysis (e.g., "supplement efficacy vs. device efficacy for sleep")

---

## 2. Entry Requirements Structure

### 2.1 Schema

Each entry requirement specifies:

```json
{
  "intervention_type": "supplement | device_noninvasive | behavioral | food | pharmaceutical | procedure",
  "subcategory": "string (e.g., minerals, electrical_stimulation)",
  "product": "string (specific product name)",
  "product_variants": ["array of variants if applicable"],
  "outcomes": ["validated outcome categories"],
  "priority": "high | medium | low",
  "studies_estimate": "number (estimated RCTs/meta-analyses)",
  "notes": "optional context"
}
```

### 2.2 Priority Assignment

**High Priority (460 entries, 46%):**
- Consumer products with >20 peer-reviewed studies
- Examples: magnesium glycinate, omega-3 EPA/DHA, vitamin D3, melatonin, caffeine, tDCS, TENS

**Medium Priority (365 entries, 36.5%):**
- Emerging products with 10-20 studies
- Examples: ashwagandha KSM-66, berberine, infrared therapy, acupuncture for pain

**Low Priority (175 entries, 17.5%):**
- Niche products with <10 studies but plausible mechanism
- Examples: specific herbal extracts, novel device applications

---

## 3. Target Entry Distribution (1,020+ entries)

| Intervention Type   | Subcategories | Target Entries | High | Med | Low | Rationale                          |
|---------------------|---------------|----------------|------|-----|-----|------------------------------------|
| **supplement**      | 8             | 670            | 340  | 230 | 100 | Largest consumer market            |
| **device_noninvasive** | 5          | 110            | 35   | 50  | 25  | Growing evidence base              |
| **behavioral**      | 4             | 80             | 30   | 35  | 15  | Well-established interventions     |
| **food**            | 3             | 60             | 20   | 25  | 15  | Dietary patterns + bioactives      |
| **pharmaceutical**  | 1             | 40             | 30   | 10  | 0   | Approved indications only          |
| **procedure**       | 1             | 30             | 10   | 15  | 5   | Manual therapies with evidence     |
| **safety**          | N/A           | 100            | 50   | 50  | 0   | Contraindications, interactions    |
| **TOTAL**           |               | **1,090**      | 515  | 415 | 160 | Balanced distribution              |

### 3.1 Supplement Subcategories (670 entries)

| Subcategory         | Examples                          | Target |
|---------------------|-----------------------------------|--------|
| minerals            | magnesium, zinc, calcium, iron    | 80     |
| vitamins            | D3, B-complex, K2, folate         | 70     |
| amino_acids         | L-theanine, glycine, taurine      | 60     |
| omega_fatty_acids   | omega-3 EPA/DHA, omega-6          | 50     |
| herbal_adaptogen    | ashwagandha, rhodiola, ginseng    | 120    |
| herbal_nootropic    | bacopa, ginkgo, lion's mane       | 80     |
| probiotics          | specific strains, multi-strain    | 90     |
| compounds           | berberine, curcumin, resveratrol  | 120    |

### 3.2 Device Subcategories (110 entries)

| Subcategory             | Examples                     | Target |
|-------------------------|------------------------------|--------|
| electrical_stimulation  | EMS, TENS, tDCS, rTMS        | 40     |
| light_therapy           | red/NIR, blue light, UV      | 25     |
| thermal_therapy         | infrared, cold therapy       | 20     |
| mechanical_stimulation  | vibration plates, ultrasound | 15     |
| sound_therapy           | binaural beats, white noise  | 10     |

---

## 4. Φ Gate: Global Forbidden Patterns

### 4.1 Pseudoscience Rejection Mechanism

**Purpose:** Automatically reject products with implausible mechanisms **before** probabilistic evaluation.

**Implementation:** `protocol/phi_rules.yaml` → `forbidden_global` section

**8 Pattern Categories:**

1. **Germanium bracelets** (Korean + English)
   - Pattern: `(germanium.{0,20}(bracelet|band|jewelry)|게르마늄.{0,20}팔찌)`
   - Reason: No plausible physiological coupling mechanism

2. **Magnetic bracelets**
   - Pattern: `(magnetic.{0,20}(bracelet|band)|자석.{0,20}팔찌)`
   - Reason: Insufficient field strength for therapeutic effects

3. **Ion bands**
   - Pattern: `(ion.{0,20}(band|bracelet)|이온.{0,20}팔찌)`
   - Reason: No validated ion emission at therapeutic levels

4. **Copper bracelets** (systemic claims)
   - Pattern: `(copper.{0,20}bracelet.{0,40}(arthritis|pain|circulation))`
   - Reason: No transdermal absorption pathway at therapeutic dose

5. **Quantum pendants**
   - Pattern: `(quantum.{0,20}(pendant|necklace|jewelry))`
   - Reason: Misappropriation of quantum physics terminology

6. **Bioresonance devices**
   - Pattern: `(bioresonance|bio-resonance|바이오레조넌스)`
   - Reason: No validated biophysical mechanism

7. **Scalar wave products**
   - Pattern: `(scalar.{0,20}(energy|wave|field))`
   - Reason: Not recognized in physics literature

8. **Detox foot pads**
   - Pattern: `(detox.{0,20}foot.{0,20}(pad|patch))`
   - Reason: Color change is oxidation, not toxin extraction

### 4.2 Enforcement Logic

```python
def check_phi_gate(category, evidence_rows, substance="", claim_text=""):
    # Step 1: Check global forbidden patterns FIRST
    forbidden_global = load_phi_rules()["forbidden_global"]
    search_text = f"{substance} {claim_text}".lower()

    for pattern_entry in forbidden_global:
        if re.search(pattern_entry["pattern"], search_text, re.IGNORECASE):
            reason = pattern_entry["reason"]
            return "FAIL", f"{reason} (global exclusion)"

    # Step 2: Category-specific rules (if passed global check)
    # ...
```

**Test Coverage:** 14/14 tests passing (including Korean variants)

---

## 5. Comparison to Existing Methods

### 5.1 GRADE / PRISMA (Manual Review)

| Feature                  | GRADE/PRISMA           | TERVYX                  |
|--------------------------|------------------------|-------------------------|
| Pseudoscience exclusion  | Manual decision        | Automated (Φ gate)      |
| Reproducibility          | Subjective             | Deterministic           |
| Audit trail              | Narrative justification| Pattern + reason logged |
| Scale                    | <100 interventions     | 1,000+ interventions    |
| Real-time updates        | Annual reviews         | Continuous integration  |

### 5.2 Cochrane Reviews

| Feature                | Cochrane               | TERVYX                  |
|------------------------|------------------------|-------------------------|
| Scope                  | Single intervention    | Multi-intervention      |
| Meta-analysis method   | Fixed/Random effects   | REML with Monte Carlo   |
| Safety integration     | Separate assessment    | K gate (parallel)       |
| Commercial applicability| Academic focus        | Product-specific        |

---

## 6. Quality Metrics

### 6.1 Entry Quality Indicators

**For each entry, TERVYX computes:**

1. **P(effect > δ)** - Probability of clinically meaningful effect
   - Gold: P > 0.80
   - Silver: 0.65 < P ≤ 0.80
   - Bronze: 0.50 < P ≤ 0.65
   - Red: P ≤ 0.50
   - Black: Safety concerns or implausible mechanism

2. **Heterogeneity (τ² and I²)** - Study variability
   - τ² estimated via REML
   - I² reported for transparency

3. **Study Quality (JIF distribution)** - Publication venue credibility
   - Journal-Trust Oracle (J gate) with blacklist masking
   - Prevents "predatory journal rescue"

4. **Safety Profile (K gate)** - Contraindications and adverse events
   - Renal safety for supplements
   - Drug-supplement interactions
   - Electrical injury risk for devices

### 6.2 Dataset Quality Metrics

**Target for Nature submission:**

- **Total entries:** 1,020+
- **High-priority entries with real DOIs:** 460+ (45%)
- **Entries with ≥5 RCTs:** 70%+
- **Entries with safety data:** 100% (mandatory K gate)
- **Global forbidden pattern test coverage:** 100% (14/14 passing)

---

## 7. Methodological Advantages for Nature Submission

### 7.1 Reproducibility

✅ **Policy-as-code:** All exclusion criteria in versioned YAML files
✅ **Deterministic:** Same input → same output (no subjective decisions)
✅ **Auditable:** Every rejection logged with pattern match + reason

### 7.2 Transparency

✅ **Open algorithms:** REML implementation available in `engine/reml.py`
✅ **Explicit priors:** δ (clinical threshold) defined per outcome category
✅ **Pattern visibility:** All forbidden patterns published in `phi_rules.yaml`

### 7.3 Scalability

✅ **Automated pipeline:** Gate → REML → Classification → JSON-LD output
✅ **Continuous integration:** New studies added without full re-analysis
✅ **Multi-domain:** Health (current) → Finance, Climate (future)

---

## 8. Implementation Roadmap

### Phase 1: Structure Finalization (COMPLETED ✅)
- [x] Delete all 967 legacy entries (domain-based structure)
- [x] Design 2-axis taxonomy (Outcome × Intervention)
- [x] Implement global forbidden patterns in Φ gate
- [x] Create intervention_types_v2.yaml with Φ/K requirements
- [x] Update entry schema with `intervention_type` field
- [x] Expand entry_requirements_v2.json to 100 high-priority items

### Phase 2: Entry Generation (IN PROGRESS ⏳)
- [ ] Generate 515 high-priority entries with real paper DOIs
- [ ] Generate 415 medium-priority entries
- [ ] Generate 160 low-priority entries
- [ ] Validate all entries against updated schema

### Phase 3: Quality Assurance (PENDING)
- [ ] Run Φ gate validation on all entries (expect 0 forbidden pattern matches)
- [ ] Verify REML convergence for all entries
- [ ] Check K gate coverage (100% of entries must have safety assessment)
- [ ] Audit trail export for reproducibility

### Phase 4: Nature Manuscript (PENDING)
- [ ] Methods section: "Gate Governance Protocol with Automated Pseudoscience Rejection"
- [ ] Figure 1: 2-axis taxonomy diagram (Outcome × Intervention)
- [ ] Figure 2: Φ gate decision tree with global forbidden patterns
- [ ] Supplementary Table 1: Full list of 1,020+ entries with DOIs
- [ ] Supplementary Table 2: Global forbidden patterns with test results
- [ ] Case study: "How TERVYX rejects germanium bracelets"

---

## 9. Expected Contributions to Literature

### 9.1 Methodological Novelty

**First automated evidence synthesis system with:**
1. Policy-as-code governance for quality control
2. Multi-axis taxonomy enabling commercial health claim validation
3. Probabilistic classification integrated with deterministic safety gates
4. Global forbidden patterns for pseudoscience rejection

### 9.2 Practical Impact

**Enables:**
- Automated fact-checking of health product advertisements
- Real-time validation of influencer health claims
- Regulatory compliance monitoring for e-commerce platforms
- Consumer protection at scale (millions of products)

### 9.3 Domain Generalization (Trust OS)

**Beyond health:**
- **Finance:** Investment products (outcome: returns, intervention: asset class)
- **Climate:** Mitigation strategies (outcome: CO₂ reduction, intervention: technology type)
- **Education:** Learning interventions (outcome: skill acquisition, intervention: pedagogy)

---

## 10. Risk Mitigation

### 10.1 Potential Criticisms

**Criticism 1:** "Automated system cannot replace expert judgment"

**Response:**
- TERVYX **augments** expert review, not replaces it
- Φ gate rules are **designed by domain experts** and versioned
- Manual override possible for edge cases (documented in audit log)

**Criticism 2:** "Global forbidden patterns may exclude emerging valid therapies"

**Response:**
- Patterns target **established pseudoscience** (germanium bracelets, quantum pendants)
- New therapies with plausible mechanisms pass Φ gate (e.g., rTMS, tDCS)
- Pattern list is **versioned and updateable** as science evolves

**Criticism 3:** "Sample size too large to validate manually"

**Response:**
- **Reproducibility is the validation:** Any researcher can re-run TERVYX pipeline
- High-priority entries (515) include **real paper DOIs** for spot-checking
- Φ gate test suite (14 tests) ensures pseudoscience rejection works correctly

### 10.2 Limitations Acknowledged

1. **Language coverage:** Currently English + Korean only (extensible to Chinese, Japanese, Spanish)
2. **Outcome categories:** Health-focused (generalization to other domains in progress)
3. **Publication bias:** Inherited from underlying literature (mitigated by J gate blacklist)
4. **Contextual nuance:** Binary PASS/FAIL may oversimplify some interventions (addressed via tier system: Gold/Silver/Bronze)

---

## 11. Data Availability Statement (Draft for Nature)

**Upon publication, the following will be released:**

1. **Full dataset:** 1,020+ entries in JSON-LD format (Schema.org compliant)
2. **Source code:** Complete TERVYX pipeline (Python, YAML configs)
3. **DOI list:** All papers used in high-priority entries
4. **Test suite:** 14 Φ gate tests + 50+ integration tests
5. **Policy rules:** `phi_rules.yaml` with all forbidden patterns
6. **Replication script:** One-command reproduction of entire dataset

**License:** MIT (code) + CC-BY 4.0 (data)

---

## 12. Conclusion

TERVYX demonstrates that **automated evidence synthesis with policy-as-code governance** can achieve reproducibility and transparency at scale while maintaining scientific rigor. The 2-axis intervention-outcome taxonomy enables practical validation of commercial health claims, addressing a critical gap in consumer protection.

**Next milestone:** Generate 1,020+ entries with real paper DOIs, validate Φ gate rejection of pseudoscience, prepare Nature Methods manuscript.

---

## Appendix A: Intervention-Outcome Compatibility Matrix

| Intervention ↓ / Outcome → | Sleep | Cognition | Mental Health | Cardiovascular | Metabolic | Musculoskeletal |
|----------------------------|-------|-----------|---------------|----------------|-----------|-----------------|
| **supplement**             | ✅     | ✅         | ✅             | ✅              | ✅         | ✅               |
| **device_noninvasive**     | 🔶*    | 🔶*        | 🔶*            | ❌              | 🔶*        | ✅               |
| **behavioral**             | ✅     | ✅         | ✅             | ✅              | ✅         | ✅               |
| **food**                   | ✅     | ✅         | ✅             | ✅              | ✅         | 🔶*              |
| **pharmaceutical**         | ✅     | ✅         | ✅             | ✅              | ✅         | ✅               |
| **procedure**              | ❌     | ❌         | ✅             | ❌              | ❌         | ✅               |

**Legend:**
- ✅ Allowed (plausible mechanism)
- 🔶 Conditional (requires specific mechanism validation)
- ❌ Excluded (no plausible mechanism)

**Example conditionals:**
- *Device for sleep:* Light therapy ✅, EMS ❌
- *Device for cognition:* tDCS ✅, TENS ❌
- *Device for metabolic:* EMS (insulin sensitivity) ✅, EMS (fat reduction) ❌

---

## Appendix B: Example Entry (Post-Generation)

```json
{
  "@context": "https://schema.org/",
  "@type": "Dataset",
  "id": "supplement:magnesium-glycinate:sleep:v1",
  "intervention_type": "supplement",
  "category": "sleep",
  "substance": "magnesium glycinate",
  "claim": "Magnesium glycinate supplementation improves sleep quality in adults with insomnia symptoms",
  "tier": "Gold",
  "label": "PASS",
  "delta": 0.5,
  "p_effect_gt_delta": 0.87,
  "studies": 14,
  "total_n": 1247,
  "heterogeneity": {
    "tau2": 0.12,
    "i2": 42.3
  },
  "gates": {
    "phi": "PASS",
    "r": "PASS",
    "j": "PASS",
    "k": "PASS (monitor renal function in CKD)",
    "l": "PASS"
  },
  "dois": [
    "10.1016/j.sleep.2022.03.028",
    "10.1093/sleep/zsab156"
  ],
  "policy_version": "v1.1.0",
  "generated_date": "2025-11-07"
}
```

---

**Document Status:** Ready for implementation
**Next Action:** Begin Phase 2 (Entry Generation with real DOIs)
