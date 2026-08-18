"""Static import-graph check (spec FR-006, SC-005; research.md), mirroring
Phase 11's `test_write_access_boundary.py` pattern: `reject_service.py`
must have zero import of Phase 7/9's model-fitting functions, so feedback
capture has no reachable code path to trigger retraining, not just a
convention that nothing currently calls it.
"""

import ast
from pathlib import Path

FORBIDDEN_MODULE_PREFIXES = ("app.anomaly.benchmark", "app.risk.benchmark")

REJECT_SERVICE_FILE = Path(__file__).resolve().parents[2] / "app" / "hitl" / "reject_service.py"


def _imported_module_names(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_reject_service_does_not_import_model_fitting_functions():
    assert REJECT_SERVICE_FILE.exists()
    imported = _imported_module_names(REJECT_SERVICE_FILE)

    forbidden_hits = {
        name for name in imported if any(name.startswith(prefix) for prefix in FORBIDDEN_MODULE_PREFIXES)
    }
    assert not forbidden_hits, f"reject_service.py imports retraining-capable modules: {forbidden_hits}"
