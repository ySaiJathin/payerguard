"""Reusable synthetic claims generator (demo Task 1).

`generate_batch(spec)` returns a claim-grain DataFrame carrying **every**
column of the real cleaned extract, in the same order and with the same
dtypes, plus a parallel ground-truth frame recording which rows were
deliberately injected and with which injection type. Nothing is read from a
pre-baked fixture file -- the frame is synthesised from the statistical
column profile in `column_profile.py` each time, so the same spec always
reproduces the same batch (every draw goes through one seeded
`numpy.random.Generator`) while a different spec produces genuinely
different data.

The five injection types are exactly the taxonomy the dashboard already
displays (`app.anomaly.schemas.InjectionType`):

- missing_value_spike: nulls a random half of the row's populated fields
- amount_spike: multiplies the row's amount columns by a large factor
- duplicate_spike: appends an exact copy of the row (the copy is the anomaly)
- volume_drop: thins a contiguous date block; its survivors are the anomaly
- distribution_shift: shifts the row's numeric fields by several batch std devs

They are applied to disjoint row subsets, so a row carries at most one
label and per-type recall/precision are cleanly separable.
"""

from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.demo.column_profile import load_column_profile
from app.demo.schemas import BatchSpec, InjectionType
from app.quality.schemas import ColumnCategory

CLAIM_ID_COLUMN = "CLM_ID"
BENE_ID_COLUMN = "BENE_ID"
CLAIM_FROM_COLUMN = "CLM_FROM_DT"
CLAIM_THRU_COLUMN = "CLM_THRU_DT"
ADMISSION_COLUMN = "CLM_ADMSN_DT"
DISCHARGE_COLUMN = "NCH_BENE_DSCHRG_DT"
WEEKLY_PROC_COLUMN = "NCH_WKLY_PROC_DT"
PAYMENT_COLUMN = "CLM_PMT_AMT"
UTILIZATION_DAYS_COLUMN = "CLM_UTLZTN_DAY_CNT"

GROUND_TRUTH_COLUMN = "injection_type"
ROW_KEY_COLUMN = "row_key"
NO_INJECTION = "none"

AMOUNT_SPIKE_FACTOR_RANGE = (20.0, 80.0)
MISSING_SPIKE_COLUMN_FRACTION = 0.6
DISTRIBUTION_SHIFT_N_STD = 6.0
VOLUME_DROP_SURVIVOR_FRACTION = 0.3
# Beneficiaries recur across claims in the real extract; roughly two claims
# per beneficiary keeps that structure without making BENE_ID a second
# primary key.
CLAIMS_PER_BENEFICIARY = 2.0


def _columns_of(profile: dict, category: ColumnCategory) -> list[str]:
    return [c["name"] for c in profile["columns"] if c["category"] == category.value]


def _draw_pool(rng: np.random.Generator, pool: dict, n: int) -> np.ndarray:
    values = pool.get("values") or []
    if not values:
        return np.array([None] * n, dtype=object)
    weights = np.asarray(pool.get("weights") or [], dtype=float)
    if weights.size != len(values) or weights.sum() <= 0:
        weights = np.full(len(values), 1.0 / len(values))
    else:
        weights = weights / weights.sum()
    return rng.choice(np.asarray(values, dtype=object), size=n, p=weights)


def _draw_amounts(rng: np.random.Generator, fit: dict, n: int, scale: float, spread: float) -> np.ndarray:
    sigma = max(float(fit.get("log_sigma", 0.5)) * spread, 1e-6)
    mu = float(fit.get("log_mu", 0.0)) + float(np.log(max(scale, 1e-9)))
    values = rng.lognormal(mean=mu, sigma=sigma, size=n)
    zero_pct = float(fit.get("zero_pct", 0.0))
    if zero_pct > 0:
        values = np.where(rng.random(n) < zero_pct, 0.0, values)
    return np.round(values, 2)


