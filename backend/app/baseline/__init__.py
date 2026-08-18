"""Historical baseline computation (Phase 4).

Computes volume-per-window, amount-distribution, data-health, and
length-of-stay baselines from Phase 2's cleaned historical data (cross-
checked against Phase 3's quality results for missingness/duplicate
figures), and persists them as a versioned `BaselineSnapshot` with
source-data provenance. See specs/004-historical-baseline/ for the
feature spec, plan, and data model.
"""
