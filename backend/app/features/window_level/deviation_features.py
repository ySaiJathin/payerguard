"""Window-level volume/amount deviation vs. Phase 4's BaselineSnapshot
(FR-007). A window-definition mismatch is detected and reported rather
than silently computing a deviation against an incompatible baseline
(spec edge case; constitution Principle VII).
"""

from app.baseline.schemas import BaselineSnapshot


class WindowDefinitionMismatchError(ValueError):
    """Raised when the configured window_definition doesn't match the
    BaselineSnapshot's volume_baseline.window_definition."""


def compute_deviation_features(
    window_aggregates: list[dict], baseline: BaselineSnapshot, window_definition: str
) -> dict[str, dict]:
    if window_definition != baseline.volume_baseline.window_definition:
        raise WindowDefinitionMismatchError(
            f"Configured window_definition {window_definition!r} does not match "
            f"BaselineSnapshot.volume_baseline.window_definition "
            f"{baseline.volume_baseline.window_definition!r}."
        )

    baseline_windows = {w.window_id: w for w in baseline.volume_baseline.windows}
    baseline_amounts = {a.column_name: a for a in baseline.amount_baselines}

    deviations: dict[str, dict] = {}
    for window in window_aggregates:
        window_id = window["window_id"]
        baseline_window = baseline_windows.get(window_id)
        baseline_claim_count = baseline_window.claim_count if baseline_window is not None else 0
        volume_deviation = window["claim_count"] - baseline_claim_count

        amount_deviation: dict[str, float] = {}
        for column, stats in window["amount_stats"].items():
            baseline_amount = baseline_amounts.get(column)
            if baseline_amount is None:
                continue
            amount_deviation[column] = stats["mean"] - baseline_amount.mean

        deviations[window_id] = {
            "volume_deviation": float(volume_deviation),
            "amount_deviation": amount_deviation,
        }
    return deviations
