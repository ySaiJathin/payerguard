"""PayerGuard backend entrypoint.

Wires per-feature routers together. This file stays thin -- no business
logic here. Each domain module under app/ owns its own router; this
module only includes them.
"""

from fastapi import FastAPI

from app.anomaly.router import router as anomaly_router
from app.baseline.router import router as baseline_router
from app.data_engineering.router import router as data_engineering_router
from app.features.router import router as features_router
from app.features.selection.router import router as selection_router
from app.quality.router import router as quality_router
from app.risk.benchmark.router import router as risk_benchmark_router
from app.risk.dataset.router import router as risk_dataset_router
from app.risk.scoring.router import router as risk_scoring_router

app = FastAPI(title="PayerGuard")

for r in (
    data_engineering_router,
    quality_router,
    baseline_router,
    features_router,
    selection_router,
    anomaly_router,
    risk_dataset_router,
    risk_benchmark_router,
    risk_scoring_router,
):
    app.include_router(r)

# Remaining domain routers (ingestion, llm, incidents, hitl, remediation,
# revalidation, simulation, audit) are wired in as each feature is
# implemented -- their router.py files are still placeholders as of this
# feature (010-severity-impact-priority-scoring). The `risk` module is now
# complete: dataset (Phase 8), benchmark (Phase 9), scoring (Phase 10).
