# TERVYX Intervention-Based Taxonomy v2.0

## Purpose
TERVYX는 **상업적으로 판매되는 건강 제품/서비스의 주장을 검증**합니다.
기존의 학술적 도메인 분류(behavioral, psychological) 대신 **사용자가 실제로 구매하고 사용하는 제품/중재법** 중심으로 재구성합니다.

---

## Core Principle

**사용자 질문 중심 설계:**
- ❌ 잘못된 질문: "이 연구는 어느 학문 도메인에 속하나?"
- ✅ 올바른 질문: "마그네슘 글리시네이트가 수면에 효과 있나?"

**구조:**
```
{제품/중재법 타입} / {구체적 제품명} / {주장된 효과} / {버전}
```

**예시:**
```
supplements/minerals/magnesium-glycinate/sleep/v1/
devices/electrical_stimulation/ems/fat_reduction/v1/
devices/wearables/germanium_bracelet/circulation/v1/
behavioral/meditation/mindfulness/anxiety/v1/
```

---

## Taxonomy Hierarchy

### Level 1: Intervention Type (중재법 대분류)

#### 1. **Dietary Supplements** (`supplements/`)
상업적으로 판매되는 모든 식이보충제

**Level 2 Subcategories:**

##### 1.1 `vitamins/`
- vitamin-d, vitamin-k2, vitamin-b12, vitamin-c, vitamin-e, b-complex, multivitamin

##### 1.2 `minerals/`
- magnesium-glycinate, magnesium-citrate, zinc, iron, calcium, selenium, chromium, iodine

##### 1.3 `herbs_botanicals/`
- ashwagandha, rhodiola, ginkgo-biloba, turmeric, curcumin, ginseng, bacopa, st-johns-wort
- green-tea-extract, grape-seed-extract, milk-thistle, saw-palmetto

##### 1.4 `amino_acids/`
- l-theanine, l-tryptophan, l-tyrosine, glycine, taurine, l-carnitine, 5-htp
- creatine, beta-alanine, glutamine

##### 1.5 `fatty_acids/`
- omega-3, fish-oil, krill-oil, dha, epa, omega-6, gla, cla

##### 1.6 `probiotics/`
- lactobacillus, bifidobacterium, multi-strain, specific-strains

##### 1.7 `antioxidants/`
- resveratrol, quercetin, coq10, alpha-lipoic-acid, astaxanthin, pycnogenol
- nac, glutathione

##### 1.8 `specialty_compounds/`
- melatonin, cbd, berberine, nicotinamide-riboside (NR), nmn, pterostilbene
- collagen, hyaluronic-acid, glucosamine, chondroitin, msm

##### 1.9 `superfoods/`
- spirulina, chlorella, wheatgrass, beetroot-powder, maca, moringa

---

#### 2. **Physical Devices & Therapies** (`devices/`)
물리적 기기 및 에너지 기반 치료

**Level 2 Subcategories:**

##### 2.1 `electrical_stimulation/`
- ems (electrical muscle stimulation) - 근육 자극
- tens (transcutaneous electrical nerve stimulation) - 통증 완화
- tacs (transcranial alternating current stimulation) - 뇌 자극
- tdcs (transcranial direct current stimulation) - 우울증, 인지

##### 2.2 `wearables/`
- germanium-bracelet (게르마늄 팔찌)
- magnetic-bracelet (자기 팔찌)
- copper-bracelet (구리 팔찌)
- ion-band (이온 밴드)
- acupressure-band (지압 밴드)

##### 2.3 `light_therapy/`
- red-light-therapy (적색광)
- blue-light-therapy (청색광 - 여드름)
- uv-therapy (자외선 - 피부질환)
- sad-lamp (seasonal affective disorder)
- infrared-therapy (적외선)

##### 2.4 `thermal_therapy/`
- sauna (사우나)
- cryotherapy (냉동치료)
- heat-pad (온열 패드)
- ice-bath (냉수욕)

##### 2.5 `mechanical/`
- massage-devices (마사지 기기)
- vibration-plates (진동 플레이트)
- foam-roller (폼롤러)
- compression-devices (압박 기기)

##### 2.6 `acoustic/`
- ultrasound-therapy (초음파 치료)
- sound-therapy (음향 치료)
- binaural-beats (바이노럴 비트)

---

#### 3. **Behavioral Interventions** (`behavioral/`)
행동 기반 중재 (비제품)

**Level 2 Subcategories:**

##### 3.1 `exercise/`
- aerobic, resistance, yoga, tai-chi, pilates, hiit, walking

##### 3.2 `meditation/`
- mindfulness, transcendental, vipassana, loving-kindness, body-scan

##### 3.3 `sleep_hygiene/`
- sleep-restriction, stimulus-control, sleep-schedule, bedroom-optimization

##### 3.4 `stress_management/`
- breathing-exercises, progressive-muscle-relaxation, biofeedback, autogenic-training

