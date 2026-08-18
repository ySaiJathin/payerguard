"""Error types for risk dataset construction (contracts/api.md's 409 response)."""


class RiskDatasetInputUnavailableError(RuntimeError):
    """Raised when Phase 3/4/5's persisted outputs (quality results, baseline
    snapshot, window features) are not yet available."""


class AnomalyEnrichmentIncompleteError(RiskDatasetInputUnavailableError):
    """Raised when Phase 7's `POST /anomaly/enrich-windows` has not been run
    yet -- i.e. at least one `WindowFeatures.anomaly_count` is still `None`
    (spec FR-008). Assembling a row in this state would require fabricating
    or silently zeroing the anomaly signal, which spec FR-008 forbids."""
