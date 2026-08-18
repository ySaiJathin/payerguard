"""Empirical production-model selection (spec FR-005, FR-006, FR-007;
research.md).

A model whose test-split `pr_auc` is at or below the test label's own
positive base rate is excluded first: a random/no-skill classifier's
PR-AUC (average precision) equals the positive class prevalence exactly,
so this is a standard, non-arbitrary "meaningfully better than random"
gate -- not a hand-picked multiplier. Among the models that clear the
gate (or, if none do, among all three -- surfaced via the caller's
`data_scale_warning`), the survivor with the highest `recall` wins
(directly implementing MVP_CONTEXT.md's "false negatives are the costly
error"); a tie on `recall` (rounded to 3 decimal places) is broken by the
lower `calibration_brier_score` (better-calibrated model preferred), and
a further tie by the lower `false_negative_rate`. Never defaults to
XGBoost by assumption -- whichever model actually wins the real benchmark
run is selected (constitution Principle I).
"""

from datetime import datetime, timezone

from app.risk.benchmark.schemas import ProductionRiskModelSelection, RiskBenchmarkResult

RANKING_RULE = "PR-AUC floor gate (= test label base rate), then rank by recall, Brier score tie-break, FNR final tie-break"
RECALL_ROUND_DIGITS = 3


def _recall_key(result: RiskBenchmarkResult) -> tuple[float, float, float]:
    return (
        -round(result.recall, RECALL_ROUND_DIGITS),
        result.calibration_brier_score,
        result.false_negative_rate,
    )


def select_production_model(
    results: list[RiskBenchmarkResult], test_label_base_rate: float
) -> ProductionRiskModelSelection:
    if not results:
        raise ValueError("select_production_model requires at least one RiskBenchmarkResult")

    survivors = [r for r in results if r.pr_auc > test_label_base_rate]
    candidates = survivors if survivors else results

    ranked = sorted(candidates, key=_recall_key)
    best = ranked[0]

    best_recall_rounded = round(best.recall, RECALL_ROUND_DIGITS)
    tied_count = sum(1 for r in candidates if round(r.recall, RECALL_ROUND_DIGITS) == best_recall_rounded)
    tie_break_applied = tied_count > 1

    return ProductionRiskModelSelection(
        selected_model=best.model_type,
        ranking_rule=RANKING_RULE,
        pr_auc_floor_used=test_label_base_rate,
        tie_break_applied=tie_break_applied,
        benchmark_result_ids=[r.model_type.value for r in results],
        selected_at=datetime.now(timezone.utc),
    )
