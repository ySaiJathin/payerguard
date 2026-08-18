"""Shared DB session builder for `tests/incidents/` and `tests/hitl/` --
not a test module itself (no `test_` prefix, so pytest doesn't collect
it).

Builds a fresh, isolated `sqlite:///:memory:` engine per call -- no
Docker/Postgres needed to test the real SQLAlchemy models (012's Setup
phase). Importing both `app.incidents.models` and `app.hitl.models`
before `init_db()` ensures every table is registered on `Base.metadata`,
regardless of which module a given test file imports directly.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.hitl.models  # noqa: F401 -- registers HumanFeedback/IncidentStatusTransition on Base.metadata
import app.incidents.models  # noqa: F401 -- registers Incident on Base.metadata
from app.core.database import init_db


def make_test_session() -> Session:
    # StaticPool is required for sqlite:///:memory: -- without it, each
    # new connection checkout (e.g. from a different thread, as FastAPI's
    # TestClient uses for request handling) gets its own fresh, empty
    # in-memory database, silently losing every table/row created so far.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(target_engine=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return factory()
