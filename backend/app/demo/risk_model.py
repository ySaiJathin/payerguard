"""XGBoost risk scoring over ten distinct signal types (demo Tasks 2c & 5).

## What the model consumes

Risk is never a single blended number here. Each ingestion window is
measured on ten separate 0-100 sub-scores, computed from the window's own
rows -- these are the model's feature vector, in this exact order. The
first four and the anomaly signal are expressed as the window's *excess
over the batch's own baseline* for that measure (see `compute_sub_scores`
for why); the rest have a genuine zero baseline and so are absolute.

| feature               | measured from                                                    |
|-----------------------|------------------------------------------------------------------|
| `missing_data_risk`   | excess null-cell rate over the batch baseline                     |
| `null_risk`           | excess null rate in the business-critical columns                 |
| `duplicate_risk`      | share of exact duplicate rows in the window                       |
| `sla_timeliness_risk` | lag from claim-through date to the weekly processing cutoff,      |
|                       | relative to the batch's own median lag                            |
| `range_risk`          | share of rows with a numeric value outside the batch p1-p99 band  |
| `dtype_risk`          | share of date cells that fail the ISO-8601 format expectation     |
| `validity_risk`       | share of rows carrying a negative amount (amount >= 0 expectation)|
| `uniqueness_risk`     | share of repeated CLM_ID values beyond claim-grain expectation    |
| `freshness_risk`      | staleness of the window relative to the batch's latest claim date |
| `anomaly_risk`        | share of the window's claims flagged by the Isolation Forest      |

`sla_timeliness_risk` is a *timeliness* signal derived from
`NCH_WKLY_PROC_DT`, which is a weekly batch cutoff rather than an
operational adjudication timestamp. It is labelled as such and never
presented as a contractual SLA breach -- the dataset has no such field.

## How the training labels were derived

There is no ground-truth "true risk" for a window, so the labels are
rule-derived and documented rather than pretended to be observed:

    base        = sum(weight_i * sub_score_i)      # weights below, sum to 1
    interaction = 12 * (anomaly_risk/100) * (missing_data_risk/100)
    label       = clip(base + interaction, 0, 100)

The interaction term is what makes this more than a weighted average: a
window that is both anomalous *and* structurally incomplete is worse than
either alone, and a linear blend cannot express that. The model is fitted
on the real windows of every generated batch plus a Latin-style random
sweep of the feature space, so it learns the surface rather than
memorising a handful of points -- and at inference time the score on the
dashboard is a genuine `XGBRegressor.predict` call, not the formula.

## Severity bands

The 0-100 output maps to the same bands the UI's `bandForScore` applies,
so every surface (KPI tiles, incident table, incident detail, severity
distribution) agrees:

    score > 80  -> CRITICAL
    score > 60  -> HIGH
    score > 30  -> MEDIUM
    score <= 30 -> LOW
"""

import pickle
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.demo.generator import CLAIM_FROM_COLUMN
from app.demo.paths import risk_model_path
from app.demo.schemas import SubScores

FEATURE_ORDER = [
    "missing_data_risk",
    "null_risk",
    "duplicate_risk",
    "sla_timeliness_risk",
    "range_risk",
    "dtype_risk",
    "validity_risk",
    "uniqueness_risk",
    "freshness_risk",
    "anomaly_risk",
]

LABEL_WEIGHTS = {
    "missing_data_risk": 0.16,
    "null_risk": 0.10,
    "duplicate_risk": 0.12,
    "sla_timeliness_risk": 0.10,
    "range_risk": 0.08,
    "dtype_risk": 0.06,
    "validity_risk": 0.10,
    "uniqueness_risk": 0.08,
    "freshness_risk": 0.05,
    "anomaly_risk": 0.15,
}
INTERACTION_GAIN = 12.0

CRITICAL_COLUMNS = [
    "CLM_ID",
    "CLM_FROM_DT",
    "CLM_THRU_DT",
    "CLM_PMT_AMT",
    "CLM_TOT_CHRG_AMT",
    "PRVDR_NUM",
    "PRNCPAL_DGNS_CD",
    "CLM_DRG_CD",
]
ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
WINDOW_DAYS = 7
SEVERITY_BANDS = ((80.0, "CRITICAL"), (60.0, "HIGH"), (30.0, "MEDIUM"))

TRAINING_SWEEP_ROWS = 12000
TRAINING_SEED = 20260819


def severity_band(score: float) -> str:
    for threshold, band in SEVERITY_BANDS:
        if score > threshold:
            return band
    return "LOW"


def _pct(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) * 100.0 if denominator else 0.0


def _scaled(value: float, full_scale: float) -> float:
    """Maps a raw rate onto 0-100, saturating at `full_scale` -- the point
    at which the signal is considered maximally bad."""
    return float(min(100.0, max(0.0, value / full_scale * 100.0)))


