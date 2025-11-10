# Definition of Done (DoD) - TERVYX Protocol v2 Migration

This checklist defines the completion criteria for the intervention_based_v2 taxonomy migration and deterministic pipeline consolidation.

## 📋 Completion Checklist

### 1. Infrastructure & Configuration

- [x] **Taxonomy v2 in place**: `protocol/taxonomy/intervention_based_v2.yaml` exists and defines all intervention types
- [x] **Policy anchors configured**: `policy.yaml` includes:
  - [x] TEL-5 tier boundaries (min_p thresholds)
  - [x] Category-specific δ values and benefit directions
  - [x] Monte Carlo configuration (seed, n_draws, tau2_method)
  - [x] Gate rules (Φ/R/J/K/L versions and parameters)
  - [x] Monotone invariant enforcement rules
  - [x] Policy fingerprinting configuration
- [x] **Gate rule files**: `protocol/phi_rules.yaml` and `protocol/L_rules.yaml` exist with documented patterns
- [x] **Journal Trust snapshot**: `protocol/journal_trust/snapshot-2025-10-30.json` exists

### 2. Schemas & Validation

- [x] **All 4 schemas present**:
  - [x] `protocol/schemas/esv.schema.json` (Evidence State Vector)
  - [x] `protocol/schemas/simulation.schema.json` (REML + MC results)
  - [x] `protocol/schemas/entry.schema.json` (Final TEL-5 entry)
  - [x] `protocol/schemas/citations.schema.json` (Bibliography)
- [x] **Entry schema includes**:
  - [x] `intervention_type` field (required, enum)
  - [x] `policy_refs` object (required: tel5_levels, monte_carlo, journal_trust)
  - [x] `policy_fingerprint` (required, pattern: `^0x[a-f0-9]{16}$`)
  - [x] `audit_hash` (required, pattern: `^0x[a-f0-9]{16}$`)
  - [x] `tier_label_system` (required, const: "TEL-5")
  - [x] `gate_results` (required, all 5 gates: phi, r, j, k, l)

### 3. Documentation

- [x] **README.md updated** with all required sections:
  - [x] What is TERVYX / Core Philosophy (policy-as-code governance)
  - [x] Gate Governance Protocol (GGP) table with monotone invariant
  - [x] TEL-5 definition table with Φ/K special rule
  - [x] Deterministic Build Pipeline (6-stage flow diagram)
  - [x] Repository Structure (updated for v2 taxonomy)
  - [x] Entry Creation Workflow (5 steps with commands)
  - [x] Policy & Governance (anchors, fingerprinting, governance model)
  - [x] Example Artifacts (simulation.json, entry.jsonld, citations.json with all required fields)
- [x] **Policy version line**: README includes `Policy version: v1.3.0 | TEL-5 version: v1.2.0 | Journal Trust snapshot: 2025-10-30 | Taxonomy: intervention_based_v2.0`

### 4. Tools & Scripts

- [x] **Migration script**: `tools/migrate_to_intervention_v2.py` exists with:
  - [x] Taxonomy-based path computation
  - [x] Entry relocation logic
  - [x] Artifact rebuild via `build_protocol_entry.py`
  - [x] Schema + policy anchor validation
  - [x] Parallel processing support (--workers)
  - [x] Dry-run mode (--dry-run)
- [ ] **Validation script**: `scripts/validate_entry_artifacts.py` supports:
  - [ ] Shard-based validation (--shard-index, --shard-count)
  - [ ] Schema validation for all 3 artifacts
  - [ ] Policy anchor consistency checks
  - [ ] Gate results validation (Φ/K violations → Black enforcement)
- [x] **Policy fingerprint tool**: `scripts/tervyx.py fingerprint` computes and displays policy digest

### 5. CI/CD Pipeline

- [x] **CI workflow updated** (`.github/workflows/ci.yml`):
  - [x] Python matrix (3.9, 3.10, 3.11)
  - [x] Policy + schema validation (all files)
  - [x] Taxonomy validation (`intervention_based_v2.yaml`)
  - [x] Gate rules validation (`phi_rules.yaml`, `L_rules.yaml`)
  - [x] Journal snapshot validation (`snapshot-2025-10-30.json`)
  - [x] Policy fingerprint check
  - [x] Shard-based entry validation (10 shards)
