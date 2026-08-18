"""PayerGuard backend entrypoint.

Wires per-feature routers together. This file stays thin -- no business
logic here. Each domain module under app/ owns its own router; this
module only includes them.
"""

from fastapi import FastAPI

from app.data_engineering.router import router as data_engineering_router

app = FastAPI(title="PayerGuard")

for r in (data_engineering_router,):
    app.include_router(r)

# Remaining domain routers (ingestion, quality, baseline, anomaly, risk,
# llm, incidents, hitl, revalidation, simulation, audit) are wired in as
# each feature is implemented -- their router.py files are still
# placeholders as of this feature (002-cleaning-standardization, still
# within the data_engineering module).
