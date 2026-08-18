"""Classifies a computed rate into PASS/WARNING/CRITICAL per the exact
bands in MVP_CONTEXT.md Section 3.1.
"""

from app.quality.schemas import Band

MISSING_RATE_WARNING_PCT = 2.0
MISSING_RATE_CRITICAL_PCT = 5.0

DUPLICATE_RATE_WARNING_PCT = 0.0
DUPLICATE_RATE_CRITICAL_PCT = 1.0


def classify_missing_rate(pct: float) -> Band:
    """<2% PASS, 2-5% WARNING, >5% CRITICAL."""
    if pct > MISSING_RATE_CRITICAL_PCT:
        return Band.CRITICAL
    if pct >= MISSING_RATE_WARNING_PCT:
        return Band.WARNING
    return Band.PASS


def classify_duplicate_rate(pct: float) -> Band:
    """0% PASS, 0-1% WARNING, >1% CRITICAL."""
    if pct > DUPLICATE_RATE_CRITICAL_PCT:
        return Band.CRITICAL
    if pct > DUPLICATE_RATE_WARNING_PCT:
        return Band.WARNING
    return Band.PASS


UNEXPECTED_PCT_WARNING = 0.0
UNEXPECTED_PCT_CRITICAL = 1.0


def classify_unexpected_pct(
    pct: float, warning_gt: float = UNEXPECTED_PCT_WARNING, critical_gt: float = UNEXPECTED_PCT_CRITICAL
) -> Band:
    """Shared band logic for validity/range/code-set checks: any
    unexpected value is at least a WARNING, more than critical_gt% is
    CRITICAL."""
    if pct > critical_gt:
        return Band.CRITICAL
    if pct > warning_gt:
        return Band.WARNING
    return Band.PASS
