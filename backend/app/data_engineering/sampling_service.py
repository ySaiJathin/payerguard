"""Claim-consistent, reproducible sampling of inpatient.csv.

See research.md ("Sampling by claim (CLM_ID) with a fixed seed") --
sampling selects whole claims so no claim's line items are split across
the included/excluded boundary, and a fixed seed makes the same
configuration reproducible run to run (FR-009, FR-011, SC-004, SC-005).
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.data_engineering.paths import raw_inpatient_csv, sampled_dir
from app.data_engineering.profiling_service import (
    CLM_ID_COLUMN,
    EXPECTED_COLUMN_COUNT,
    ProfilingError,
    load_source_csv,
)
from app.data_engineering.schemas import SampleManifest

DEFAULT_SEED = 42
# 8%, not 10% -- claims average 2.82 line-items each (right-skewed), so a
# 10% claim-fraction sample has an *expected* row-reduction ratio of only
# ~10.0x, meaning ordinary sampling variance can land it under the SC-004
# "at least 10x smaller" bar (spec Assumptions explicitly allows tuning this
# default). 8% builds in headroom (~12.5x expected) so SC-004 holds reliably.
DEFAULT_TARGET_CLAIM_FRACTION = 0.08
SAMPLE_FILENAME = "inpatient_sample.csv"


class SamplingError(ValueError):
    """Source file missing/malformed, or the configured fraction is degenerate."""


def generate_sample(
    seed: int = DEFAULT_SEED,
    target_claim_fraction: float = DEFAULT_TARGET_CLAIM_FRACTION,
    source_path: Path | None = None,
    out_dir: Path | None = None,
    expected_column_count: int | None = EXPECTED_COLUMN_COUNT,
) -> SampleManifest:
    if not (0 < target_claim_fraction <= 1):
        raise SamplingError(
            f"target_claim_fraction must be in (0, 1], got {target_claim_fraction}"
        )

    source = source_path or raw_inpatient_csv()
    try:
        df = load_source_csv(source, expected_column_count=expected_column_count)
    except ProfilingError as exc:
        raise SamplingError(str(exc)) from exc

    claim_ids = df[CLM_ID_COLUMN].drop_duplicates().sort_values().reset_index(drop=True)
    target_count = int(round(len(claim_ids) * target_claim_fraction))
    if target_count == 0:
        raise SamplingError(
            f"target_claim_fraction={target_claim_fraction} selects zero claims out of "
            f"{len(claim_ids)} -- refusing to produce an empty sample."
        )

    # A seeded RandomState keyed off the sorted claim list gives the same
    # selection every run for the same (seed, fraction, source file).
    rng = np.random.RandomState(seed)
    selected = rng.choice(claim_ids.to_numpy(), size=target_count, replace=False)
    selected_set = set(selected.tolist())

    sample_df = df[df[CLM_ID_COLUMN].isin(selected_set)]

    out_dir = out_dir or sampled_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / SAMPLE_FILENAME
    sample_df.to_csv(output_path, sep="|", index=False)

    return SampleManifest(
        output_file=str(output_path),
        source_file=str(source),
        seed=seed,
        target_claim_fraction=target_claim_fraction,
        claims_included=len(selected_set),
        rows_included=len(sample_df),
        generated_at=datetime.now(timezone.utc),
    )
