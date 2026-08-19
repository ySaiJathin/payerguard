# Phase 15 Test Coverage Map

**Feature**: [specs/015-testing-suite](../../specs/015-testing-suite/spec.md) (FR-001, SC-001)

This is the authoritative record mapping every test scenario named in
[MVP_CONTEXT.md](../../MVP_CONTEXT.md) Section 5 / Phase 15 to either an
existing Phase 1-14 success criterion (by citation) or a new test added by
this feature. `backend/tests/coverage_map/test_coverage_map_completeness.py`
parses this file and asserts every named scenario appears exactly once with
a non-empty `Reference` — so this table cannot silently drift out of date.

**Status values** (per [data-model.md](../../specs/015-testing-suite/data-model.md)):

- `covered_by_prior_phase` — already genuinely tested by an earlier phase; this feature adds nothing (FR-009, no duplication).
- `new_test_added` — a real coverage gap this feature closes with a new test.
- `limitation_documented` — cannot be meaningfully tested today; the `Reference` explains why, honestly, rather than skipping silently (FR-008).

## Coverage Table

| Category | Scenario | Status | Reference |
|---|---|---|---|
| Data | missing values | covered_by_prior_phase | Phase 2 SC-005 — `backend/tests/data_engineering/test_cleaning_service.py::test_missing_value_gets_exactly_one_record_per_missing_cell` (every missing cell stays null and gets exactly one audit record); also re-run via `backend/tests/data_suite/test_data_category_suite.py` |
| Data | duplicates | covered_by_prior_phase | Phase 1 SC-003 — `backend/tests/data_engineering/test_duplicate_detection.py::test_exact_duplicate_excluded_and_flagged` and `test_real_file_has_zero_duplicates`; plus `test_profiling_service.py::test_full_duplicate_row_is_detected`; also re-run via `backend/tests/data_suite/test_data_category_suite.py` |
| Data | invalid types/values/dates | covered_by_prior_phase | Phase 2 SC-001/SC-006 — `backend/tests/data_engineering/test_invalid_value_detection.py` (negative amounts, out-of-range dates, unrecognized codes, all flagged not corrected) and `test_date_standardization.py` (ISO reformatting, unparseable dates flagged not guessed); Phase 3 validity expectations in `backend/tests/quality/test_suite_builder.py::test_negative_amount_trips_critical_validity_check`; also re-run via `backend/tests/data_suite/test_data_category_suite.py` |
| Data | missing columns | covered_by_prior_phase | Phase 1 SC-002 — `backend/tests/data_engineering/test_profiling_service.py::test_wrong_column_count_fails_fast` and `test_missing_column_reported_as_100_percent_missing`; Phase 2 schema gate in `test_cleaning_service.py::test_schema_mismatch_raises_schema_validation_error`; also re-run via `backend/tests/data_suite/test_data_category_suite.py` |
| Data | empty files | new_test_added | `backend/tests/data_engineering/test_empty_file_handling.py` — a genuine gap found while building this map: Phase 1 covered a *missing* file (`test_missing_source_file_fails_fast`) and Phase 3 covered empty *check results*, but no test covered an empty or header-only *source file*. Also re-run via `backend/tests/data_suite/test_data_category_suite.py` |
| Anomaly | injected-anomaly detection accuracy | covered_by_prior_phase | Phase 7 SC-002/SC-003 — `backend/tests/anomaly/test_injection_harness.py::test_all_five_injection_types_produce_at_least_one_instance` and `backend/tests/anomaly/test_benchmark_metrics.py::test_rerunning_the_same_benchmark_reproduces_identical_metrics` |
| Anomaly | false positives | covered_by_prior_phase | Phase 7 SC-003 — `BenchmarkResult.false_positive_rate` computed from the real confusion matrix in `app/anomaly/benchmark.py::_metrics_from_confusion`, asserted reproducible by `backend/tests/anomaly/test_benchmark_metrics.py` |
| Anomaly | false negatives | covered_by_prior_phase | Phase 7 SC-003 — recall/confusion-matrix component of the same `_metrics_from_confusion` path, asserted reproducible by `backend/tests/anomaly/test_benchmark_metrics.py`; selection correctness in `test_model_selection.py` |
| Anomaly | detection latency | covered_by_prior_phase | Phase 7 SC-003 — `MeasurementContext` + per-model execution timing recorded on every `BenchmarkResult` (`app/anomaly/benchmark.py`), asserted present by `backend/tests/anomaly/test_benchmark_metrics.py::test_every_result_has_all_five_injection_type_keys_and_measurement_context` |
| Anomaly | model stability | new_test_added | `backend/tests/anomaly/test_model_stability.py` — repeated independent fit/score cycles on unchanged data, asserting score variance stays within a documented tolerance (FR-002) |
| Risk | data-leakage test | covered_by_prior_phase | Phase 9 SC-001 — `backend/tests/risk/benchmark/test_leakage_isolation.py::test_corrupting_test_split_portion_does_not_change_fitted_hyperparameters` |
| Risk | temporal-split-correctness test | covered_by_prior_phase | Phase 9 SC-006 — `backend/tests/risk/benchmark/test_split_consistency.py::test_row_to_split_assignment_matches_assign_split_directly`; plus Phase 8's `backend/tests/risk/dataset/test_temporal_ordering.py` |
| Risk | false negatives | covered_by_prior_phase | Phase 9 SC-003 — recall is a primary term in the documented ranking rule, asserted by `backend/tests/risk/benchmark/test_model_selection.py` |
| Risk | model calibration | covered_by_prior_phase | Phase 9 SC-005 — `backend/tests/risk/benchmark/test_calibration_reported.py::test_every_model_reports_a_numeric_calibration_score` and `test_brier_score_exposes_a_calibration_gap_hidden_by_equal_discrimination` |
| Risk | drift sensitivity | new_test_added | `backend/tests/risk/test_drift_sensitivity.py` — scores a deliberately drifted window against the same fitted model and asserts the score moves measurably, proving the model is not frozen/insensitive (FR-003) |
| LLM | hallucination | new_test_added | `backend/tests/llm/test_evidence_grounding.py` — fixture-based citation tracing. **Documented limitation** (spec Assumptions, FR-007): this checks whether specific cited claim IDs/dollar figures trace back to the real `StructuredIncidentPayload`, which is a best-effort proxy, NOT a general-purpose hallucination classifier. No such classifier is in scope for this MVP |
| LLM | unsupported claims | new_test_added | `backend/tests/llm/test_evidence_grounding.py` — same citation-tracing mechanism applied to the `evidence` section; an evidence citation naming a claim ID absent from the payload is flagged. Same documented best-effort limitation as the hallucination row above |
| LLM | insufficient-evidence handling | covered_by_prior_phase | Phase 11 SC-002 — `backend/tests/llm/test_insufficient_evidence.py::test_insufficiency_phrase_is_tagged_true_in_every_run` (100% of runs, not probabilistic) and `test_substantive_root_cause_is_tagged_false_not_applied_indiscriminately` |
| LLM | incorrect-recommendation detection | new_test_added | `backend/tests/llm/test_evidence_grounding.py` — the citation-tracing check applied specifically to `recommended_fix`/`prevention_recommendation`, catching a recommendation that references evidence never supplied. Distinct from the hallucination row: it targets the action the model proposes, not its stated evidence. Same documented best-effort limitation |
| HITL | accept → fix → revalidate | new_test_added | `backend/tests/integration/test_hitl_accept_remediate_revalidate.py` — chains the real Phase 12 accept, Phase 13 remediation, and Phase 14 revalidation routers over HTTP on one shared session, with no mocking at the module boundary (FR-004, SC-003) |
| HITL | reject → feedback → recalculate → re-review | covered_by_prior_phase | Phase 12 — `backend/tests/hitl/test_router_hitl_flow.py::test_full_create_reject_recalculate_accept_flow` already exercises create → reject-with-feedback → recalculate → accept (re-review) end-to-end over real HTTP. Per FR-009 this feature adds no duplicate test |
| Ingestion | large files | limitation_documented | Not testable today: `015-continuous-ingestion` — the feature that would have built the ingestion pipeline — was removed as out-of-scope in commit `6dd9ad2`, and this testing feature was renumbered into its `015` slot. `backend/app/ingestion/` remains an unimplemented Phase-0 placeholder (no router, service, or watcher). Testing this would require either adding production code this feature explicitly must not add, or mocking the very pipeline the test is meant to prove is real. See `backend/tests/ingestion/test_placeholder.py` |
| Ingestion | malformed batches | limitation_documented | Same descoping as the "large files" row above (commit `6dd9ad2`; `app/ingestion/` unimplemented). Note the *file-level* malformed-input case is separately covered by Phase 1's `load_source_csv` validation tests (`test_wrong_column_count_fails_fast`, `test_missing_source_file_fails_fast`) — what is untestable is specifically the *batch* pipeline layer that was descoped. See `backend/tests/ingestion/test_placeholder.py` |
| Ingestion | repeated/continuous uploads | limitation_documented | Same descoping as the rows above (commit `6dd9ad2`; `app/ingestion/` unimplemented). This scenario depended most directly on the deleted watched-folder/multi-batch windowing design, so there is no partial substitute to cite. See `backend/tests/ingestion/test_placeholder.py` |

## Summary

| Status | Count |
|---|---|
| `covered_by_prior_phase` | 13 |
| `new_test_added` | 8 |
| `limitation_documented` | 3 |
| **Total** | **24** |

## Notes on honesty (FR-008, SC-006)

- The three `limitation_documented` rows are **not** silent skips: no test pretends to cover them, and `backend/tests/ingestion/test_placeholder.py` carries the same explanation so a developer who opens that package sees why it is empty.
- The four LLM `new_test_added` rows are honest about being a **best-effort citation-tracing proxy**, not true hallucination detection. Overstating them would violate the same principle the `limitation_documented` rows exist to uphold.
- The Data "empty files" row was **reclassified from covered to new_test_added** while building this map, after verifying no existing test actually covered an empty or header-only source file. Recording the gap and closing it is the point of this exercise; assuming prior coverage would have defeated it.
