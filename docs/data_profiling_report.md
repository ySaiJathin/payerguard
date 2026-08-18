# Data Profiling Report — inpatient.csv

Generated during repo scaffolding (Phase 0), from the actual file supplied
by the user. This is a starting point, not a substitute for the full
automated profiling step in Phase 1.1 — re-run and expand this once
`backend/app/data_engineering/profiling.py` is implemented.

## File format
- Delimiter: `|` (pipe). Despite the `.csv` extension, this is **not**
  comma-delimited. Must load with `sep="|"`.
- 197 columns, 58,066 data rows (excluding header).

## Grain
- The file is at **claim-line** grain (one row per revenue-center line),
  not claim grain.
- Unique `CLM_ID`: 20,867
- Unique `BENE_ID`: 5,699
- Lines per claim: mean 2.82, median 1, max 46 (right-skewed)
- Exact duplicate full rows: 0

## Dates
- `CLM_FROM_DT`, `CLM_THRU_DT`, `CLM_ADMSN_DT`, `NCH_BENE_DSCHRG_DT` all
  range 01-Apr-2015 to 31-Oct-2022.
- Format is `DD-Mon-YYYY` (e.g. `01-Apr-2015`), stored as strings — needs
  explicit parsing in the standardization step.

## Key amount fields
| Field | mean | median | std | min | max |
|---|---:|---:|---:|---:|---:|
| CLM_PMT_AMT | 13,638.31 | 1,481.72 | 35,993.91 | 62.44 | 598,716.31 |
| CLM_TOT_CHRG_AMT | 13,638.31 | 1,481.72 | 35,993.91 | 62.44 | 598,716.31 |

Both are heavily right-skewed — baselines should use median/percentiles,
not mean, as the central-tendency reference.

## Utilization
- `CLM_UTLZTN_DAY_CNT`: mean 1.70, median 0, max 104.

## Missingness (selected columns)
- 100% missing (drop): `OT_PHYSN_UPIN`, `OT_PHYSN_NPI`, `FI_CLM_ACTN_CD`,
  `FI_NUM`, `FI_CLM_PROC_DT`, `NCH_VRFD_NCVRD_STAY_FROM_DT`,
  `NCH_VRFD_NCVRD_STAY_THRU_DT`, `NCH_BENE_MDCR_BNFTS_EXHTD_DT_I`,
  `NCH_ACTV_OR_CVRD_LVL_CARE_THRU`, `CLM_UNCOMPD_CARE_PMT_AMT`
- `ADMTG_DGNS_CD`: 72.2% missing
- `PRNCPAL_DGNS_CD`: 0% missing (more reliable diagnosis field)
- `CLM_DRG_CD`: 5.5% missing
- `PRVDR_NUM`: 4.4% missing
- `AT_PHYSN_NPI`, `ORG_NPI_NUM`: 0% missing
- Procedure code slots `ICD_PRCDR_CD1`…`ICD_PRCDR_CD25` (and paired
  `PRCDR_DTn`): missingness rises sharply with slot position —
  `ICD_PRCDR_CD16` is already 98.3% missing, `ICD_PRCDR_CD25` is 99.9%
  missing. Only the first several slots carry real signal.

## Cardinality / constant columns
- Constant across the whole file (candidates for removal):
  `NCH_CLM_TYPE_CD` (=60), `CLM_FREQ_CD` (=1), `CLAIM_QUERY_CODE` (=3),
  `CLM_MDCR_NON_PMT_RSN_CD` (blank), `PTNT_DSCHRG_STUS_CD` (=1, in this
  extract).
- `CLM_IP_ADMSN_TYPE_CD`: 3 categories — 1 (emergency, 43,089), 3
  (elective, 14,020), 2 (urgent, 957).
- `PRVDR_STATE_CD`: 51 distinct values, reasonably spread.
- `CLM_DRG_CD`: 167 distinct values.
- `PRVDR_NUM`: 4,876 distinct values.
- `HCPCS_CD`: 106 distinct values. `REV_CNTR`: only 2 distinct values in
  this extract.

## No pre-existing target label
There is no SLA-breach, fraud, or risk label in this file. Phase 8 (Risk
Dataset Construction) must derive a label from operational proxies
(processing delay, volume anomalies, quality-check failure rate) and
document the derivation logic explicitly rather than assuming a
ground-truth column exists.

## Next steps (Phase 1.1/1.2 in MVP_CONTEXT.md)
1. Run full automated profiling across all 197 columns (not just the
   subset above) once `data_engineering/profiling.py` exists.
2. Finalize column categorization for every column, including the
   diagnosis (`ICD_DGNS_CD*`, `ICD_DGNS_E_CD*`) and procedure
   (`ICD_PRCDR_CD*`) code families not fully enumerated here.
3. Decide the concrete missingness threshold for Stage 1 feature
   selection (e.g. drop columns >95% missing) and document it.
