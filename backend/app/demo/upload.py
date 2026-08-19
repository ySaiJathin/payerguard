"""Schema-validated file upload, feeding the identical pipeline.

An uploaded file is checked against the expected claim schema *before*
anything is run, and a mismatch is reported as a clear, specific error --
which columns are missing, which are unexpected -- rather than failing
somewhere deep in the quality suite with an unrelated message.

Once accepted, the frame goes through `pipeline.run_pipeline`, the same
function the synthetic batches use. There is no separate upload pipeline.
"""

import io
from datetime import datetime, timezone

import pandas as pd

from app.data_engineering.dtype_conversion import load_column_categories
from app.demo import paths
from app.demo.column_profile import load_column_profile
from app.demo.generator import (
    CLAIM_FROM_COLUMN,
    GROUND_TRUTH_COLUMN,
    NO_INJECTION,
    ROW_KEY_COLUMN,
)
from app.quality.data_loader import _dtype_map

REQUIRED_COLUMNS = ("CLM_ID", "CLM_FROM_DT", "CLM_THRU_DT", "CLM_PMT_AMT")
MAX_MISSING_COLUMNS_REPORTED = 12
MIN_ROWS = 100


class UploadSchemaError(ValueError):
    """Raised when an uploaded file does not match the expected schema."""


def _read_any(content: bytes, filename: str) -> pd.DataFrame:
    """Accepts comma- or pipe-delimited text; the real CMS extract is
    pipe-delimited despite its `.csv` extension, so sniffing the separator
    is not optional."""
    categories = load_column_categories()
    dtypes = _dtype_map(categories)
    for separator in (",", "|"):
        try:
            frame = pd.read_csv(io.BytesIO(content), sep=separator, dtype=dtypes, low_memory=False)
        except Exception:  # noqa: BLE001 -- try the next separator
            continue
        if frame.shape[1] > 1:
            return frame
    raise UploadSchemaError(
        f"Could not parse {filename!r} as a comma- or pipe-delimited table with more than one column."
    )


def validate_and_load(content: bytes, filename: str) -> tuple[pd.DataFrame, pd.Series]:
    """Returns the accepted frame and an all-`none` ground-truth label
    series -- an uploaded file has no injected anomalies to know about, so
    every row is honestly labelled as not-injected. Detection still runs;
    only the per-injection-type recall breakdown is necessarily empty,
    because there is no ground truth to measure it against."""
    profile = load_column_profile()
    expected = list(profile["column_order"])

    frame = _read_any(content, filename)
    frame = frame.drop(columns=[c for c in (ROW_KEY_COLUMN, GROUND_TRUTH_COLUMN) if c in frame.columns])

    present = set(frame.columns)
    missing = [column for column in expected if column not in present]
    unexpected = [column for column in frame.columns if column not in expected]

    if missing:
        shown = ", ".join(missing[:MAX_MISSING_COLUMNS_REPORTED])
        more = f" (and {len(missing) - MAX_MISSING_COLUMNS_REPORTED} more)" if len(missing) > MAX_MISSING_COLUMNS_REPORTED else ""
        raise UploadSchemaError(
            f"{filename!r} is missing {len(missing)} of the {len(expected)} expected claim columns: {shown}{more}. "
            "The file must match the cleaned claims schema exactly."
        )
    if unexpected:
        shown = ", ".join(unexpected[:MAX_MISSING_COLUMNS_REPORTED])
        raise UploadSchemaError(
            f"{filename!r} carries {len(unexpected)} column(s) that are not part of the claims schema: {shown}."
        )
    for column in REQUIRED_COLUMNS:
        if frame[column].isna().all():
            raise UploadSchemaError(
                f"{filename!r} has no values at all in {column}, which the pipeline requires."
            )
    if len(frame) < MIN_ROWS:
        raise UploadSchemaError(
            f"{filename!r} has only {len(frame)} row(s); at least {MIN_ROWS} are needed to fit a detector."
        )
    if pd.to_datetime(frame[CLAIM_FROM_COLUMN], errors="coerce").notna().sum() == 0:
        raise UploadSchemaError(
            f"{filename!r} has no parseable dates in {CLAIM_FROM_COLUMN}; claims cannot be windowed."
        )

    frame = frame[expected]
    frame.index = pd.Index([f"UPL-R{i:06d}" for i in range(len(frame))], name=ROW_KEY_COLUMN)
    labels = pd.Series(NO_INJECTION, index=frame.index, name=GROUND_TRUTH_COLUMN)
    return frame, labels


def persist_upload(content: bytes, filename: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(c for c in filename if c.isalnum() or c in "._-") or "upload.csv"
    path = paths.uploads_dir() / f"{stamp}-{safe}"
    path.write_bytes(content)
    return path.name
