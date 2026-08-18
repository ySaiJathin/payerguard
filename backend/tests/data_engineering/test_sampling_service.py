import hashlib
from pathlib import Path

import pandas as pd
import pytest

from app.data_engineering.sampling_service import SamplingError, generate_sample

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "inpatient_sample.csv"
FIXTURE_COLUMN_COUNT = 9  # backend/tests/fixtures/inpatient_sample.csv has 9 columns


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reproducible_sample_same_seed_and_fraction(tmp_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    manifest1 = generate_sample(
        seed=7, target_claim_fraction=0.4, source_path=FIXTURE, out_dir=out1,
        expected_column_count=FIXTURE_COLUMN_COUNT,
    )
    manifest2 = generate_sample(
        seed=7, target_claim_fraction=0.4, source_path=FIXTURE, out_dir=out2,
        expected_column_count=FIXTURE_COLUMN_COUNT,
    )

    assert manifest1.claims_included == manifest2.claims_included
    file1 = Path(manifest1.output_file)
    file2 = Path(manifest2.output_file)
    assert file1.read_text(encoding="utf-8") == file2.read_text(encoding="utf-8")


def test_degenerate_fraction_selecting_zero_claims_is_rejected(tmp_path):
    with pytest.raises(SamplingError):
        generate_sample(
            seed=1, target_claim_fraction=0.05, source_path=FIXTURE, out_dir=tmp_path,
            expected_column_count=FIXTURE_COLUMN_COUNT,
        )


def test_zero_fraction_rejected(tmp_path):
    with pytest.raises(SamplingError):
        generate_sample(
            seed=1, target_claim_fraction=0.0, source_path=FIXTURE, out_dir=tmp_path,
            expected_column_count=FIXTURE_COLUMN_COUNT,
        )


def test_source_file_untouched_by_sampling(tmp_path):
    source_copy = tmp_path / "source.csv"
    source_copy.write_bytes(FIXTURE.read_bytes())
    before = _checksum(source_copy)

    generate_sample(
        seed=1, target_claim_fraction=0.4, source_path=source_copy, out_dir=tmp_path / "out",
        expected_column_count=FIXTURE_COLUMN_COUNT,
    )

    assert _checksum(source_copy) == before


def test_no_claim_split_across_sample_boundary(tmp_path):
    manifest = generate_sample(
        seed=3, target_claim_fraction=0.6, source_path=FIXTURE, out_dir=tmp_path,
        expected_column_count=FIXTURE_COLUMN_COUNT,
    )

    raw = pd.read_csv(FIXTURE, sep="|")
    sample = pd.read_csv(manifest.output_file, sep="|")

    for clm_id in sample["CLM_ID"].unique():
        assert (sample["CLM_ID"] == clm_id).sum() == (raw["CLM_ID"] == clm_id).sum()
