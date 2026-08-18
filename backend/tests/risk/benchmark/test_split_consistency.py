from app.features.selection.temporal_split import assign_split
from app.risk.benchmark.data_loading import build_benchmark_frame
from tests.risk.benchmark._fixtures import make_rows, make_split


def test_row_to_split_assignment_matches_assign_split_directly():
    rows = make_rows(n_days=100, seed=2)
    split = make_split(n_days=100)

    frame = build_benchmark_frame(rows=rows, split=split)

    expected_counts = {"train": 0, "validation": 0, "test": 0}
    for row in rows:
        expected_counts[assign_split(row.window_start, split)] += 1

    assert len(frame.train[0]) == expected_counts["train"]
    assert len(frame.validation[0]) == expected_counts["validation"]
    assert len(frame.test[0]) == expected_counts["test"]
    assert sum(expected_counts.values()) == len(rows)
