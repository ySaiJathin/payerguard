"""Integration test: profiling the real inpatient.csv must match the
ground-truth figures measured in MVP_CONTEXT.md Section 2.2 exactly
(spec SC-003). Skipped if the raw file hasn't been supplied yet.
"""

import pytest

from app.data_engineering.paths import raw_inpatient_csv
from app.data_engineering.profiling_service import generate_profiling_report

RAW_FILE = raw_inpatient_csv()

pytestmark = pytest.mark.skipif(
    not RAW_FILE.exists(), reason=f"real dataset not present at {RAW_FILE}"
)


def test_real_file_matches_mvp_context_ground_truth():
    report = generate_profiling_report(RAW_FILE)

    assert report.total_rows == 58066
    assert report.total_columns == 197
    assert report.unique_claim_count == 20867
    assert report.unique_beneficiary_count == 5699
    assert report.duplicate_row_count == 0
    assert len(report.columns) == 197
    assert all(col.category is not None for col in report.columns)
