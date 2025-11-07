# Entry Requirements Restructuring Plan

## Current Status
- File: entry_requirements.json (200 items)
- Structure: Domain-based (behavioral, metabolic, physiological)
- Problem: "substance" field contains academic domains, not product types

## New Structure (Intervention-Based)

### JSON Schema
```json
{
  "intervention_type": "supplement | device_noninvasive | behavioral | food | pharmaceutical | procedure",
  "subcategory": "string (e.g., minerals, electrical_stimulation, exercise)",
  "product": "string (specific product name)",
  "product_variants": ["array of variants if applicable"],
  "outcomes": ["array of validated outcome categories"],
  "priority": "high | medium | low",
  "studies_estimate": "number (estimated available studies)",
  "notes": "string (optional context)"
}
```

### Mapping Strategy

**Supplements:**
```json
{
  "intervention_type": "supplement",
  "subcategory": "minerals",
  "product": "magnesium-glycinate",
  "product_variants": ["magnesium-citrate", "magnesium-threonate"],
  "outcomes": ["sleep", "anxiety", "muscle_pain"],
  "priority": "high",
  "studies_estimate": 25
}
```

**Devices:**
```json
{
  "intervention_type": "device_noninvasive",
  "subcategory": "electrical_stimulation",
  "product": "ems",
  "outcomes": ["muscle_strength", "recovery", "pain"],
  "priority": "medium",
  "studies_estimate": 15,
  "notes": "Exclude fat reduction claims (insufficient mechanism)"
}
```

**Foods:**
```json
{
  "intervention_type": "food",
  "subcategory": "whole_foods",
  "product": "beetroot",
  "outcomes": ["cardiovascular", "athletic_performance"],
  "priority": "medium",
  "studies_estimate": 12
}
```

## Priority Assignment Criteria

**High Priority:**
- Well-established products with >20 studies
- Common consumer products (magnesium, omega-3, vitamin D)
- Evidence-based devices (TENS, tDCS for validated indications)

**Medium Priority:**
- Emerging products with 10-20 studies
- Traditional remedies with modern evidence
- Device applications with preliminary evidence

**Low Priority:**
- Niche products with <10 studies
- Preliminary research stage
- Highly specific populations

## Target Distribution (1,000+ entries)

| Intervention Type | Subcategories | Target Entries | Priority Distribution |
|-------------------|---------------|----------------|----------------------|
| supplement | 8 subcategories | 600 | High: 300, Med: 200, Low: 100 |
| device_noninvasive | 5 subcategories | 150 | High: 50, Med: 70, Low: 30 |
| behavioral | 4 subcategories | 100 | High: 40, Med: 40, Low: 20 |
| food | 3 subcategories | 80 | High: 30, Med: 30, Low: 20 |
| pharmaceutical | 1 subcategory | 40 | High: 30, Med: 10, Low: 0 |
| procedure | 1 subcategory | 30 | High: 10, Med: 15, Low: 5 |
| **Total** | | **1,000** | **460 High, 365 Med, 175 Low** |

## Next Actions

1. ✅ Delete old entries (completed)
2. ⏳ Create new entry_requirements_v2.json (in progress)
3. ⏳ Map top 100 high-priority entries
4. ⏳ Collect real paper DOIs for high-priority entries
5. ⏳ Generate entries LAST (after structure confirmed)