##### 3.5 `cognitive_behavioral/`
- cbt-i (insomnia), cbt (cognitive behavioral therapy), act (acceptance commitment therapy)

---

#### 4. **Foods & Functional Foods** (`foods/`)
가공되지 않은 전체 식품

**Level 2 Subcategories:**

##### 4.1 `whole_foods/`
- beetroot, garlic, ginger, turmeric-root, tart-cherry, blueberry, pomegranate

##### 4.2 `fermented_foods/`
- kimchi, sauerkraut, kefir, kombucha, yogurt, miso, tempeh

##### 4.3 `beverages/`
- green-tea, coffee, cocoa, herbal-tea, bone-broth

##### 4.4 `dietary_patterns/`
- mediterranean-diet, ketogenic-diet, intermittent-fasting, plant-based-diet

---

#### 5. **Pharmaceutical & OTC** (`pharmaceutical/`)
의약품 및 일반의약품 (제한적 포함)

**Level 2 Subcategories:**

##### 5.1 `otc_medications/`
- ibuprofen, acetaminophen, aspirin, antihistamines

##### 5.2 `nutraceuticals/`
- 의약품과 보충제 경계에 있는 제품 (berberine for diabetes 등)

---

#### 6. **Safety & Contraindications** (`safety/`)
부작용, 금기사항, 상호작용 전용

**Level 2 Subcategories:**

##### 6.1 `drug_interactions/`
- supplement-drug interactions
- supplement-supplement interactions

##### 6.2 `contraindications/`
- pregnancy, lactation, pediatric, geriatric, disease-specific

##### 6.3 `adverse_events/`
- hepatotoxicity (간독성)
- nephrotoxicity (신독성)
- cardiovascular events
- allergic reactions

---

## Directory Structure Examples

### Current (Wrong)
```
entries/
├── behavioral/5htp-slp-fhtp-serotonin/sleep/v1/
├── metabolic/spirulina-meta-glu12/metabolic/v1/
├── physiological/omega-3-card-gen-0301/cardiovascular/v1/
└── nutrient/magnesium-glycinate/sleep/v1/
```
❌ Problems:
- "behavioral", "metabolic" are academic domains, not product types
- "nutrient" is a substance class, not a category
- User doesn't think "I need a metabolic intervention"

### Proposed (Correct)
```
entries/
├── supplements/
│   ├── amino_acids/
│   │   └── 5htp/sleep/v1/
│   ├── superfoods/
│   │   └── spirulina/metabolic_health/v1/
│   ├── fatty_acids/
│   │   └── omega-3/cardiovascular_health/v1/
│   └── minerals/
│       └── magnesium-glycinate/sleep/v1/
├── devices/
│   ├── electrical_stimulation/
│   │   └── ems/fat_reduction/v1/
│   └── wearables/
│       └── germanium-bracelet/circulation/v1/
└── behavioral/
    └── meditation/
        └── mindfulness/anxiety/v1/
```
✅ Benefits:
- User-centric: "마그네슘 글리시네이트" is in `supplements/minerals/`
- Product type clear: devices, supplements, behaviors
- Commercial relevance: matches how products are sold

---

## Outcome Categories (Level 4)

**Standardized outcomes across all intervention types:**

### Physical Health
- `cardiovascular_health` - BP, lipids, heart function
- `metabolic_health` - glucose, insulin, HbA1c, body composition
- `immune_function` - infection resistance, immune markers
- `musculoskeletal_health` - strength, joint function, pain
- `digestive_health` - gut function, microbiome
- `skin_health` - acne, aging, inflammation
- `renal_function` - kidney markers, eGFR
- `hepatic_function` - liver enzymes, detox

### Mental & Cognitive
- `cognitive_function` - memory, attention, executive function
- `mental_wellbeing` - depression, anxiety, mood
- `sleep_quality` - insomnia, sleep architecture
- `stress_resilience` - cortisol, stress response

### Performance & Longevity
- `athletic_performance` - endurance, strength, recovery
- `longevity_biomarkers` - telomeres, biological age
- `energy_vitality` - fatigue, vitality

### Safety
- `safety_profile` - adverse events, tolerability
- `contraindications` - drug interactions, populations to avoid

---

## Migration Plan

### Step 1: Map Current Entries
```python
MIGRATION_MAP = {
    "behavioral/5htp-*/sleep": "supplements/amino_acids/5htp/sleep",
    "metabolic/spirulina-*": "supplements/superfoods/spirulina/{outcome}",
    "physiological/omega-3-*": "supplements/fatty_acids/omega-3/{outcome}",
    "nutrient/magnesium-glycinate": "supplements/minerals/magnesium-glycinate/{outcome}",
    # ... (967 entries)
}
```

### Step 2: Add Missing Intervention Types
**Priority Additions (to reach 1,000+):**

