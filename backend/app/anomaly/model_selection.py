"""Empirical production-model selection (spec FR-007, FR-008).

Ranks the four `BenchmarkResult` entries primarily by F1 score, with false
positive rate as the first tie-breaker and execution time as the second
(research.md's documented, defensible ranking rule) -- never defaults to
HBOS by assumption; whichever model actually wins the real benchmark run is
selected, even if that contradicts the expectation that HBOS wins
(constitution Principle I).
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.anomaly.schemas import BenchmarkResult, ProductionModelSelection

RANKING_RULE = "F1 primary, FPR tie-break, execution_time second tie-break"


def _rank_key(result: BenchmarkResult) -> tuple[float, float, float]:
    # Higher F1 is better, lower FPR is better, lower execution_time is
    # better -- negate F1 so a single ascending sort puts the best result
    # first for all three criteria.
    return (-result.f1, result.fpr, result.execution_time_s)


def select_production_model(results: list[BenchmarkResult]) -> ProductionModelSelection:
    if not results:
        raise ValueError("select_production_model requires at least one BenchmarkResult")

    ranked = sorted(results, key=_rank_key)
    best = ranked[0]

    best_f1_count = sum(1 for r in results if r.f1 == best.f1)
    tie_break_applied = best_f1_count > 1

    return ProductionModelSelection(
        selected_model=best.model_type,
        ranking_rule=RANKING_RULE,
        tie_break_applied=tie_break_applied,
        benchmark_result_ids=[r.model_type.value for r in results],
        selected_at=datetime.now(timezone.utc),
    )
