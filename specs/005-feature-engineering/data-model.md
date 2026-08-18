# Phase 1 Data Model: Feature Engineering

## ClaimFeatures

| Field | Type | Notes |
|---|---|---|
| `claim_id` | string | `CLM_ID` |
| `payment_to_charge_ratio` | float \| null | `CLM_PMT_AMT / CLM_TOT_CHRG_AMT`; null if denominator is 0/missing (spec FR-001) |
| `length_of_stay_days` | integer \| null | Shared derivation with Phase 4; null if admission/discharge date missing (spec FR-002) |
| `admission_day_of_week` / `admission_month` / `admission_year` | integer | Date-derived, from ISO `CLM_ADMSN_DT` (spec FR-003) |
| `encoded_categoricals` | object | column → encoded value(s), per the `EncodingScheme` used (spec FR-004) |
| `provider_frequency` | float \| null | Historical occurrence rate of this claim's `PRVDR_NUM`; null if `PRVDR_NUM` missing (spec FR-005) |

**Validation rules**: Every null field has a documented reason traceable to missing/zero source data — never a fabricated stand-in (spec FR-010, SC-001).

## WindowFeatures

| Field | Type | Notes |
|---|---|---|
| `window_id` | string | Matches Phase 4's `VolumeBaseline.windows[].window_id` |
| `claim_count` | integer | Real count for this window, including 0 |
| `amount_stats` | object | Per-amount-column `{mean, median, std}` for this window's claims |
| `missing_pct` / `duplicate_pct` / `invalid_status_pct` | float | Sourced from/consistent with Phase 2/3, scoped to this window |
| `volume_deviation` | float | vs. Phase 4 `BaselineSnapshot.volume_baseline` (spec FR-007) |
| `amount_deviation` | object | Per-amount-column deviation vs. `BaselineSnapshot.amount_baselines` |
| `anomaly_count` | integer \| null | **Deferred field** — `null` until a Phase 7/8 enrichment step populates it; never a fabricated zero (spec FR-008, SC-004) |

**Validation rules**: `anomaly_count` is present on every row; a schema/contract test verifies its value is `null` (not `0`) in every row produced before Phase 7 ships (spec SC-004). `volume_deviation`/`amount_deviation` reference the exact `BaselineSnapshot` and `window_definition` used, and computation aborts (rather than silently proceeding) on a window-definition mismatch (spec FR-007).

## EncodingScheme

| Field | Type | Notes |
|---|---|---|
| `column_name` | string | |
| `strategy` | enum | `one_hot` (low cardinality) or `frequency` (high cardinality) — see research.md |
| `fitted_categories` | array | Categories known at fitting time |
| `unseen_category_policy` | string | e.g., `"map_to_unknown_bucket"` — always explicit, never silent aliasing (spec FR-004, SC-005) |

## Relationships

`ClaimFeatures` rows are 1:1 with cleaned claims (Phase 2 output, claim grain — not claim-line grain, since features here are claim-level, not line-item-level). `WindowFeatures` rows are 1:1 with Phase 4's defined windows. `EncodingScheme` is fit once per categorical column and referenced by every `ClaimFeatures.encoded_categoricals` computation for consistency across claims.
