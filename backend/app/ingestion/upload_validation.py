"""Raw-schema conformance validation for uploaded claims files (spec
FR-001, FR-002, FR-010).

Validates against the **raw**, pre-cleaning 197-column schema Phase 1
profiled (`app.data_engineering.dtype_conversion.load_column_categories`)
-- not the cleaned schema `app.demo.upload` validates against (see
research.md's first decision; the two are deliberately separate).

Unlike `app.demo.upload`'s delimiter sniffing (comma- or pipe-, for demo
convenience), this module requires pipe-delimited input outright:
`app.data_engineering.cleaning_service.run_cleaning` reads whatever gets
persisted here via `load_source_csv`, which hardcodes `sep="|"`
(MVP_CONTEXT.md Section 2.1) -- silently re-serializing a comma-delimited
upload to match would risk a lossy round-trip the raw production path
should not accept. A comma-delimited (or otherwise malformed) file is
rejected as `wrong_delimiter`/`unparseable` instead.
"""

import io
from pathlib import Path

import pandas as pd

from app.data_engineering.dtype_conversion import CategoriesUnavailableError, load_column_categories

# MVP defaults (spec Assumptions) -- not user-configurable this pass.
# MAX_UPLOAD_BYTES matches app/demo/router.py's existing limit for
# consistency across the codebase's two upload paths.
MAX_UPLOAD_BYTES = 64 * 1024 * 1024
MIN_ROWS = 100
MAX_ISSUES_REPORTED = 12


class UploadRejectionError(ValueError):
    """Raised when an uploaded file fails raw-schema conformance. Carries
    the specific `reason_code`/`detail` the router turns into a 422/413
    body (contracts/api.md)."""

    def __init__(self, reason_code: str, detail: str):
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(detail)


def _expected_columns(categories_path: Path | None = None) -> list[str]:
    try:
        categories = load_column_categories(categories_path)
    except CategoriesUnavailableError as exc:
        # Phase 1 profiling defines the raw schema; without it there is
        # nothing to validate against, and no fabricated schema is used
        # instead (constitution Principle II).
        raise UploadRejectionError(
            "unparseable",
            "No raw column schema is available yet (Phase 1 profiling has not run) -- "
            "the uploaded file cannot be validated.",
        ) from exc
    return list(categories.keys())


def validate_and_load(
    content: bytes, filename: str, categories_path: Path | None = None
) -> tuple[pd.DataFrame, int]:
    """Returns the validated, pipe-delimited raw frame and its row count,
    or raises `UploadRejectionError` naming exactly what is wrong (spec
    FR-002, SC-002) -- before any pipeline stage runs.

    `categories_path` overrides where the expected raw-schema column set
    is read from (default: Phase 1's real project profiling report) --
    tests point it at a small fixture schema, matching the override
    convention `load_column_categories` itself already provides."""
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadRejectionError(
            "above_max_size",
            f"{filename!r} is {len(content) / 1e6:.1f} MB; the limit is {MAX_UPLOAD_BYTES / 1e6:.0f} MB.",
        )
    if not content:
        raise UploadRejectionError("empty_file", f"{filename!r} is empty.")

    expected = _expected_columns(categories_path)

    try:
        frame = pd.read_csv(io.BytesIO(content), sep="|", dtype=str, low_memory=False)
    except Exception as exc:  # noqa: BLE001 -- surfaced as a rejection, not a 500
        raise UploadRejectionError(
            "unparseable", f"{filename!r} could not be parsed as a pipe-delimited table: {exc}"
        ) from exc

    if frame.shape[1] <= 1:
        raise UploadRejectionError(
            "wrong_delimiter",
            f"{filename!r} parsed to a single column -- it does not look pipe-delimited "
            "(the real CMS extract is pipe-delimited despite its .csv extension).",
        )

    present = set(frame.columns)
    missing = [c for c in expected if c not in present]
    unexpected = [c for c in frame.columns if c not in expected]

    if missing:
        shown = ", ".join(missing[:MAX_ISSUES_REPORTED])
        more = f" (and {len(missing) - MAX_ISSUES_REPORTED} more)" if len(missing) > MAX_ISSUES_REPORTED else ""
        raise UploadRejectionError(
            "missing_columns",
            f"{filename!r} is missing {len(missing)} of the {len(expected)} expected raw claim "
            f"columns: {shown}{more}.",
        )
    if unexpected:
        shown = ", ".join(unexpected[:MAX_ISSUES_REPORTED])
        raise UploadRejectionError(
            "unexpected_columns",
            f"{filename!r} carries {len(unexpected)} column(s) outside the raw claims schema: {shown}.",
        )

    if len(frame) < MIN_ROWS:
        raise UploadRejectionError(
            "below_min_rows",
            f"{filename!r} has only {len(frame)} row(s); at least {MIN_ROWS} are needed to process a batch.",
        )

    return frame[expected], len(frame)
