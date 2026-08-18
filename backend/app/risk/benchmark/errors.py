"""Error types for the risk model benchmark (contracts/api.md's 409 response)."""


class RiskModelInputUnavailableError(RuntimeError):
    """Raised when Phase 6's `TemporalSplit` or Phase 8's `risk_dataset.csv`
    is not yet available."""


class InsufficientClassDiversityError(RiskModelInputUnavailableError):
    """Raised when the train-split rows contain only one
    `investigation_risk_label` class -- fitting a classifier against a
    single-class target is meaningless, so this fails fast rather than
    silently producing a degenerate always-predict-one-class model."""
