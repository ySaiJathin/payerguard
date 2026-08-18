"""SC-005: no field named or semantically equivalent to "processing
time", "SLA", or "turnaround" appears anywhere in this feature's output
schema. Automated counterpart to quickstart.md's manual curl|python check.
"""

from datetime import datetime, timezone

import pandas as pd

from app.baseline.amount_baseline import compute_amount_baselines
from app.baseline.data_health_baseline import compute_data_health_baseline
from app.baseline.length_of_stay_baseline import compute_length_of_stay_baseline
from app.baseline.schemas import BaselineSnapshot, SourceDateRange
from app.baseline.volume_baseline import compute_volume_baseline
from app.data_engineering.schemas import ColumnCategory

_FORBIDDEN_TERMS = ("processing_time", "sla", "turnaround")


def _fixture_df():
    return pd.DataFrame(
        {
            "CLM_FROM_DT": ["2026-01-01", "2026-01-02"],
            "CLM_ADMSN_DT": ["2026-01-01", "2026-01-02"],
            "NCH_BENE_DSCHRG_DT": ["2026-01-03", "2026-01-05"],
            "CLM_PMT_AMT": [100.0, 200.0],
            "PTNT_DSCHRG_STUS_CD": ["1", "1"],
        }
    )


def test_full_snapshot_has_no_processing_time_sla_or_turnaround_field():
    df = _fixture_df()
    categories = {"CLM_PMT_AMT": ColumnCategory.AMOUNT}

    snapshot = BaselineSnapshot(
        snapshot_id="snap-1",
        source_file="fixture.csv",
        source_row_count=len(df),
        source_date_range=SourceDateRange(min_date="2026-01-01", max_date="2026-01-02"),
        volume_baseline=compute_volume_baseline(df),
        amount_baselines=compute_amount_baselines(df, categories),
        data_health_baseline=compute_data_health_baseline(df, check_results=[]),
        length_of_stay_baseline=compute_length_of_stay_baseline(df),
        computed_at=datetime.now(timezone.utc),
    )

    blob = snapshot.model_dump_json().lower()
    for term in _FORBIDDEN_TERMS:
        assert term not in blob, f"forbidden term {term!r} found in BaselineSnapshot output"


def test_schema_field_names_avoid_forbidden_terms():
    for model in (BaselineSnapshot,):
        for field_name in model.model_fields:
            lowered = field_name.lower()
            for term in _FORBIDDEN_TERMS:
                assert term not in lowered, f"field {field_name!r} contains forbidden term {term!r}"
