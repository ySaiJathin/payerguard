"""SQLAlchemy engine/session setup and the shared declarative `Base`.

This is the first feature (012-incident-management-hitl) to need real
relational persistence -- every prior phase used file-based JSON/CSV
under `data/`, since incident lifecycle (multiple state transitions over
time, linked feedback history) is a poor fit for a flat file (plan.md's
Storage section). Tests build their own isolated engine (see
`backend/tests/_db_fixtures.py`) rather than touching the module-level
`engine`/`SessionLocal` below, which are bound to `DATABASE_URL`.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _connect_args(database_url: str) -> dict:
    # SQLite's default same-thread check would reject the connection
    # FastAPI's threadpool-backed request handling hands it -- harmless
    # for our use (one session per request, closed immediately after).
    return {"check_same_thread": False} if database_url.startswith("sqlite") else {}


def _make_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    return create_engine(url, connect_args=_connect_args(url))


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency: yields a request-scoped session, always closed
    afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Creates every table registered on `Base.metadata` -- callable once
    at app startup, and independently by tests against their own isolated
    engine. No Alembic migration scaffolding yet (out of this feature's
    scope); this is sufficient for the MVP and doesn't block adding
    Alembic later without changing these models.
    """
    Base.metadata.create_all(bind=target_engine or engine)
