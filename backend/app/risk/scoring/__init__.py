"""Severity, Business Impact, and Priority scoring (Phase 10, spec
010-severity-impact-priority-scoring).

Four distinct, non-overlapping signals (MVP_CONTEXT.md Section 3.3):
Quality (Phase 3), Anomaly (Phase 7), Risk (Phase 9), and this module's own
Severity + Business Impact, combined into a single Priority score. Every
function here is pure -- it takes already-resolved input values and never
reaches into Phase 3/4/7/8/9's stores itself (research.md) -- so Phase 12
(incident creation) and Phase 14 (post-remediation revalidation) can both
call the exact same functions with different input snapshots.
"""
