"""Static import-graph check (spec FR-005, FR-009, SC-003; research.md):
`investigation_service.py` -- and, transitively, every other file in
`backend/app/llm/` -- must have zero import of `app.incidents` or
`app.remediation`'s write-capable functions. This is enforced by parsing
the actual source files with `ast`, not by trusting that nobody adds such
an import later.
"""

import ast
from pathlib import Path

FORBIDDEN_MODULE_PREFIXES = ("app.incidents", "app.remediation")

LLM_MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "llm"


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


def test_no_llm_module_file_imports_incidents_or_remediation():
    py_files = sorted(LLM_MODULE_DIR.glob("*.py"))
    assert py_files, "expected to find backend/app/llm/*.py files"

    violations = {}
    for file_path in py_files:
        imported = _imported_module_names(file_path)
        forbidden_hits = {
            name for name in imported if any(name.startswith(prefix) for prefix in FORBIDDEN_MODULE_PREFIXES)
        }
        if forbidden_hits:
            violations[file_path.name] = forbidden_hits

    assert not violations, f"llm module files import write-capable modules: {violations}"
