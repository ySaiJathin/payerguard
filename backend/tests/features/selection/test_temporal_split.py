import pandas as pd
import pytest

from app.features.selection.temporal_split import assign_split, compute_temporal_split


def _claim_dates(n_days: int = 1000) -> pd.Series:
    dates = pd.date_range("2015-04-01", periods=n_days, freq="D")
    # Repeat each date a few times (multiple claims per day) and shuffle the
    # row order, so the split logic can't rely on input already being sorted.
    repeated = dates.repeat(3)
    return pd.Series(repeated).sample(frac=1, random_state=42).reset_index(drop=True)


def test_split_is_chronological_70_15_15():
    dates = _claim_dates()
    split = compute_temporal_split(dates)

    assert split.train_date_range.start <= split.train_date_range.end
    assert split.train_date_range.end < split.validation_date_range.start
    assert split.validation_date_range.end < split.test_date_range.start

    total = split.train_count + split.validation_count + split.test_count
    assert total == len(dates)
    assert split.train_count / total == pytest.approx(0.70, abs=0.02)
    assert split.validation_count / total == pytest.approx(0.15, abs=0.02)
    assert split.test_count / total == pytest.approx(0.15, abs=0.02)


def test_split_has_zero_date_overlap():
    dates = _claim_dates()
    split = compute_temporal_split(dates)

    assert split.train_date_range.end < split.validation_date_range.start
    assert split.validation_date_range.end < split.test_date_range.start


def test_split_is_deterministic_on_unmodified_data():
    dates = _claim_dates()
    split_a = compute_temporal_split(dates)
    split_b = compute_temporal_split(dates)

    assert split_a.train_date_range == split_b.train_date_range
    assert split_a.validation_date_range == split_b.validation_date_range
    assert split_a.test_date_range == split_b.test_date_range
    assert split_a.train_count == split_b.train_count
    assert split_a.validation_count == split_b.validation_count
    assert split_a.test_count == split_b.test_count


def test_split_is_order_independent_not_a_shuffle():
    dates = _claim_dates()
    shuffled = dates.sample(frac=1, random_state=99).reset_index(drop=True)

    split_original = compute_temporal_split(dates)
    split_shuffled = compute_temporal_split(shuffled)

    assert split_original.train_date_range == split_shuffled.train_date_range
    assert split_original.test_date_range == split_shuffled.test_date_range


def test_assign_split_classifies_claim_dates_correctly():
    dates = _claim_dates()
    split = compute_temporal_split(dates)

    assert assign_split(split.train_date_range.start, split) == "train"
    assert assign_split(split.validation_date_range.start, split) == "validation"
    assert assign_split(split.test_date_range.end, split) == "test"


def test_too_few_distinct_dates_raises():
    with pytest.raises(ValueError):
        compute_temporal_split(pd.Series(pd.to_datetime(["2020-01-01", "2020-01-02"])))


def test_small_tail_portion_sets_sample_size_warning():
    dates = _claim_dates(n_days=10)
    split = compute_temporal_split(dates)
    assert split.sample_size_warning is not None
