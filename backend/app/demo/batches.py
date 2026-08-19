"""The three demo batches: their specs, their generation, and their manifest.

These specs are the single source of demo data. The dashboard's first-load
state, the Simulator's batch picker and the validation runs all read the
same three batches -- there is no second, disconnected set of demo files.

The three differ deliberately along every axis the dashboard renders, so
running the pipeline three times produces three visibly different pictures
rather than the same output repeated:

- **batch-1 (Steady state)** -- the reference batch. Moderate volume, the
  source's natural amount distribution, a light sprinkle of all five
  injection types, so every panel has representative data on first load.
- **batch-2 (Data quality degradation)** -- larger volume, a real
  structural missingness increase and a genuine duplicate rate, with
  injections skewed to missing-value and duplicate spikes. Quality score
  drops; completeness/missing-rate/duplicate-rate checks are the ones that
  fail.
- **batch-3 (Payment anomaly surge)** -- smaller volume, a heavier and
  wider amount distribution, injections skewed to amount spikes, volume
  drops and distribution shifts. Quality stays high; the anomaly and risk
  panels are where this batch shows up.
"""

import json
from datetime import datetime, timezone

import pandas as pd

from app.demo import paths
from app.demo.column_profile import load_column_profile
from app.demo.generator import (
    CLAIM_FROM_COLUMN,
    GROUND_TRUTH_COLUMN,
    NO_INJECTION,
    PAYMENT_COLUMN,
    ROW_KEY_COLUMN,
    generate_batch,
    ground_truth_frame,
)
from app.demo.schemas import (
    BatchManifestEntry,
    BatchSpec,
    InjectionCluster,
    InjectionPlan,
    InjectionType,
)

BATCH_SPECS: list[BatchSpec] = [
    BatchSpec(
        batch_id="batch-1",
        label="Steady state",
        description=(
            "Reference batch: the source amount distribution, no structural "
            "degradation, and three incident clusters of decreasing severity so "
            "every band on the dashboard is populated on first load."
        ),
        claim_count=3000,
        start_date="2026-01-05",
        end_date="2026-03-29",
        seed=101,
        amount_scale=1.0,
        amount_spread=1.0,
        extra_missing_pct=0.0,
        duplicate_rate=0.004,
        injection_plan=InjectionPlan(
            clusters=[
                # Four failure modes in one fully corrupted week, including
                # the sign error that fails amount validity -- the critical
                # incident.
                InjectionCluster(
                    name="severe-multi-failure",
                    rates={
                        InjectionType.missing_value_spike: 0.020,
                        InjectionType.duplicate_spike: 0.016,
                        InjectionType.amount_spike: 0.020,
                        InjectionType.distribution_shift: 0.016,
                    },
                    density=1.0,
                ),
                # A truncated extract replayed twice: completeness and
                # uniqueness fail, amounts stay sane. Lands in HIGH.
                InjectionCluster(
                    name="truncated-replay",
                    rates={
                        InjectionType.missing_value_spike: 0.016,
                        InjectionType.duplicate_spike: 0.014,
                    },
                    density=1.0,
                ),
                # Payment-side only, partly diluted by healthy claims.
                InjectionCluster(
                    name="payment-and-shift",
                    rates={
                        InjectionType.amount_spike: 0.012,
                        InjectionType.distribution_shift: 0.012,
                    },
                    density=0.8,
                ),
                # A single failure mode: a short delivery.
                InjectionCluster(
                    name="short-delivery",
                    rates={InjectionType.volume_drop: 0.014},
                    density=0.6,
                ),
            ],
            rates={
                InjectionType.missing_value_spike: 0.004,
                InjectionType.duplicate_spike: 0.004,
                InjectionType.volume_drop: 0.004,
            },
            background_density=0.5,
        ),
    ),
    BatchSpec(
        batch_id="batch-2",
        label="Data quality degradation",
        description=(
            "High volume with a real missingness increase and duplicate rate "
            "across the whole batch; clusters skewed to missing-value and "
            "duplicate spikes."
        ),
        claim_count=4800,
        start_date="2026-03-30",
        end_date="2026-06-21",
        seed=202,
        amount_scale=0.85,
        amount_spread=0.9,
        extra_missing_pct=9.0,
        duplicate_rate=0.035,
        injection_plan=InjectionPlan(
            clusters=[
                InjectionCluster(
                    name="extract-truncation",
                    rates={
                        InjectionType.missing_value_spike: 0.045,
                        InjectionType.duplicate_spike: 0.030,
                    },
                    density=1.0,
                ),
                InjectionCluster(
                    name="replayed-batch",
                    rates={InjectionType.duplicate_spike: 0.020},
                    density=0.8,
                ),
            ],
            rates={
                InjectionType.missing_value_spike: 0.015,
                InjectionType.amount_spike: 0.010,
                InjectionType.volume_drop: 0.010,
                InjectionType.distribution_shift: 0.015,
            },
            background_density=0.6,
        ),
    ),
    BatchSpec(
        batch_id="batch-3",
        label="Payment anomaly surge",
        description=(
            "Lower volume, a heavier and wider payment distribution, and "
            "clusters skewed to amount spikes and distribution shifts."
        ),
        claim_count=1900,
        start_date="2026-06-22",
        end_date="2026-08-16",
        seed=303,
        amount_scale=1.9,
        amount_spread=1.45,
        extra_missing_pct=0.5,
        duplicate_rate=0.001,
        injection_plan=InjectionPlan(
            clusters=[
                InjectionCluster(
                    name="mapping-fault",
                    rates={
                        InjectionType.amount_spike: 0.045,
                        InjectionType.distribution_shift: 0.030,
                        InjectionType.missing_value_spike: 0.010,
                    },
                    density=1.0,
                ),
                InjectionCluster(
                    name="late-delivery",
                    rates={InjectionType.volume_drop: 0.020},
                    density=0.7,
                ),
            ],
            rates={
                InjectionType.amount_spike: 0.020,
                InjectionType.distribution_shift: 0.020,
                InjectionType.duplicate_spike: 0.005,
            },
            background_density=0.6,
        ),
    ),
]

