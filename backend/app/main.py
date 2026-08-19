"""PayerGuard backend entrypoint.

Wires per-feature routers together. This file stays thin -- no business
logic here. Each domain module under app/ owns its own router; this
module only includes them.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.anomaly.router import router as anomaly_router
from app.audit.router import router as audit_router
from app.baseline.router import router as baseline_router
from app.core.config import get_settings
from app.core.database import init_db
from app.data_engineering.router import router as data_engineering_router
from app.demo.router import router as demo_router
from app.features.router import router as features_router
from app.features.selection.router import router as selection_router
from app.hitl.router import router as hitl_router
from app.incidents.router import router as incidents_router
from app.ingestion.router import router as ingestion_router
from app.llm.router import router as llm_router
from app.quality.router import router as quality_router
from app.remediation.router import router as remediation_router
from app.revalidation.router import router as revalidation_router
from app.risk.benchmark.router import router as risk_benchmark_router
from app.risk.dataset.router import router as risk_dataset_router
from app.risk.scoring.router import router as risk_scoring_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # First feature needing real relational tables (012) -- creates them
    # if they don't exist yet. No Alembic migration scaffolding yet (out
    # of this feature's scope); sufficient for the MVP.
    init_db()
    yield


app = FastAPI(title="PayerGuard", lifespan=lifespan)

# Browser clients (Vite dev server, Dockerized frontend) run on a different
# origin than the API, so requests are preflighted. Origins come from config,
# never hardcoded here (constitution Principle II).
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    llm_router,
    incidents_router,
    hitl_router,
    remediation_router,
    revalidation_router,
    audit_router,
    demo_router,
    ingestion_router,
):
    app.include_router(r)

# `simulation` has no router wired in and remains a Phase-0 placeholder --
# out of scope (constitution "Scope Discipline"; see
# app/ingestion/watcher.py). `ingestion` (this module, spec
# 017-batch-file-ingestion) now owns manual + repeated-batch upload of the
# raw claims schema at /claims/upload, distinct from `app/demo`'s
# /demo/upload for the cleaned/synthetic schema.
