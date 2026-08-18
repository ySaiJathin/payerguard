import pandas as pd
import pytest

from app.data_engineering.categorization import categorize
from app.data_engineering.schemas import ColumnCategory

FIXTURE_PATH = __file__.replace("test_categorization.py", "../fixtures/inpatient_sample.csv")

# Columns explicitly categorized in MVP_CONTEXT.md Section 2.3.
DOCUMENTED_CATEGORIES = {
    "CLM_ID": ColumnCategory.IDENTIFIER,
    "BENE_ID": ColumnCategory.IDENTIFIER,
    "PRVDR_NUM": ColumnCategory.IDENTIFIER,
    "AT_PHYSN_NPI": ColumnCategory.IDENTIFIER,
    "CLM_FROM_DT": ColumnCategory.DATE,
    "CLM_THRU_DT": ColumnCategory.DATE,
    "CLM_PMT_AMT": ColumnCategory.AMOUNT,
    "CLM_TOT_CHRG_AMT": ColumnCategory.AMOUNT,
    "CLM_UTLZTN_DAY_CNT": ColumnCategory.UTILIZATION_DURATION,
    "CLM_IP_ADMSN_TYPE_CD": ColumnCategory.CATEGORICAL_CODE,
    "HCPCS_CD": ColumnCategory.CATEGORICAL_CODE,
    "REV_CNTR": ColumnCategory.CATEGORICAL_CODE,
    "PRNCPAL_DGNS_CD": ColumnCategory.DIAGNOSIS_PROCEDURE_CODE,
    "ADMTG_DGNS_CD": ColumnCategory.DIAGNOSIS_PROCEDURE_CODE,
}


@pytest.mark.parametrize("column_name,expected", list(DOCUMENTED_CATEGORIES.items()))
def test_documented_columns_match_mvp_context(column_name, expected):
    assert categorize(column_name) == expected


@pytest.mark.parametrize(
    "column_name",
    ["ICD_DGNS_CD1", "ICD_DGNS_CD25", "ICD_PRCDR_CD1", "ICD_DGNS_E_CD1", "CLM_POA_IND_SW1"],
)
def test_repeated_diagnosis_procedure_slot_columns(column_name):
    assert categorize(column_name) == ColumnCategory.DIAGNOSIS_PROCEDURE_CODE


@pytest.mark.parametrize("column_name", ["PRCDR_DT1", "PRCDR_DT25"])
def test_repeated_procedure_date_slot_columns(column_name):
    assert categorize(column_name) == ColumnCategory.DATE


def test_fully_null_column_still_gets_a_category():
    # OT_PHYSN_UPIN is 100% missing in the real dataset (MVP_CONTEXT.md 2.2)
    # but must still be categorized, not skipped.
    assert categorize("OT_PHYSN_UPIN") == ColumnCategory.IDENTIFIER


def test_every_fixture_column_gets_exactly_one_category():
    df = pd.read_csv(FIXTURE_PATH, sep="|")
    for column in df.columns:
        category = categorize(column)
        assert isinstance(category, ColumnCategory)
