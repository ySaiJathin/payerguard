"""Shared dollar-amount-vs-baseline scaling curve, reused by both
`severity.materiality_score` and `business_impact.compute_business_impact`
(spec FR-003, FR-005) so "how does this dollar figure compare to Phase 4's
baseline" is answered by one documented curve, not two independently
invented ones.

Maps `value` onto 0-100 by piecewise-linear interpolation through Phase
4's baseline percentile breakpoints (p25→20, p50→40, p75→60, p95→80,
p99→95), saturating toward 100 for anything beyond p99 -- a value at or
below 0 scores 0, and the curve is monotonically increasing throughout.
"""

from app.baseline.schemas import Percentiles

_BREAKPOINTS: list[tuple[str, float]] = [
    ("p25", 20.0),
    ("p50", 40.0),
    ("p75", 60.0),
    ("p95", 80.0),
    ("p99", 95.0),
]


def percentile_bucket_score(value: float, percentiles: Percentiles) -> float:
    if value <= 0:
        return 0.0

    points: list[tuple[float, float]] = [(0.0, 0.0)]
    for attr, score in _BREAKPOINTS:
        points.append((getattr(percentiles, attr), score))

    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return y1
            frac = (value - x0) / (x1 - x0)
            return y0 + frac * (y1 - y0)

    # Beyond p99: saturate toward 100, approaching it asymptotically so a
    # single extreme outlier doesn't blow past the [0, 100] scale.
    p99 = percentiles.p99
    if p99 <= 0:
        return 100.0
    excess_ratio = min(1.0, (value - p99) / p99)
    return 95.0 + excess_ratio * 5.0
