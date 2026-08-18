"""PayerGuard backend entrypoint.

STATUS: not implemented yet. Wires per-feature routers together. This file
must stay thin -- no business logic here. Each domain module under app/
(ingestion, data_engineering, quality, baseline, features, anomaly, risk,
llm, incidents, hitl, remediation, revalidation, simulation, audit) owns
its own router; this module only includes them.
"""
# from fastapi import FastAPI
#
# app = FastAPI(title="PayerGuard")
#
# from app.ingestion.router import router as ingestion_router
# from app.quality.router import router as quality_router
# from app.baseline.router import router as baseline_router
# from app.anomaly.router import router as anomaly_router
# from app.risk.router import router as risk_router
# from app.llm.router import router as llm_router
# from app.incidents.router import router as incidents_router
# from app.hitl.router import router as hitl_router
# from app.revalidation.router import router as revalidation_router
# from app.simulation.router import router as simulation_router
# from app.audit.router import router as audit_router
#
# for r in (
#     ingestion_router, quality_router, baseline_router, anomaly_router,
#     risk_router, llm_router, incidents_router, hitl_router,
#     revalidation_router, simulation_router, audit_router,
# ):
#     app.include_router(r)
