"""Risk model benchmark (Phase 9, spec 009-risk-model-benchmark).

Fits Logistic Regression, Random Forest, and XGBoost on Phase 8's risk
dataset, restricted to Phase 6's train-range rows, tuned on
validation-range rows only, and evaluated on test-range rows exactly
once -- never recomputing or reshuffling Phase 6's `TemporalSplit`
(constitution Principle VII). Selects the production model empirically,
prioritizing recall and PR-AUC over raw accuracy (constitution
Principle I; false negatives -- missed investigation-worthy incidents --
are the costly error).
"""
