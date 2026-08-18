"""Shared helper for reading GX validation result rates.

For a column with zero non-null values (e.g. the fully-null columns
identified in MVP_CONTEXT.md 2.2), GX returns `unexpected_percent_nonmissing`
as `None` rather than 0.0 -- there's nothing non-missing to be unexpected
about. Falling through to `unexpected_percent` (and finally 0.0) treats
"nothing to check" as vacuously passing this particular expectation; the
column's completeness check independently reports the missingness.
"""


def extract_unexpected_pct(result: dict) -> float:
    value = result.get("unexpected_percent_nonmissing")
    if value is None:
        value = result.get("unexpected_percent")
    if value is None:
        value = 0.0
    return float(value)