- [x] **Sample entry paths**: Updated to v2 structure (`entries/supplements/minerals/magnesium-glycinate/sleep/v1`)

### 6. Entry Artifacts (Post-Migration)

These will be validated after migration is run:

- [ ] **All entries reorganized**: Entries moved to intervention-based v2 structure
  - [ ] `entries/supplements/` populated
  - [ ] `entries/devices/` populated
  - [ ] `entries/behavioral/` populated
  - [ ] `entries/foods/` populated
  - [ ] `entries/safety/` populated (if applicable)
- [ ] **All entries have 3 artifacts**:
  - [ ] `evidence.csv` (ESV-compliant)
  - [ ] `simulation.json` (with policy_fingerprint)
  - [ ] `entry.jsonld` (with all required anchors)
  - [ ] `citations.json` (with policy_fingerprint)
- [ ] **100% schema pass rate**: All artifacts validate against schemas
- [ ] **Policy anchor consistency**: All entries reference same:
  - [ ] `policy_refs.tel5_levels`: `"v1.2.0"`
  - [ ] `policy_refs.monte_carlo`: `"v1.0.1-reml-grid"`
  - [ ] `policy_refs.journal_trust`: `"2025-10-30"`
  - [ ] `policy_fingerprint`: Same value across all entries (computed from `policy.yaml` + snapshots)

### 7. Gate Rules & Monotone Invariant

- [ ] **Sample validation cases**: Test at least N entries (N ≥ 10) for:
  - [ ] Φ=FAIL entries → tier=Black, label=FAIL (regardless of P(effect > δ))
  - [ ] K=FAIL entries → tier=Black, label=FAIL (regardless of P(effect > δ))
  - [ ] J* masking: If Φ=FAIL or K=FAIL, J* score masked to 0.0
  - [ ] No J* bypass: High J* cannot override Φ/K violations
- [ ] **Implementation verified**: `engine/gates.py` enforces monotone invariant at build time

### 8. Reproducibility & Determinism

- [ ] **Fixed seed**: All Monte Carlo simulations use seed `20251005`
- [ ] **Identical outputs**: Re-running `build_protocol_entry.py` on same evidence → identical JSON artifacts (byte-for-byte, except timestamps)
- [ ] **Policy fingerprint stability**: Policy fingerprint remains constant unless policy files change

### 9. Repository Cleanup

- [x] **.gitignore updated**: Intermediate artifacts excluded (`.cache`, `.tmp`, `.build/`)
- [ ] **No uncommitted secrets**: Verify no `.env`, credentials, or API keys in git history
- [ ] **Legacy paths cleaned**: Old entry paths (if any) removed or documented

### 10. Final Validation

- [ ] **CI passes**: All CI jobs (build, validate-entries, validate-schema-only, security-scan) pass
- [ ] **Smoke tests**: `python scripts/tervyx.py status` reports healthy state
- [ ] **No critical warnings**: No schema violations, missing fields, or anchor mismatches in logs

---

## 🚀 Ready for Commit

When all items above are checked:

1. **Create pre-migration tag**: `git tag pre-v2-migration`
2. **Commit changes**: `git add -A && git commit -m "feat: Implement deterministic pipeline v2 with intervention taxonomy"`
3. **Push to feature branch**: `git push -u origin claude/tervyx-deterministic-pipeline-v2-011CUyKZ3EqUKXPESA5vdWC6`
4. **Verify CI**: Wait for all CI jobs to complete successfully
5. **Create PR**: If targeting main, open PR with this DoD checklist in description

---

## 📊 Success Metrics

- **Entry coverage**: ≥1,000 entries migrated and validated
- **Schema compliance**: 100% pass rate
- **Policy anchor consistency**: 100% match rate
- **Gate enforcement**: 100% Φ/K violations result in Black/FAIL
- **CI stability**: All jobs green across all Python versions

---

**Last Updated**: 2025-11-10
**Migration Target**: intervention_based_v2.yaml
**Policy Version**: v1.3.0
