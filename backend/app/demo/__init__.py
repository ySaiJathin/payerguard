"""Demo-scoped synthetic data, simulator and end-to-end pipeline.

This package exists to make the PayerGuard dashboard demonstrable without a
real claims feed. Everything in it is *real computation on synthetic data*:
the batches are generated (not hand-written fixtures), Great Expectations
really validates them, scikit-learn's IsolationForest is really fitted and
scored, and XGBoost really predicts the 0-100 risk score. Nothing here
hardcodes a dashboard number.
"""
