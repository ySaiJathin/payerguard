"""The generator's contract: schema fidelity, reproducibility, and ground truth."""

import numpy as np
import pandas as pd
import pytest

from app.demo import batches
from app.demo.column_profile import load_column_profile
from app.demo.generator import (
    CLAIM_FROM_COLUMN,
    GROUND_TRUTH_COLUMN,
    NO_INJECTION,
    generate_batch,
    inject,
)
from app.demo.schemas import BatchSpec, InjectionCluster, InjectionPlan, InjectionType


@pytest.fixture(scope="module")
def profile() -> dict:
    return load_column_profile()


def _small_spec(**overrides) -> BatchSpec:
    defaults = dict(
        batch_id="test-batch",
        label="Test",
        description="Small batch for tests.",
        claim_count=400,
        start_date="2026-01-05",
        end_date="2026-02-15",
        seed=7,
    )
    defaults.update(overrides)
    return BatchSpec(**defaults)


def test_generated_batch_matches_the_source_schema_exactly(profile):
    df, _labels = generate_batch(_small_spec(), profile)
    assert list(df.columns) == list(profile["column_order"])


def test_generation_is_reproducible_from_the_spec(profile):
    first, first_labels = generate_batch(_small_spec(), profile)
    second, second_labels = generate_batch(_small_spec(), profile)
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_series_equal(first_labels, second_labels)


def test_different_specs_produce_different_batches(profile):
    first, _ = generate_batch(_small_spec(seed=7), profile)
    second, _ = generate_batch(_small_spec(seed=8, claim_count=500), profile)
    assert len(first) != len(second)


def test_every_row_carries_at_most_one_injection_label(profile):
    plan = InjectionPlan(
        rates={t: 0.04 for t in InjectionType},
        clusters=[
            InjectionCluster(
                name="cluster",
                rates={InjectionType.amount_spike: 0.05, InjectionType.duplicate_spike: 0.05},
            )
        ],
    )
    df, labels = generate_batch(_small_spec(injection_plan=plan), profile)

    assert labels.index.equals(df.index)
    assert not labels.index.duplicated().any()
    assert set(labels.unique()) <= {NO_INJECTION} | {t.value for t in InjectionType}


def test_each_injection_type_is_actually_applied(profile):
    plan = InjectionPlan(rates={t: 0.05 for t in InjectionType})
    _df, labels = generate_batch(_small_spec(claim_count=800, injection_plan=plan), profile)
    produced = set(labels.unique()) - {NO_INJECTION}
    assert produced == {t.value for t in InjectionType}


def test_missing_value_spike_really_raises_the_row_null_count(profile):
    plan = InjectionPlan(rates={InjectionType.missing_value_spike: 0.1})
    df, labels = generate_batch(_small_spec(injection_plan=plan), profile)

    injected = df.loc[labels == InjectionType.missing_value_spike.value]
    clean = df.loc[labels == NO_INJECTION]
    assert injected.isna().sum(axis=1).mean() > clean.isna().sum(axis=1).mean() * 1.5


def test_amount_spike_really_raises_the_paid_amount(profile):
    plan = InjectionPlan(rates={InjectionType.amount_spike: 0.1})
    df, labels = generate_batch(_small_spec(injection_plan=plan), profile)

    injected = pd.to_numeric(df.loc[labels == InjectionType.amount_spike.value, "CLM_PMT_AMT"])
    clean = pd.to_numeric(df.loc[labels == NO_INJECTION, "CLM_PMT_AMT"])
    assert injected.median() > clean.median() * 10


def test_duplicate_spike_rows_are_exact_copies_of_an_earlier_row(profile):
    plan = InjectionPlan(rates={InjectionType.duplicate_spike: 0.1})
    df, labels = generate_batch(_small_spec(injection_plan=plan), profile)

    duplicated = df.duplicated(keep="first")
    injected_rows = labels[labels == InjectionType.duplicate_spike.value].index
    assert duplicated.loc[injected_rows].all()


def test_batch_is_sorted_by_claim_date(profile):
    df, _labels = generate_batch(_small_spec(), profile)
    dates = pd.to_datetime(df[CLAIM_FROM_COLUMN], errors="coerce")
    assert dates.is_monotonic_increasing


def test_injection_targets_are_clustered_in_time_not_uniform(profile):
    """A cluster is supposed to be localised -- if its rows were spread
    uniformly the demo's severity bands would all collapse to one."""
    plan = InjectionPlan(
        clusters=[InjectionCluster(name="c", rates={InjectionType.amount_spike: 0.05}, density=1.0)]
    )
    df, labels = generate_batch(_small_spec(claim_count=1000, injection_plan=plan), profile)

    dates = pd.to_datetime(df[CLAIM_FROM_COLUMN], errors="coerce")
    injected_span = (
        dates.loc[labels == InjectionType.amount_spike.value].max()
        - dates.loc[labels == InjectionType.amount_spike.value].min()
    ).days
    batch_span = (dates.max() - dates.min()).days
    assert injected_span < batch_span * 0.5


def test_inject_never_relabels_an_already_injected_row(profile):
    df, labels = generate_batch(
        _small_spec(injection_plan=InjectionPlan(rates={InjectionType.amount_spike: 0.1})), profile
    )
    before = labels[labels == InjectionType.amount_spike.value].index

    df2, labels2 = inject(
        df, labels, InjectionPlan(rates={InjectionType.missing_value_spike: 0.1}), profile, seed=99
    )
    still_amount = labels2.reindex(before)
    assert (still_amount == InjectionType.amount_spike.value).all()


def test_the_three_demo_batches_differ_from_each_other():
    manifest = batches.ensure_generated()
    assert len(manifest) == 3
    assert len({entry.rows for entry in manifest}) == 3
    assert len({round(entry.clm_pmt_amt_median) for entry in manifest}) == 3
    assert all(entry.injected_rows > 0 for entry in manifest)


def test_load_batch_round_trips_the_ground_truth():
    for spec in batches.BATCH_SPECS:
        df, labels = batches.load_batch(spec.batch_id)
        assert labels.index.equals(df.index)
        assert labels.name == GROUND_TRUTH_COLUMN
        assert (labels != NO_INJECTION).sum() > 0