def assign_windows(df: pd.DataFrame, window_days: int = WINDOW_DAYS) -> pd.Series:
    """Fixed-length calendar windows anchored on the batch's first claim
    date, so a window id means the same thing across every batch."""
    dates = pd.to_datetime(df[CLAIM_FROM_COLUMN], errors="coerce")
    origin = dates.min()
    offset = ((dates - origin).dt.days // window_days).fillna(0).astype(int)
    starts = origin + pd.to_timedelta(offset * window_days, unit="D")
    return pd.Series(starts.dt.strftime("%Y-%m-%d"), index=df.index, name="window_start")


def _raw_measures(df: pd.DataFrame, flags: pd.Series, context: dict) -> dict[str, float]:
    """The seven data-quality measures, taken over whatever rows are passed
    -- one window, or the whole batch when establishing its baseline."""
    rows = len(df)
    total_cells = rows * df.shape[1]

    critical = [c for c in CRITICAL_COLUMNS if c in df.columns]

    out_of_range = pd.Series(False, index=df.index)
    for column in context["numeric_columns"]:
        low, high = context["envelope"][column]
        values = pd.to_numeric(df[column], errors="coerce")
        out_of_range |= (values < low) | (values > high)

    bad_format = 0
    date_cells = 0
    for column in context["date_columns"]:
        values = df[column].dropna().astype(str)
        date_cells += len(values)
        bad_format += int((~values.str.match(ISO_DATE_PATTERN)).sum())

    negative = pd.Series(False, index=df.index)
    for column in context["amount_columns"]:
        negative |= pd.to_numeric(df[column], errors="coerce") < 0

    claim_ids = df["CLM_ID"].astype(str)
    return {
        "missing": _pct(int(df.isna().sum().sum()), total_cells),
        "null": _pct(int(df[critical].isna().sum().sum()), rows * len(critical)) if critical else 0.0,
        "duplicate": _pct(int(df.duplicated(keep="first").sum()), rows),
        "range": _pct(int(out_of_range.sum()), rows),
        "dtype": _pct(bad_format, date_cells),
        "validity": _pct(int(negative.sum()), rows),
        "uniqueness": _pct(rows - claim_ids.nunique(), rows),
        "anomaly": _pct(int(flags.reindex(df.index).fillna(False).sum()), rows),
    }


def compute_sub_scores(
    window_df: pd.DataFrame,
    flags: pd.Series,
    batch_context: dict,
) -> SubScores:
    """Every sub-score is a real measurement over the window's own rows,
    expressed as the window's **excess over the batch's own baseline** for
    that measure.

    The excess, not the absolute level, is what makes a window risky. This
    extract is structurally sparse -- dozens of columns are legitimately
    100% null across every batch -- so an absolute missing-cell rate would
    saturate every window at 100 and carry no information. What an operator
    needs to know is that *this* window is worse than the batch it arrived
    in, which is exactly the deviation-from-baseline framing the rest of
    the pipeline already uses. Measures whose healthy baseline is genuinely
    zero (duplicates, out-of-range, bad dtype, negative amounts, repeated
    claim ids) behave identically either way.
    """
    raw = _raw_measures(window_df, flags, batch_context)
    base = batch_context["batch_measures"]

    def excess(key: str) -> float:
        return max(raw[key] - base[key], 0.0)

    lag_days = batch_context["processing_lag"].reindex(window_df.index).dropna()
    excess_lag = float(lag_days.mean() - batch_context["median_lag"]) if len(lag_days) else 0.0

    window_end = pd.to_datetime(window_df[CLAIM_FROM_COLUMN], errors="coerce").max()
    staleness_days = float((batch_context["batch_end"] - window_end).days) if pd.notna(window_end) else 0.0

    return SubScores(
        missing_data_risk=_scaled(excess("missing"), 6.0),
        null_risk=_scaled(excess("null"), 8.0),
        duplicate_risk=_scaled(raw["duplicate"], 8.0),
        sla_timeliness_risk=_scaled(max(excess_lag, 0.0), 4.0),
        range_risk=_scaled(raw["range"], 10.0),
        dtype_risk=_scaled(raw["dtype"], 5.0),
        validity_risk=_scaled(raw["validity"], 5.0),
        uniqueness_risk=_scaled(raw["uniqueness"], 10.0),
        freshness_risk=_scaled(staleness_days, float(batch_context["batch_span_days"] or 1)),
        anomaly_risk=_scaled(raw["anomaly"], 20.0),
    )


def build_batch_context(df: pd.DataFrame, categories: dict, flags: pd.Series | None = None) -> dict:
    from app.quality.schemas import ColumnCategory

    amount_columns = [
        c for c, cat in categories.items() if cat == ColumnCategory.AMOUNT and c in df.columns
    ]
    utilization_columns = [
        c
        for c, cat in categories.items()
        if cat == ColumnCategory.UTILIZATION_DURATION and c in df.columns
    ]
    date_columns = [c for c, cat in categories.items() if cat == ColumnCategory.DATE and c in df.columns]

    numeric_columns = [
        c
        for c in (amount_columns + utilization_columns)
        if pd.to_numeric(df[c], errors="coerce").notna().sum() > 0
    ][:12]
    envelope = {}
    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        envelope[column] = (float(values.quantile(0.01)), float(values.quantile(0.99)))

    thru = pd.to_datetime(df.get("CLM_THRU_DT"), errors="coerce")
    proc = pd.to_datetime(df.get("NCH_WKLY_PROC_DT"), errors="coerce")
    processing_lag = (proc - thru).dt.days.astype(float)

    claim_dates = pd.to_datetime(df[CLAIM_FROM_COLUMN], errors="coerce")
    context = {
        "amount_columns": amount_columns,
        "date_columns": date_columns,
        "numeric_columns": numeric_columns,
        "envelope": envelope,
        "processing_lag": processing_lag,
        "median_lag": float(processing_lag.median()) if processing_lag.notna().any() else 0.0,
        "batch_end": claim_dates.max(),
        "batch_span_days": int((claim_dates.max() - claim_dates.min()).days) or 1,
    }
    if flags is None:
        flags = pd.Series(False, index=df.index)
    context["batch_measures"] = _raw_measures(df, flags, context)
    return context


# --------------------------------------------------------------------------
# The model itself
# --------------------------------------------------------------------------


def rule_label(features: np.ndarray) -> np.ndarray:
    """The documented training-label formula (see module docstring)."""
    weights = np.array([LABEL_WEIGHTS[name] for name in FEATURE_ORDER])
    base = features @ weights
    anomaly = features[:, FEATURE_ORDER.index("anomaly_risk")] / 100.0
    missing = features[:, FEATURE_ORDER.index("missing_data_risk")] / 100.0
    return np.clip(base + INTERACTION_GAIN * anomaly * missing, 0.0, 100.0)


def _training_frame(observed: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """The sweep is a deliberate two-part mixture.

    Sixty percent is drawn from a low-skewed Beta, because most real
    windows are quiet and a purely uniform sweep would fit the model to a
    population that does not occur. But a low-skewed sweep alone never
    produces the corner where *many* signals are simultaneously maxed --
    with ten independent draws that combination has effectively zero
    probability -- so the model extrapolates badly exactly where it matters
    most: a genuine five-alarm window came back scored 62 when the
    documented formula puts it at 81. A uniform quarter covers the middle
    of the space and a high-skewed Beta covers the severe corner, which
    brings the fitted surface back onto the formula at both ends.
    """
    rng = np.random.default_rng(TRAINING_SEED)
    quiet_rows = int(TRAINING_SWEEP_ROWS * 0.60)
    uniform_rows = int(TRAINING_SWEEP_ROWS * 0.25)
    severe_rows = TRAINING_SWEEP_ROWS - quiet_rows - uniform_rows
    quiet = rng.beta(1.4, 3.0, size=(quiet_rows, len(FEATURE_ORDER))) * 100.0
    uniform = rng.uniform(0.0, 100.0, size=(uniform_rows, len(FEATURE_ORDER)))
    severe = rng.beta(3.0, 1.4, size=(severe_rows, len(FEATURE_ORDER))) * 100.0
    sweep = np.vstack([quiet, uniform, severe])
    features = sweep if observed is None or len(observed) == 0 else np.vstack([sweep, observed])
    return features, rule_label(features)


def train_risk_model(observed: np.ndarray | None = None):
    from xgboost import XGBRegressor

    X, y = _training_frame(observed)
    model = XGBRegressor(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.10,
        subsample=0.9,
        objective="reg:squarederror",
        random_state=TRAINING_SEED,
    )
    model.fit(pd.DataFrame(X, columns=FEATURE_ORDER), y)

    with risk_model_path().open("wb") as handle:
        pickle.dump(
            {
                "model": model,
                "feature_columns": FEATURE_ORDER,
                "label_weights": LABEL_WEIGHTS,
                "interaction_gain": INTERACTION_GAIN,
                "training_rows": int(len(X)),
            },
            handle,
        )
    return model


def load_risk_model(retrain: bool = False):
    path = risk_model_path()
    if retrain or not path.exists():
        return train_risk_model()
    with path.open("rb") as handle:
        return pickle.load(handle)["model"]


def predict_risk(sub_scores_list: list[SubScores], model=None) -> list[float]:
    """Real inference: the dashboard's 0-100 risk score is this call's
    output, clipped to the reportable range."""
    if not sub_scores_list:
        return []
    model = model or load_risk_model()
    frame = pd.DataFrame(
        [[getattr(s, name) for name in FEATURE_ORDER] for s in sub_scores_list],
        columns=FEATURE_ORDER,
    )
    predictions = np.clip(model.predict(frame), 0.0, 100.0)
    return [round(float(p), 2) for p in predictions]


def window_bounds(window_start: str, window_days: int = WINDOW_DAYS) -> tuple[str, str]:
    start = date.fromisoformat(window_start)
    return start.isoformat(), (start + timedelta(days=window_days - 1)).isoformat()
