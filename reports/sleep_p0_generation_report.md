# Sleep P0 Generation Run Summary (policy.yaml TEL-5 calibration)

## Execution Overview
- Command: `python -m scripts.tervyx_scale catalog generate --category sleep --priority P0 --limit 20 --apply policy.yaml --no-formulation-split --algo-version 2.0.0 --data-snapshot "monthly@2025-10" --concurrency 1 --bump minor --update-registry --report reports/tiers_by_category.md --show-adjustments`
- Environment warnings: sentence-transformers, scikit-learn, and requests modules unavailable in sandbox; run completed using offline fallbacks.
- Total entries processed: **2** (available sleep/P0 catalog entries in offline dataset).

## Entry Outcomes
| Entry ID | Substance | Indication | Adjusted Tier | Notes |
| --- | --- | --- | --- | --- |
| `SLP-MAG-CORE` | Magnesium | Sleep quality | Bronze | Scaffold-only payload present; evidence summary still pending (n_studies = 0). |
| `SLP-MEL-ACUTE` | Melatonin | Sleep onset | P0 | Catalog metadata available but no linked entry artifacts in offline cache; rerun with full dataset required for evidence integration. |

## Policy Adjustment Signals
- Recalibration enforced Gold probability ≥ 0.90, Silver ≥ 0.75, Bronze ≥ 0.60.
- Gold evidence floor requires ≥ 5 studies with ≥ 2 RCTs; heterogeneity ≥ 75% or freshness ≥ 5 years without follow-up caps entries at Silver.

## Distribution Snapshot
- Sleep category distribution after run: Black 1, P0 1 (unchanged due to limited offline coverage).

## Follow-up Actions
1. Re-run generation once scaling dependencies (`sentence-transformers`, `scikit-learn`, `requests`) and full evidence warehouse are available to unlock remaining P0 sleep entries.
2. For `SLP-MAG-CORE`, trigger evidence ingestion to populate study counts and TEL-5 metrics before final tier review.
3. Re-run catalog preview with `--show-adjustments` after dependencies are restored to confirm Silver cap triggers on high I² items once evidence arrives.