**Devices (현재 0개 → 100개 목표):**
- EMS devices (fat reduction, muscle toning, pain relief)
- TENS units (chronic pain, acute pain)
- Germanium/magnetic bracelets (circulation, pain, energy)
- Red light therapy (skin aging, wound healing, pain)
- Blue light therapy (acne, SAD)
- Vibration plates (bone density, circulation)

**Foods (현재 매우 적음 → 50개 목표):**
- Beetroot (cardiovascular, athletic performance)
- Garlic (cardiovascular, immune)
- Ginger (inflammation, nausea)
- Tart cherry (sleep, inflammation, recovery)
- Green tea (metabolic, cognitive, longevity)

**Safety (현재 3개 → 100개 목표):**
- Drug interactions (warfarin + vitamin K, statins + CoQ10)
- Pregnancy contraindications (각 보충제별)
- Hepatotoxicity profiles (green tea extract, kava)

### Step 3: Remove Redundant/Invalid Entries
**Deletion Criteria:**
- Duplicate entries with slightly different codes
- Purely academic exercises (no commercial product)
- Invalid claims (Φ gate violations that shouldn't exist)

---

## Policy Configuration Update

### New `policy.yaml` Structure
```yaml
version: "v2.0.0"
taxonomy: "intervention_based"

intervention_types:
  supplements:
    description: "Commercial dietary supplements"
    subcategories: [vitamins, minerals, herbs_botanicals, amino_acids, ...]

  devices:
    description: "Physical devices and energy-based therapies"
    subcategories: [electrical_stimulation, wearables, light_therapy, ...]

  behavioral:
    description: "Behavioral interventions (non-product)"
    subcategories: [exercise, meditation, sleep_hygiene, ...]

  foods:
    description: "Whole foods and dietary patterns"
    subcategories: [whole_foods, fermented_foods, beverages, ...]

outcome_categories:
  cardiovascular_health:
    delta: 2.0
    delta_units: "MD (mmHg)"
    measures: [SBP, DBP, LDL, HDL, triglycerides]

  metabolic_health:
    delta: 0.25
    delta_units: "SMD"
    measures: [fasting_glucose, HbA1c, insulin, HOMA-IR]

  # ... (12 total outcome categories)
```

---

## Expected Entry Distribution (Target: 1,000+)

```
Intervention Type               Target Count
─────────────────────────────────────────────
supplements/vitamins/                  80
supplements/minerals/                  70
supplements/herbs_botanicals/         120
supplements/amino_acids/               80
supplements/fatty_acids/               60
supplements/probiotics/                40
supplements/antioxidants/              80
supplements/specialty_compounds/       90
supplements/superfoods/                50
                                     ─────
Supplements Subtotal:                 670

devices/electrical_stimulation/        40
devices/wearables/                     30
devices/light_therapy/                 20
devices/thermal_therapy/               10
devices/mechanical/                    10
                                     ─────
Devices Subtotal:                     110

behavioral/exercise/                   30
behavioral/meditation/                 20
behavioral/sleep_hygiene/              15
behavioral/stress_management/          15
                                     ─────
Behavioral Subtotal:                   80

foods/whole_foods/                     30
foods/fermented_foods/                 15
foods/beverages/                       15
                                     ─────
Foods Subtotal:                        60

safety/drug_interactions/              40
safety/contraindications/              30
safety/adverse_events/                 30
                                     ─────
Safety Subtotal:                      100
                                     ─────
TOTAL:                              1,020
```

---

## Implementation Checklist

- [ ] Create new taxonomy YAML (`protocol/taxonomy/intervention_based_v2.yaml`)
- [ ] Write migration script (`tools/migrate_to_intervention_taxonomy.py`)
- [ ] Analyze current 967 entries and map to new structure
- [ ] Identify and delete redundant/invalid entries
- [ ] Generate missing device entries (100+)
- [ ] Generate missing food entries (50+)
- [ ] Generate missing safety entries (100+)
- [ ] Update `policy.yaml` to v2.0.0
- [ ] Rebuild all entries with new structure
- [ ] Update README to emphasize "Trust OS" (not just health fact-check)
- [ ] Validate all entries against new schema
- [ ] Update documentation for Nature submission

---

## Nature Publication Alignment

### Key Messages for Paper

1. **"Health products are the first use case"**
   - TERVYX is a trust standard, not a health-specific tool
   - Intervention taxonomy is domain-agnostic (can extend to finance, climate, legal)

2. **"User-centric categorization"**
   - Organized by how people actually use products (supplements, devices, behaviors)
   - Not academic silos

3. **"Commercial claim verification"**
   - Target: products sold to consumers
   - Real-world relevance, not just academic literature

4. **"Reproducibility through structure"**
   - Same policy, same pipeline, same results
   - 5-minute reproduction time

---

## Next Steps

1. **Approve this taxonomy?**
2. **Proceed with migration?**
3. **Delete redundant entries?**
4. **Generate missing device/food/safety entries?**

Once approved, we will:
- Create migration script
- Restructure all entries
- Fill gaps to 1,000+
- Update all documentation for Nature
