"""Three-stage feature selection (Phase 6).

Establishes the shared temporal train/validation/test split (reused by
Phases 7 and 9), then narrows Phase 5's engineered features via structural
(Stage 1), statistical (Stage 2), and model-based (Stage 3) filtering,
fit exclusively on train+validation data. See specs/006-feature-selection/
for the feature spec, plan, and data model.
"""
