"""spec SC-002: every malformed/non-conformant upload is rejected with a
specific, actionable reason before any pipeline stage runs.
"""

import pytest

from app.ingestion import upload_validation
from tests.ingestion._fixtures import raw_claims_fixture, write_fixture_categories


def test_conformant_file_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_validation, "MIN_ROWS", 3)
    categories_path = write_fixture_categories(tmp_path)

    frame, row_count = upload_validation.validate_and_load(
        raw_claims_fixture(), "inpatient_sample.csv", categories_path
    )

    assert row_count == 6
    assert list(frame.columns) == [
        "BENE_ID",
        "CLM_ID",
        "CLM_FROM_DT",
        "CLM_THRU_DT",
        "CLM_PMT_AMT",
        "CLM_IP_ADMSN_TYPE_CD",
        "PRNCPAL_DGNS_CD",
        "OT_PHYSN_UPIN",
        "CLM_LINE_NUM",
    ]


def test_empty_file_rejected(tmp_path):
    categories_path = write_fixture_categories(tmp_path)
    with pytest.raises(upload_validation.UploadRejectionError) as exc_info:
        upload_validation.validate_and_load(b"", "empty.csv", categories_path)
    assert exc_info.value.reason_code == "empty_file"


def test_above_max_size_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_validation, "MAX_UPLOAD_BYTES", 10)
    categories_path = write_fixture_categories(tmp_path)
    with pytest.raises(upload_validation.UploadRejectionError) as exc_info:
        upload_validation.validate_and_load(raw_claims_fixture(), "inpatient_sample.csv", categories_path)
    assert exc_info.value.reason_code == "above_max_size"


def test_wrong_delimiter_rejected(tmp_path):
    categories_path = write_fixture_categories(tmp_path)
    comma_content = raw_claims_fixture().replace(b"|", b",")
    with pytest.raises(upload_validation.UploadRejectionError) as exc_info:
        upload_validation.validate_and_load(comma_content, "comma.csv", categories_path)
    assert exc_info.value.reason_code == "wrong_delimiter"


def test_missing_columns_rejected(tmp_path):
    categories_path = write_fixture_categories(tmp_path)
    # Drop the last column from the header and every data row.
    lines = raw_claims_fixture().decode("utf-8").splitlines()
    truncated = "\n".join("|".join(line.split("|")[:-1]) for line in lines).encode("utf-8")
    with pytest.raises(upload_validation.UploadRejectionError) as exc_info:
        upload_validation.validate_and_load(truncated, "truncated.csv", categories_path)
    assert exc_info.value.reason_code == "missing_columns"
    assert "CLM_LINE_NUM" in exc_info.value.detail


def test_unexpected_columns_rejected(tmp_path):
    categories_path = write_fixture_categories(tmp_path)
    lines = raw_claims_fixture().decode("utf-8").splitlines()
    header = lines[0] + "|EXTRA_COL"
    rows = [line + "|X" for line in lines[1:]]
    with_extra = "\n".join([header] + rows).encode("utf-8")
    with pytest.raises(upload_validation.UploadRejectionError) as exc_info:
        upload_validation.validate_and_load(with_extra, "extra.csv", categories_path)
    assert exc_info.value.reason_code == "unexpected_columns"


def test_below_min_rows_rejected(tmp_path):
    # Default MIN_ROWS (100) comfortably exceeds this 6-row fixture.
    categories_path = write_fixture_categories(tmp_path)
    with pytest.raises(upload_validation.UploadRejectionError) as exc_info:
        upload_validation.validate_and_load(raw_claims_fixture(), "inpatient_sample.csv", categories_path)
    assert exc_info.value.reason_code == "below_min_rows"
