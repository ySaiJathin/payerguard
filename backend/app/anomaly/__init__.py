"""Anomaly detection benchmark and production model (Phase 7).

Benchmarks IQR/HBOS/Isolation Forest/LOF against Phase 6's shared
train/validation/test split, using a synthetic anomaly-injection harness
applied only to validation/test copies, empirically selects a production
model, and populates Phase 5's deferred `WindowFeatures.anomaly_count`.
See specs/007-anomaly-detection-benchmark/ for the feature spec, plan, and
data model.
"""
