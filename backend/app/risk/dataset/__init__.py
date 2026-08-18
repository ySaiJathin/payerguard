"""Risk dataset construction (Phase 8, spec 008-risk-dataset-construction).

Assembles one window-grain `RiskDatasetRow` per Phase 4/5 window from
Phase 3 (GX failures), Phase 4 (historical quality baseline), Phase 5
(volume/amount deviation, claim count), and Phase 7 (`anomaly_count`)
persisted outputs -- never recomputing a value independently (spec
FR-002) -- and derives + documents the investigation-risk label per
MVP_CONTEXT.md Section 2.4. This dataset is Phase 9's sole training input.
"""
