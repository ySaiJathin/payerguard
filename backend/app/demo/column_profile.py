"""Learns a per-column statistical profile of the real cleaned batch, so the
synthetic generator can emit rows with the *same schema and the same shape*
rather than invented columns.

The profile is built once from `data/cleaned/inpatient_cleaned.csv` (Phase
2's output) plus Phase 1's `column_categories.json`, and cached as
`data/demo/synthetic/column_profile.json`. It records, per column:

- its Phase 1 category (identifier / date / amount / ... ), which decides
  how values are synthesised and what dtype the CSV round-trips as;
- its measured missing rate, so synthetic batches inherit the source's real
  structural missingness (columns that are 100% null in the source stay
  100% null, which is what the completeness calibration expects);
- a value pool for coded/identifier columns and a log-normal fit for amount
  columns, so generated values fall inside the code sets and ranges the
  Great Expectations suites check against.

No number in here is hardcoded: re-running `build_column_profile()` against
a different source file re-derives all of it.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.data_engineering.cleaning_service import CLEANED_OUTPUT_FILENAME
from app.data_engineering.dtype_conversion import load_column_categories
from app.data_engineering.paths import cleaned_dir
from app.demo.paths import column_profile_path
from app.quality.data_loader import load_cleaned_batch
from app.quality.schemas import ColumnCategory

# Enough rows to characterise 197 columns without reading the whole 58k-row
# batch on every cold start; the pools/fits are stable well below this.
PROFILE_SAMPLE_ROWS = 20000
MAX_POOL_SIZE = 60


class DemoProfileUnavailableError(FileNotFoundError):
    """Raised when neither a cached profile nor the cleaned source batch it
    would be derived from exists."""


def _pool(series: pd.Series) -> dict:
    counts = series.dropna().astype(str).value_counts()
    if counts.empty:
        return {"values": [], "weights": []}
    counts = counts.head(MAX_POOL_SIZE)
    total = float(counts.sum())
    return {"values": [str(v) for v in counts.index], "weights": [float(c) / total for c in counts]}


def _amount_fit(series: pd.Series) -> dict:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"zero_pct": 1.0, "log_mu": 0.0, "log_sigma": 0.0, "min": 0.0, "max": 0.0}
    positive = values[values > 0]
    zero_pct = float((values <= 0).mean())
    if positive.empty:
        return {"zero_pct": 1.0, "log_mu": 0.0, "log_sigma": 0.0, "min": float(values.min()), "max": float(values.max())}
    logs = np.log(positive.to_numpy(dtype=float))
    return {
        "zero_pct": zero_pct,
        "log_mu": float(logs.mean()),
        "log_sigma": float(logs.std()) or 0.5,
        "min": float(values.min()),
        "max": float(values.max()),
    }


def _int_fit(series: pd.Series) -> dict:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"min": 0, "max": 0, "mean": 0.0}
    return {"min": int(values.min()), "max": int(values.max()), "mean": float(values.mean())}


def build_column_profile(source: Path | None = None) -> dict:
    """Derives and caches the column profile. Call this to reseed the
    generator after the source batch changes."""
    categories = load_column_categories()
    source = source or (cleaned_dir() / CLEANED_OUTPUT_FILENAME)
    if not source.exists():
        raise DemoProfileUnavailableError(
            f"Cannot build a demo column profile: no cleaned batch at {source}."
        )

    df = load_cleaned_batch(source, categories)
    if len(df) > PROFILE_SAMPLE_ROWS:
        df = df.sample(PROFILE_SAMPLE_ROWS, random_state=0)

    columns: list[dict] = []
    for name in df.columns:
        category = categories.get(name)
        series = df[name]
        entry: dict = {
            "name": name,
            "category": category.value if category is not None else None,
            "missing_pct": float(series.isna().mean() * 100.0),
        }
        if category in (ColumnCategory.AMOUNT,):
            entry["amount"] = _amount_fit(series)
        elif category is ColumnCategory.UTILIZATION_DURATION:
            entry["integer"] = _int_fit(series)
            entry["pool"] = _pool(series)
        elif category is ColumnCategory.DATE:
            parsed = pd.to_datetime(series, errors="coerce")
            entry["date"] = {
                "min": parsed.min().date().isoformat() if parsed.notna().any() else None,
                "max": parsed.max().date().isoformat() if parsed.notna().any() else None,
            }
        else:
            entry["pool"] = _pool(series)
        columns.append(entry)

    profile = {
        "source_file": str(source),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sampled_rows": int(len(df)),
        "column_order": list(df.columns),
        "columns": columns,
    }
    column_profile_path().write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return profile


def load_column_profile(rebuild: bool = False) -> dict:
    path = column_profile_path()
    if rebuild or not path.exists():
        return build_column_profile()
    return json.loads(path.read_text(encoding="utf-8"))
