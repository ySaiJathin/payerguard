from app.risk.benchmark.benchmark_runner import run_benchmark
from app.risk.benchmark.data_loading import build_benchmark_frame
from tests.risk.benchmark._fixtures import make_rows, make_split


def test_label_distribution_context_matches_the_full_assembled_dataset(tmp_path):
    rows = make_rows(n_days=100, seed=3)
    split = make_split(n_days=100)

    frame = build_benchmark_frame(rows=rows, split=split)
    results, _warning = run_benchmark(frame, model_out_dir=tmp_path)

    worthy = sum(1 for r in rows if r.investigation_risk_label == 1)
    for result in results:
        ctx = result.label_distribution_context
        assert ctx["total_rows"] == len(rows)
        assert ctx["investigation_worthy_count"] == worthy
        assert ctx["not_investigation_worthy_count"] == len(rows) - worthy
