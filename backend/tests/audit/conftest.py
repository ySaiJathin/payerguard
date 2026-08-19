"""Keeps audit tests from writing into the real project data directory.

`tests/audit/_fixtures.py` drives the *real* `create_incident`, which
calls Phase 11's `investigate()`, which appends to
`investigation_log`'s store. That store defaults to the repo's own
`data/reports/llm_investigations.json` -- so without this redirect, simply
running the audit suite mutates a tracked file and leaves fixture
investigations in the project's real data. Caught exactly that way: a
test run showed up as 154 unstaged lines in `git status`.

Autouse so it applies to every test in this package, including the ones
that only reach `investigate()` indirectly through the lifecycle fixture
and would otherwise be easy to miss.
"""

import pytest

from app.llm import investigation_log


@pytest.fixture(autouse=True)
def isolate_investigation_log(tmp_path, monkeypatch):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