def _apply_missingness(
    rng: np.random.Generator, values: np.ndarray, missing_pct: float, extra_pct: float
) -> np.ndarray:
    rate = min(100.0, missing_pct + extra_pct) / 100.0
    if rate <= 0:
        return values
    if rate >= 1.0:
        return np.array([None] * len(values), dtype=object)
    values = values.astype(object)
    values[rng.random(len(values)) < rate] = None
    return values


def _weekly_cutoff(series: pd.Series) -> pd.Series:
    """`NCH_WKLY_PROC_DT` is a weekly batch-cutoff Friday in the real
    extract, not an operational timestamp -- reproduce that structure so
    the generated column means the same thing the source column means."""
    parsed = pd.to_datetime(series, errors="coerce")
    offset = (4 - parsed.dt.weekday) % 7
    return (parsed + pd.to_timedelta(offset, unit="D") + pd.Timedelta(days=7)).dt.strftime("%Y-%m-%d")


def generate_base_frame(spec: BatchSpec, profile: dict | None = None) -> pd.DataFrame:
    """The clean, uninjected batch: schema-identical to the real cleaned
    extract, shaped by `spec`."""
    profile = profile or load_column_profile()
    rng = np.random.default_rng(spec.seed)
    n = spec.claim_count

    start = date.fromisoformat(spec.start_date)
    end = date.fromisoformat(spec.end_date)
    span_days = max((end - start).days, 1)

    offsets = np.sort(rng.integers(0, span_days + 1, size=n))
    from_dates = pd.to_datetime([start + timedelta(days=int(d)) for d in offsets])

    util_entry = next((c for c in profile["columns"] if c["name"] == UTILIZATION_DAYS_COLUMN), None)
    util_fit = (util_entry or {}).get("integer", {"min": 1, "max": 20, "mean": 5.0})
    lengths = np.clip(
        rng.poisson(max(float(util_fit.get("mean", 5.0)), 0.5), size=n),
        max(int(util_fit.get("min", 0)), 0),
        max(int(util_fit.get("max", 30)), 1),
    )
    thru_dates = from_dates + pd.to_timedelta(lengths, unit="D")

    bene_pool_size = max(int(n / CLAIMS_PER_BENEFICIARY), 1)
    bene_ids = np.array([f"SYNB{i:08d}" for i in rng.integers(0, bene_pool_size, size=n)], dtype=object)

    data: dict[str, np.ndarray] = {}
    for entry in profile["columns"]:
        name = entry["name"]
        category = entry["category"]
        missing_pct = float(entry.get("missing_pct", 0.0))

        if name == CLAIM_ID_COLUMN:
            data[name] = np.array([f"{spec.batch_id.upper()}-CLM-{i:07d}" for i in range(n)], dtype=object)
            continue
        if name == BENE_ID_COLUMN:
            data[name] = bene_ids
            continue
        if name in (CLAIM_FROM_COLUMN, ADMISSION_COLUMN):
            data[name] = np.array(from_dates.strftime("%Y-%m-%d"), dtype=object)
            continue
        if name in (CLAIM_THRU_COLUMN, DISCHARGE_COLUMN):
            data[name] = np.array(thru_dates.strftime("%Y-%m-%d"), dtype=object)
            continue
        if name == UTILIZATION_DAYS_COLUMN:
            data[name] = lengths.astype(float)
            continue

        if category == ColumnCategory.AMOUNT.value:
            fit = entry.get("amount", {})
            scale = spec.amount_scale if name == PAYMENT_COLUMN else 1.0 + (spec.amount_scale - 1.0) * 0.5
            spread = spec.amount_spread if name == PAYMENT_COLUMN else 1.0 + (spec.amount_spread - 1.0) * 0.5
            values = _draw_amounts(rng, fit, n, scale, spread).astype(object)
        elif category == ColumnCategory.UTILIZATION_DURATION.value:
            fit = entry.get("integer", {"min": 0, "max": 10, "mean": 1.0})
            low = int(fit.get("min", 0))
            high = max(int(fit.get("max", 1)), low) + 1
            values = rng.integers(low, high, size=n).astype(float).astype(object)
        elif category == ColumnCategory.DATE.value:
            bounds = entry.get("date", {})
            if bounds.get("min") and bounds.get("max"):
                jitter = rng.integers(-15, 16, size=n)
                values = np.array(
                    (from_dates + pd.to_timedelta(jitter, unit="D")).strftime("%Y-%m-%d"), dtype=object
                )
            else:
                values = np.array([None] * n, dtype=object)
        else:
            values = _draw_pool(rng, entry.get("pool", {}), n).astype(object)

        # Key columns keep their natural missingness only; every other
        # column also absorbs the spec's structural degradation.
        extra = spec.extra_missing_pct if missing_pct < 99.0 else 0.0
        data[name] = _apply_missingness(rng, values, missing_pct, extra)

    df = pd.DataFrame(data, columns=profile["column_order"])
    if WEEKLY_PROC_COLUMN in df.columns:
        df[WEEKLY_PROC_COLUMN] = _weekly_cutoff(df[CLAIM_FROM_COLUMN])

    df.index = pd.RangeIndex(len(df))
    return df


