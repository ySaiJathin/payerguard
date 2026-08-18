"""Assembles one pre-label `RiskDatasetRow` per Phase 4/5 window from
Phase 3/4/5/7's persisted outputs -- joining on `window_id`, never
recomputing a statistic independently (spec FR-001, FR-002).

Two fields have no direct per-window upstream source and are documented
judgment calls (constitution Principle II):

- `gx_failure_count`: Phase 3's `ExpectationCheckResult`s are batch-level
  (one validation run over the whole cleaned historical file), not
  partitioned by window -- there is no per-window GX result to read. The
  real, persisted batch-total CRITICAL (+ configurable WARNING) count is
  therefore carried unchanged onto every window row, rather than
  fabricating a per-window split of a number that was never computed at
  that grain.
- `historical_quality_failure_rate`: Phase 4's `DataHealthBaseline` is
  likewise a single historical snapshot, not per-window. It is summarized
  here as the mean of its own real `historical_missing_rate_by_column`
  values combined with its real `historical_duplicate_rate` (both already
  0-100 pct scale) -- an arithmetic combination of upstream numbers, not
  an independently invented one -- and is, like `gx_failure_count`,
  constant across every row in a given run.

`affected_claim_pct` combines Phase 5's own real per-window row-level
quality proxies (`duplicate_pct`, `invalid_status_pct` -- deliberately
excluding `missing_pct`, which is a per-*cell* rate, not a per-claim one,
so mixing it in would conflate grains) with Phase 7-derived
`anomaly_frequency`, via a standard union-of-independent-rates
approximation. This is the closest honest estimate of "claims flagged by
at least one quality or anomaly signal" available without per-claim GX
flags, which Phase 3 does not persist.
"""

from pathlib import Path

from app.baseline.schemas import BaselineSnapshot
from app.baseline.snapshot_log import read_latest_baseline_snapshot
from app.data_engineering.paths import reports_dir as default_reports_dir
from app.features.features_log import read_window_features
from app.features.schemas import WindowFeatures
from app.quality.quality_results_log import read_quality_results
from app.quality.schemas import Band
from app.risk.dataset.errors import AnomalyEnrichmentIncompleteError, RiskDatasetInputUnavailableError


def _gx_failure_count(reports_out_dir: Path | None, include_warning: bool) -> int:
    result = read_quality_results(reports_out_dir)
    if result is None:
        raise RiskDatasetInputUnavailableError(
            "No Phase 3 quality results found -- run POST /quality/validate first."
        )
    _, check_results = result
    bands = {Band.CRITICAL, Band.WARNING} if include_warning else {Band.CRITICAL}
    return sum(1 for c in check_results if c.band in bands)


def _historical_quality_failure_rate(baseline: BaselineSnapshot) -> float:
    health = baseline.data_health_baseline
    rates = list(health.historical_missing_rate_by_column.values()) + [health.historical_duplicate_rate]
    return sum(rates) / len(rates) if rates else 0.0


def _amount_deviation_scalar(amount_deviation: dict[str, float]) -> float:
    if not amount_deviation:
        return 0.0
    return max(abs(v) for v in amount_deviation.values())


def _quality_issue_rate(window: WindowFeatures) -> float:
    duplicate = window.duplicate_pct / 100
    invalid_status = window.invalid_status_pct / 100
    return 1 - (1 - duplicate) * (1 - invalid_status)


def assemble_rows(
    include_warning_in_gx_failure_count: bool = True,
    reports_out_dir: Path | None = None,
    features_out_dir: Path | None = None,
) -> list[dict]:
    """Returns pre-label row dicts (every `RiskDatasetRow` field except
    `investigation_risk_indicator`/`investigation_risk_label`, which
    `label_formula.py` fills in) sorted by `window_start` ascending
    (spec FR-007, US3).

    Raises `AnomalyEnrichmentIncompleteError` if any window's
    `anomaly_count` is still `None` (spec FR-008), and
    `RiskDatasetInputUnavailableError` if Phase 3/4/5 outputs are missing.
    """
    reports_out_dir = reports_out_dir or default_reports_dir()

    windows = read_window_features(features_out_dir)
    if not windows:
        raise RiskDatasetInputUnavailableError(
            "No Phase 5 window features found -- run POST /features/compute first."
        )

    unenriched = [w.window_id for w in windows if w.anomaly_count is None]
    if unenriched:
        preview = ", ".join(unenriched[:5])
        suffix = f", ... ({len(unenriched)} total)" if len(unenriched) > 5 else ""
        raise AnomalyEnrichmentIncompleteError(
            "Phase 7's anomaly_count enrichment has not been completed for window(s) "
            f"[{preview}{suffix}] -- run POST /anomaly/enrich-windows first."
        )

    baseline = read_latest_baseline_snapshot(reports_out_dir)
    if baseline is None:
        raise RiskDatasetInputUnavailableError(
            "No Phase 4 baseline snapshot found -- run POST /baseline/compute first."
        )

    gx_failure_count = _gx_failure_count(reports_out_dir, include_warning_in_gx_failure_count)
    historical_quality_failure_rate = _historical_quality_failure_rate(baseline)

    rows: list[dict] = []
    for window in windows:
        claim_count = window.claim_count
        anomaly_count = window.anomaly_count or 0
        anomaly_frequency = (anomaly_count / claim_count) if claim_count else 0.0
        anomaly_score = anomaly_frequency * 100

        if claim_count:
            quality_issue_rate = _quality_issue_rate(window)
            affected_claim_pct = 100 * (1 - (1 - quality_issue_rate) * (1 - anomaly_frequency))
        else:
            affected_claim_pct = 0.0

        rows.append(
            {
                "window_id": window.window_id,
                "window_start": window.start,
                "window_end": window.end,
                "claim_count": claim_count,
                "gx_failure_count": gx_failure_count,
                "anomaly_score": anomaly_score,
                "anomaly_frequency": anomaly_frequency,
                "affected_claim_pct": affected_claim_pct,
                "volume_deviation": window.volume_deviation,
                "amount_deviation": _amount_deviation_scalar(window.amount_deviation),
                "historical_quality_failure_rate": historical_quality_failure_rate,
            }
        )

    rows.sort(key=lambda r: r["window_start"])
    return rows
