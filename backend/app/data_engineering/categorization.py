"""Column name -> category assignment.

A static mapping seeded from MVP_CONTEXT.md Section 2.3 (and the fully-null
column list in Section 2.2, which names columns without stating their
category), plus pattern rules for the repeated numbered-slot columns
(ICD_DGNS_CD1..25 and friends) that Section 2.3 describes by pattern rather
than naming individually. See research.md ("Column categorization as a
static mapping, not inferred") for why this isn't dtype-based inference.
"""

import re

from app.data_engineering.schemas import ColumnCategory

_STATIC_CATEGORIES: dict[str, ColumnCategory] = {
    # Identifiers
    "BENE_ID": ColumnCategory.IDENTIFIER,
    "CLM_ID": ColumnCategory.IDENTIFIER,
    "PRVDR_NUM": ColumnCategory.IDENTIFIER,
    "ORG_NPI_NUM": ColumnCategory.IDENTIFIER,
    "AT_PHYSN_NPI": ColumnCategory.IDENTIFIER,
    "OP_PHYSN_NPI": ColumnCategory.IDENTIFIER,
    "OT_PHYSN_NPI": ColumnCategory.IDENTIFIER,
    "OT_PHYSN_UPIN": ColumnCategory.IDENTIFIER,
    "FI_NUM": ColumnCategory.IDENTIFIER,
    # Dates
    "CLM_FROM_DT": ColumnCategory.DATE,
    "CLM_THRU_DT": ColumnCategory.DATE,
    "NCH_WKLY_PROC_DT": ColumnCategory.DATE,
    "FI_CLM_PROC_DT": ColumnCategory.DATE,
    "CLM_ADMSN_DT": ColumnCategory.DATE,
    "NCH_BENE_DSCHRG_DT": ColumnCategory.DATE,
    "NCH_VRFD_NCVRD_STAY_FROM_DT": ColumnCategory.DATE,
    "NCH_VRFD_NCVRD_STAY_THRU_DT": ColumnCategory.DATE,
    "NCH_BENE_MDCR_BNFTS_EXHTD_DT_I": ColumnCategory.DATE,
    "NCH_ACTV_OR_CVRD_LVL_CARE_THRU": ColumnCategory.DATE,
    # Amounts
    "CLM_PMT_AMT": ColumnCategory.AMOUNT,
    "NCH_PRMRY_PYR_CLM_PD_AMT": ColumnCategory.AMOUNT,
    "CLM_TOT_CHRG_AMT": ColumnCategory.AMOUNT,
    "CLM_PASS_THRU_PER_DIEM_AMT": ColumnCategory.AMOUNT,
    "NCH_BENE_IP_DDCTBL_AMT": ColumnCategory.AMOUNT,
    "NCH_BENE_PTA_COINSRNC_LBLTY_AM": ColumnCategory.AMOUNT,
    "NCH_BENE_BLOOD_DDCTBL_LBLTY_AM": ColumnCategory.AMOUNT,
    "NCH_PROFNL_CMPNT_CHRG_AMT": ColumnCategory.AMOUNT,
    "NCH_IP_NCVRD_CHRG_AMT": ColumnCategory.AMOUNT,
    "NCH_IP_TOT_DDCTN_AMT": ColumnCategory.AMOUNT,
    "CLM_UNCOMPD_CARE_PMT_AMT": ColumnCategory.AMOUNT,
    # Utilization / duration
    "CLM_UTLZTN_DAY_CNT": ColumnCategory.UTILIZATION_DURATION,
    "BENE_TOT_COINSRNC_DAYS_CNT": ColumnCategory.UTILIZATION_DURATION,
    "BENE_LRD_USED_CNT": ColumnCategory.UTILIZATION_DURATION,
    "CLM_NON_UTLZTN_DAYS_CNT": ColumnCategory.UTILIZATION_DURATION,
    "NCH_BLOOD_PNTS_FRNSHD_QTY": ColumnCategory.UTILIZATION_DURATION,
    # Categorical / codes
    "NCH_NEAR_LINE_REC_IDENT_CD": ColumnCategory.CATEGORICAL_CODE,
    "NCH_CLM_TYPE_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLAIM_QUERY_CODE": ColumnCategory.CATEGORICAL_CODE,
    "CLM_FAC_TYPE_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_SRVC_CLSFCTN_TYPE_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_FREQ_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_MDCR_NON_PMT_RSN_CD": ColumnCategory.CATEGORICAL_CODE,
    "NCH_PRMRY_PYR_CD": ColumnCategory.CATEGORICAL_CODE,
    "PRVDR_STATE_CD": ColumnCategory.CATEGORICAL_CODE,
    "PTNT_DSCHRG_STUS_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_PPS_IND_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_IP_ADMSN_TYPE_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_SRC_IP_ADMSN_CD": ColumnCategory.CATEGORICAL_CODE,
    "NCH_PTNT_STATUS_IND_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_DRG_CD": ColumnCategory.CATEGORICAL_CODE,
    "CLM_DRG_OUTLIER_STAY_CD": ColumnCategory.CATEGORICAL_CODE,
    "HCPCS_CD": ColumnCategory.CATEGORICAL_CODE,
    "REV_CNTR": ColumnCategory.CATEGORICAL_CODE,
    "CLM_LINE_NUM": ColumnCategory.CATEGORICAL_CODE,
    "FI_CLM_ACTN_CD": ColumnCategory.CATEGORICAL_CODE,
    # Diagnosis / procedure codes
    "ADMTG_DGNS_CD": ColumnCategory.DIAGNOSIS_PROCEDURE_CODE,
    "PRNCPAL_DGNS_CD": ColumnCategory.DIAGNOSIS_PROCEDURE_CODE,
}

# Repeated numbered-slot columns (spec FR-007 / research.md pattern rules),
# for columns Section 2.3 describes by pattern rather than naming individually.
_PATTERN_CATEGORIES: list[tuple[re.Pattern[str], ColumnCategory]] = [
    (re.compile(r"^PRCDR_DT\d+$"), ColumnCategory.DATE),
    (re.compile(r"^ICD_DGNS_E_CD\d+$"), ColumnCategory.DIAGNOSIS_PROCEDURE_CODE),
    (re.compile(r"^ICD_DGNS_CD\d+$"), ColumnCategory.DIAGNOSIS_PROCEDURE_CODE),
    (re.compile(r"^ICD_PRCDR_CD\d+$"), ColumnCategory.DIAGNOSIS_PROCEDURE_CODE),
    (re.compile(r"^CLM_POA_IND_SW\d+$"), ColumnCategory.DIAGNOSIS_PROCEDURE_CODE),
    (re.compile(r"^CLM_(TOT_)?PPS_CPTL_"), ColumnCategory.AMOUNT),
    (re.compile(r"_NPI$"), ColumnCategory.IDENTIFIER),
    (re.compile(r"_UPIN$"), ColumnCategory.IDENTIFIER),
]

# Default for any column not covered by the static mapping or a pattern rule
# above (spec Assumptions: "categorized by applying the same category
# definitions used for the columns that are already confirmed").
_DEFAULT_CATEGORY = ColumnCategory.CATEGORICAL_CODE


def categorize(column_name: str) -> ColumnCategory:
    """Assign exactly one of the six fixed categories to a column name."""
    if column_name in _STATIC_CATEGORIES:
        return _STATIC_CATEGORIES[column_name]
    for pattern, category in _PATTERN_CATEGORIES:
        if pattern.search(column_name):
            return category
    return _DEFAULT_CATEGORY
