"""Isolates every incidents test from the real repo's data/ directory.

`create_incident`/`recalculate_incident` call Phase 11's `investigate()`,
which persists to `data/reports/llm_investigations.json` by default --
without this fixture, every test run would write real files into the
tracked repo (a mistake caught and fixed during 009's implementation;
applying the lesson here from the start).
"""

import pytest

from app.llm import investigation_log


@pytest.fixture(autouse=True)
def _isolate_llm_investigation_log(tmp_path, monkeypatch):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