# --------------------------------------------------------------------------
# Injection
# --------------------------------------------------------------------------


def _take_block(rng: np.random.Generator, available: list, size: int) -> list:
    size = min(max(size, 1), len(available))
    start = int(rng.integers(0, max(len(available) - size, 1)))
    return available[start : start + size]


def _place(
    rng: np.random.Generator,
    available: list,
    total_rows: int,
    rates: dict,
    density: float,
    shared_block: bool,
) -> tuple[dict, list]:
    """Draws one contiguous block (or one per type) and samples targets from
    inside it. Returns the per-type picks and what is left available."""
    counts = {
        injection_type: int(round(max(rate, 0.0) * total_rows))
        for injection_type, rate in rates.items()
        if rate > 0
    }
    picks_by_type: dict = {}
    if not counts or not available:
        return picks_by_type, available

    density = min(max(density, 0.05), 1.0)

    if shared_block:
        block = _take_block(rng, available, int(sum(counts.values()) / density))
        pool = list(rng.permutation(np.asarray(block, dtype=object)))
        cursor = 0
        for injection_type, count in counts.items():
            chunk = pool[cursor : cursor + count]
            cursor += count
            if len(chunk):
                picks_by_type[injection_type] = list(chunk)
    else:
        for injection_type, count in counts.items():
            if not available:
                break
            block = _take_block(rng, available, int(count / density))
            picks = list(
                rng.choice(np.asarray(block, dtype=object), size=min(count, len(block)), replace=False)
            )
            picks_by_type[injection_type] = picks
            chosen = set(picks)
            available = [row for row in available if row not in chosen]

    taken = {row for picks in picks_by_type.values() for row in picks}
    return picks_by_type, [row for row in available if row not in taken]


def _plan_targets(rng: np.random.Generator, ordered_index: list, plan) -> dict:
    """Resolves an `InjectionPlan` into concrete, disjoint target row sets.

    Clusters are placed first (they are the incidents the demo is built
    around), then the background rates fill in around them.
    """
    available = list(ordered_index)
    total_rows = len(ordered_index)
    targets: dict = {}

    for cluster in getattr(plan, "clusters", []) or []:
        picks_by_type, available = _place(
            rng, available, total_rows, cluster.rates, cluster.density, shared_block=True
        )
        for injection_type, picks in picks_by_type.items():
            targets.setdefault(injection_type, []).extend(picks)

    picks_by_type, available = _place(
        rng,
        available,
        total_rows,
        getattr(plan, "rates", {}) or {},
        getattr(plan, "background_density", 0.7),
        shared_block=False,
    )
    for injection_type, picks in picks_by_type.items():
        targets.setdefault(injection_type, []).extend(picks)

    return targets