SPECS_BY_ID = {spec.batch_id: spec for spec in BATCH_SPECS}


class UnknownBatchError(KeyError):
    """Raised for a batch id that isn't one of the three demo batches."""


def spec_for(batch_id: str) -> BatchSpec:
    try:
        return SPECS_BY_ID[batch_id]
    except KeyError as exc:
        raise UnknownBatchError(
            f"Unknown demo batch {batch_id!r}. Known batches: {', '.join(SPECS_BY_ID)}."
        ) from exc


def _manifest_entry(spec: BatchSpec, df: pd.DataFrame, labels: pd.Series) -> BatchManifestEntry:
    injected = labels[labels != NO_INJECTION]
    amounts = pd.to_numeric(df[PAYMENT_COLUMN], errors="coerce")
    dates = pd.to_datetime(df[CLAIM_FROM_COLUMN], errors="coerce")
    total_cells = df.shape[0] * df.shape[1]
    return BatchManifestEntry(
        batch_id=spec.batch_id,
        label=spec.label,
        description=spec.description,
        file=paths.batch_csv_path(spec.batch_id).name,
        ground_truth_file=paths.ground_truth_path(spec.batch_id).name,
        rows=int(len(df)),
        claims=int(df["CLM_ID"].nunique()),
        injected_rows=int(len(injected)),
        injected_counts={k: int(v) for k, v in injected.value_counts().items()},
        date_from=dates.min().date().isoformat(),
        date_to=dates.max().date().isoformat(),
        clm_pmt_amt_sum=float(amounts.sum()),
        clm_pmt_amt_median=float(amounts.median()),
        duplicate_rows=int(df.duplicated(keep="first").sum()),
        missing_cell_pct=float(df.isna().sum().sum() / total_cells * 100.0) if total_cells else 0.0,
        generated_at=datetime.now(timezone.utc),
        spec=spec,
    )


def generate_all(force: bool = True) -> list[BatchManifestEntry]:
    """Regenerates all three batches and rewrites the manifest.

    This is the reseed entry point -- `python -m app.demo.batches` and
    `POST /demo/batches/regenerate` both land here.
    """
    profile = load_column_profile()
    entries: list[BatchManifestEntry] = []
    for spec in BATCH_SPECS:
        csv_path = paths.batch_csv_path(spec.batch_id)
        truth_path = paths.ground_truth_path(spec.batch_id)
        if not force and csv_path.exists() and truth_path.exists():
            df, labels = load_batch(spec.batch_id)
        else:
            df, labels = generate_batch(spec, profile)
            df.to_csv(csv_path, index_label=ROW_KEY_COLUMN)
            ground_truth_frame(df, labels).to_csv(truth_path, index=False)
        entries.append(_manifest_entry(spec, df, labels))

    paths.manifest_path().write_text(
        json.dumps([json.loads(e.model_dump_json()) for e in entries], indent=2), encoding="utf-8"
    )
    return entries


def read_manifest() -> list[BatchManifestEntry]:
    path = paths.manifest_path()
    if not path.exists():
        return generate_all(force=True)
    return [BatchManifestEntry.model_validate(e) for e in json.loads(path.read_text(encoding="utf-8"))]


def ensure_generated() -> list[BatchManifestEntry]:
    """Generates any batch whose files are missing, leaving existing ones
    untouched -- used on the read paths so a cold checkout self-seeds."""
    missing = [
        spec
        for spec in BATCH_SPECS
        if not paths.batch_csv_path(spec.batch_id).exists()
        or not paths.ground_truth_path(spec.batch_id).exists()
    ]
    if missing or not paths.manifest_path().exists():
        return generate_all(force=False)
    return read_manifest()


def load_batch(batch_id: str) -> tuple[pd.DataFrame, pd.Series]:
    """Reads a generated batch back with the dtypes the quality suites
    expect (identifier/date/code columns as strings, amounts as floats)."""
    from app.data_engineering.dtype_conversion import load_column_categories
    from app.quality.data_loader import load_cleaned_batch

    spec_for(batch_id)  # validates the id
    csv_path = paths.batch_csv_path(batch_id)
    if not csv_path.exists():
        generate_all(force=False)

    categories = load_column_categories()
    df = load_cleaned_batch(csv_path, categories)
    df = df.set_index(ROW_KEY_COLUMN)

    truth = pd.read_csv(paths.ground_truth_path(batch_id), dtype=str).set_index(ROW_KEY_COLUMN)
    labels = truth[GROUND_TRUTH_COLUMN].reindex(df.index).fillna(NO_INJECTION)
    labels.name = GROUND_TRUTH_COLUMN
    return df, labels


if __name__ == "__main__":  # pragma: no cover -- reseed CLI
    for entry in generate_all(force=True):
        print(
            f"{entry.batch_id}: {entry.rows} rows, {entry.injected_rows} injected "
            f"{entry.injected_counts}, {entry.date_from}..{entry.date_to}"
        )
