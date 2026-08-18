"""Reports the investigation-risk label's class balance across an assembled
dataset (spec FR-009) so downstream consumers (Phase 9) are aware of any
class imbalance before choosing evaluation metrics.
"""

from app.risk.dataset.schemas import LabelDistributionReport


def compute_label_distribution(rows: list[dict]) -> LabelDistributionReport:
    total = len(rows)
    worthy = sum(1 for r in rows if r["investigation_risk_label"] == 1)
    not_worthy = total - worthy
    zero_claim = sum(1 for r in rows if r["claim_count"] == 0)

    return LabelDistributionReport(
        total_rows=total,
        investigation_worthy_count=worthy,
        investigation_worthy_pct=(worthy / total * 100) if total else 0.0,
        not_investigation_worthy_count=not_worthy,
        not_investigation_worthy_pct=(not_worthy / total * 100) if total else 0.0,
        zero_claim_window_count=zero_claim,
    )