def inject(
    df: pd.DataFrame,
    labels: pd.Series,
    plan,
    profile: dict,
    seed: int,
) -> tuple[pd.DataFrame, pd.Series]:
    """Applies an `InjectionPlan` to `df`, returning the mutated frame and
    its updated ground-truth labels. Rows already carrying a label are never
    re-targeted, so a row has exactly one injection type.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()
    labels = labels.copy()

    amount_columns = [c for c in _columns_of(profile, ColumnCategory.AMOUNT) if c in df.columns]
    numeric_columns = amount_columns + [
        c for c in _columns_of(profile, ColumnCategory.UTILIZATION_DURATION) if c in df.columns
    ]
    nullable_columns = [
        c
        for c in df.columns
        if c not in (CLAIM_ID_COLUMN, BENE_ID_COLUMN, CLAIM_FROM_COLUMN, CLAIM_THRU_COLUMN)
    ]

    date_ordered = [
        row
        for row in df.sort_values(CLAIM_FROM_COLUMN, kind="stable").index
        if labels.loc[row] == NO_INJECTION
    ]
    targets = _plan_targets(rng, date_ordered, plan)

    # --- missing-value spike ---------------------------------------------
    rows = targets.get(InjectionType.missing_value_spike, [])
    if rows:
        for row in rows:
            # Target the fields this row actually has. Roughly a third of the
            # 197 columns are legitimately null in every row of the source
            # extract, so drawing uniformly across all of them would spend
            # most of the injection nulling cells that are already null --
            # a "missing-value spike" that barely raises the missing rate.
            populated = [c for c in nullable_columns if pd.notna(df.loc[row, c])]
            if not populated:
                continue
            n_cols = max(1, int(len(populated) * MISSING_SPIKE_COLUMN_FRACTION))
            columns = rng.choice(np.asarray(populated, dtype=object), size=n_cols, replace=False)
            df.loc[row, list(columns)] = np.nan
        labels.loc[rows] = InjectionType.missing_value_spike.value

    # --- amount spike ------------------------------------------------------
    rows = targets.get(InjectionType.amount_spike, [])
    if rows and amount_columns:
        factors = rng.uniform(AMOUNT_SPIKE_FACTOR_RANGE[0], AMOUNT_SPIKE_FACTOR_RANGE[1], size=len(rows))
        for row, factor in zip(rows, factors):
            current = pd.to_numeric(df.loc[row, amount_columns], errors="coerce").fillna(0.0)
            df.loc[row, amount_columns] = np.round(np.where(current > 0, current, 1000.0) * factor, 2)
        labels.loc[rows] = InjectionType.amount_spike.value

    # --- distribution shift -------------------------------------------------
    rows = targets.get(InjectionType.distribution_shift, [])
    if rows and numeric_columns:
        stds = {c: float(pd.to_numeric(df[c], errors="coerce").std() or 1.0) for c in numeric_columns}
        # The most populated numeric columns, not a random draw. Picking at
        # random regularly landed on columns that are null in most rows, so
        # whether the shift was observable at all came down to the seed.
        populated_rank = sorted(
            numeric_columns,
            key=lambda c: int(pd.to_numeric(df[c], errors="coerce").notna().sum()),
            reverse=True,
        )
        shift_columns = populated_rank[: min(4, len(populated_rank))]
        # Fixed downward, not a coin flip. A distribution shift that drives
        # amounts below zero models the sign/unit error this failure mode
        # actually represents, and it makes the shift observable through the
        # amount-validity expectation instead of leaving whether the batch
        # fails validation up to the seed.
        direction = -1.0
        for row in rows:
            for column in shift_columns:
                current = pd.to_numeric(pd.Series([df.loc[row, column]]), errors="coerce").iloc[0]
                base = 0.0 if pd.isna(current) else float(current)
                std = stds[column] if not pd.isna(stds[column]) else 1.0
                df.loc[row, column] = round(base + direction * DISTRIBUTION_SHIFT_N_STD * std, 2)
        labels.loc[rows] = InjectionType.distribution_shift.value

    # --- volume drop ---------------------------------------------------------
    # A genuinely window-level phenomenon: a contiguous date block loses most
    # of its claims. The survivors of that block are what a detector can
    # actually see, so they carry the label.
    rows = targets.get(InjectionType.volume_drop, [])
    if rows:
        block_size = int(len(rows) / VOLUME_DROP_SURVIVOR_FRACTION)
        ordered = list(df.sort_values(CLAIM_FROM_COLUMN, kind="stable").index)
        if block_size >= len(ordered):
            block_size = max(int(len(ordered) * 0.1), 1)
        start = int(rng.integers(0, max(len(ordered) - block_size, 1)))
        block = [r for r in ordered[start : start + block_size] if labels.loc[r] == NO_INJECTION]
        survivors = []
        if block:
            survivors = list(
                rng.choice(
                    np.asarray(block, dtype=object),
                    size=max(int(len(block) * VOLUME_DROP_SURVIVOR_FRACTION), 1),
                    replace=False,
                )
            )
        dropped = [r for r in block if r not in set(survivors)]
        if dropped:
            df = df.drop(index=dropped)
            labels = labels.drop(index=dropped)
        if survivors:
            labels.loc[survivors] = InjectionType.volume_drop.value

    # --- duplicate spike ------------------------------------------------------
    # Appended last so the copies are not themselves re-targeted. The copy is
    # the anomaly; the original stays normal.
    rows = [r for r in targets.get(InjectionType.duplicate_spike, []) if r in df.index]
    if rows:
        copies = df.loc[rows].copy()
        copies.index = [f"DUP-{r}" for r in rows]
        df = pd.concat([df, copies])
        labels = pd.concat(
            [labels, pd.Series(InjectionType.duplicate_spike.value, index=copies.index)]
        )

    return df, labels


def generate_batch(spec: BatchSpec, profile: dict | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Full batch: base frame, structural duplicates, then injections."""
    profile = profile or load_column_profile()
    rng = np.random.default_rng(spec.seed + 1)

    df = generate_base_frame(spec, profile)
    labels = pd.Series(NO_INJECTION, index=df.index, name=GROUND_TRUTH_COLUMN)

    # Structural (non-injected) duplicate rate -- part of the batch's own
    # quality profile, which the DuplicateRate expectation measures. These
    # copies are NOT labelled anomalies; only `duplicate_spike` is.
    duplicate_count = int(round(spec.duplicate_rate * len(df)))
    if duplicate_count > 0:
        picks = rng.choice(np.asarray(df.index), size=duplicate_count, replace=False)
        copies = df.loc[list(picks)].copy()
        copies.index = [f"BGDUP-{p}" for p in picks]
        df = pd.concat([df, copies])
        labels = pd.concat([labels, pd.Series(NO_INJECTION, index=copies.index)])

    if spec.injection_plan.total_rate() > 0:
        df, labels = inject(df, labels, spec.injection_plan, profile, spec.seed + 2)

    df = df.sort_values(CLAIM_FROM_COLUMN, kind="stable")
    labels = labels.loc[df.index]

    row_keys = [f"{spec.batch_id}-R{i:06d}" for i in range(len(df))]
    df.index = pd.Index(row_keys, name=ROW_KEY_COLUMN)
    labels.index = df.index
    labels.name = GROUND_TRUTH_COLUMN
    return df, labels


def ground_truth_frame(df: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            ROW_KEY_COLUMN: list(df.index),
            CLAIM_ID_COLUMN: df[CLAIM_ID_COLUMN].astype(str).tolist(),
            GROUND_TRUTH_COLUMN: labels.tolist(),
        }
    )


def generated_at() -> datetime:
    return datetime.now(timezone.utc)
