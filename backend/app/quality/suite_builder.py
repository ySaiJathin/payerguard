"""Builds category-appropriate Great Expectations suites (FR-001) from
Phase 1's column categorization, wiring each category to exactly the
expectation types that make sense for it:

- identifier: completeness (+ CLM_ID claim-grain uniqueness, FR-002)
- date: completeness + ISO-format check on the original string batch,
  plus a range check on a separately-parsed datetime batch (GX's between
  expectation needs matching dtypes -- see expectations/range_checks.py)
- amount: completeness + value >= 0 validity (FR-003)
- utilization_duration: completeness + non-negative/observed-max range
- categorical_code / diagnosis_procedure_code: completeness + code-set
  membership against the raw-file reference universe (FR-006)

Every category gets at least a completeness expectation (Edge Cases: no
category is ever left with an empty, silently-skipped suite).
"""

from dataclasses import dataclass, field
from functools import partial
from typing import Callable
from uuid import uuid4

import great_expectations as gx
import pandas as pd
from great_expectations import ExpectationSuite

from app.quality.expectations import completeness, range_checks, uniqueness, validity
from app.quality.schemas import ColumnCategory, CompletenessCalibrationEntry, ExpectationCheckResult

CLM_ID_COLUMN = "CLM_ID"
UTILIZATION_MAX_SLACK_MULTIPLIER = 1.1  # 10% headroom above the batch's own observed max


@dataclass
class SuiteRun:
    category: ColumnCategory
    suite: ExpectationSuite
    batch: object
    extractors: list[Callable[[dict], list[ExpectationCheckResult]]] = field(default_factory=list)


def _columns_for(categories: dict[str, ColumnCategory], category: ColumnCategory) -> list[str]:
    return [col for col, cat in categories.items() if cat == category]


def _make_batch(context, df: pd.DataFrame, name: str):
    unique_name = f"{name}-{uuid4().hex[:8]}"
    data_source = context.data_sources.add_pandas(unique_name)
    asset = data_source.add_dataframe_asset(unique_name)
    batch_definition = asset.add_batch_definition_whole_dataframe(unique_name)
    return batch_definition.get_batch(batch_parameters={"dataframe": df})


def build_suites(
    context,
    df: pd.DataFrame,
    categories: dict[str, ColumnCategory],
    calibration: dict[str, CompletenessCalibrationEntry],
    known_code_values: dict[str, list[str]],
    expected_unique_claim_count: int,
    reference_date_bounds: tuple[object, object] | None = None,
) -> list[SuiteRun]:
    runs: list[SuiteRun] = []
    completeness_extractor = partial(completeness.extract_results, calibration=calibration)

    # -- identifier: completeness (+ CLM_ID uniqueness) --
    identifier_columns = _columns_for(categories, ColumnCategory.IDENTIFIER)
    if identifier_columns:
        suite_name = "identifier_suite"
        suite = context.suites.add(gx.ExpectationSuite(name=f"{suite_name}-{uuid4().hex[:8]}"))
        completeness.add_to_suite(suite, identifier_columns)
        extractors = [completeness_extractor]
        if CLM_ID_COLUMN in identifier_columns:
            uniqueness.add_to_suite(suite, expected_unique_claim_count)
            extractors.append(partial(uniqueness.extract_results, expected_unique_claim_count=expected_unique_claim_count))
        runs.append(SuiteRun(ColumnCategory.IDENTIFIER, suite, _make_batch(context, df, suite_name), extractors))

    # -- date: completeness + format on the string batch, range on a parsed-datetime batch --
    date_columns = _columns_for(categories, ColumnCategory.DATE)
    if date_columns:
        format_suite_name = "date_format_suite"
        format_suite = context.suites.add(gx.ExpectationSuite(name=f"{format_suite_name}-{uuid4().hex[:8]}"))
        completeness.add_to_suite(format_suite, date_columns)
        for column in date_columns:
            range_checks.add_date_format(format_suite, column)
        runs.append(
            SuiteRun(
                ColumnCategory.DATE,
                format_suite,
                _make_batch(context, df, format_suite_name),
                [completeness_extractor, range_checks.extract_format_results],
            )
        )

        if reference_date_bounds is not None:
            min_ts, max_ts = reference_date_bounds
            range_suite_name = "date_range_suite"
            range_suite = context.suites.add(gx.ExpectationSuite(name=f"{range_suite_name}-{uuid4().hex[:8]}"))
            parsed_df = df.copy()
            for column in date_columns:
                parsed_df[column] = pd.to_datetime(df[column], format="%Y-%m-%d", errors="coerce")
                range_checks.add_date_range(range_suite, column, min_ts, max_ts)
            runs.append(
                SuiteRun(
                    ColumnCategory.DATE,
                    range_suite,
                    _make_batch(context, parsed_df, range_suite_name),
                    [range_checks.extract_range_results],
                )
            )

    # -- amount: completeness + value >= 0 --
    amount_columns = _columns_for(categories, ColumnCategory.AMOUNT)
    if amount_columns:
        suite_name = "amount_suite"
        suite = context.suites.add(gx.ExpectationSuite(name=f"{suite_name}-{uuid4().hex[:8]}"))
        completeness.add_to_suite(suite, amount_columns)
        validity.add_amount_validity(suite, amount_columns)
        runs.append(
            SuiteRun(
                ColumnCategory.AMOUNT,
                suite,
                _make_batch(context, df, suite_name),
                [completeness_extractor, validity.extract_amount_results],
            )
        )

    # -- utilization_duration: completeness + non-negative/observed-max range --
    utilization_columns = _columns_for(categories, ColumnCategory.UTILIZATION_DURATION)
    if utilization_columns:
        suite_name = "utilization_duration_suite"
        suite = context.suites.add(gx.ExpectationSuite(name=f"{suite_name}-{uuid4().hex[:8]}"))
        completeness.add_to_suite(suite, utilization_columns)
        for column in utilization_columns:
            observed_max = df[column].max(skipna=True)
            max_value = float(observed_max) * UTILIZATION_MAX_SLACK_MULTIPLIER if pd.notna(observed_max) else 0.0
            range_checks.add_utilization_range(suite, column, max_value)
        runs.append(
            SuiteRun(
                ColumnCategory.UTILIZATION_DURATION,
                suite,
                _make_batch(context, df, suite_name),
                [completeness_extractor, range_checks.extract_range_results],
            )
        )

    # -- categorical_code / diagnosis_procedure_code: completeness + code-set membership --
    for category in (ColumnCategory.CATEGORICAL_CODE, ColumnCategory.DIAGNOSIS_PROCEDURE_CODE):
        columns = _columns_for(categories, category)
        if not columns:
            continue
        suite_name = f"{category.value}_suite"
        suite = context.suites.add(gx.ExpectationSuite(name=f"{suite_name}-{uuid4().hex[:8]}"))
        completeness.add_to_suite(suite, columns)
        column_value_sets = {col: known_code_values[col] for col in columns if col in known_code_values}
        if column_value_sets:
            validity.add_code_set_validity(suite, column_value_sets)
        runs.append(
            SuiteRun(
                category,
                suite,
                _make_batch(context, df, suite_name),
                [completeness_extractor, validity.extract_code_set_results],
            )
        )

    return runs
