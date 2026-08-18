"""Spec SC-004 / US1 Acceptance Scenario 4: a code/dependency audit
confirms zero import-time dependency from the remediation execution path
to Phase 11's LLM client -- handler selection is driven solely by the
versioned rule tables, never a model call.

A static AST check rather than a live import: even an import that would
raise at runtime (e.g. missing credentials) still counts as a dependency
this feature must not have, so parsing the source is a stronger
guarantee than "the module happens to import cleanly today".
"""

import ast
from pathlib import Path

import app.remediation as remediation_package

# Any of these names appearing as an imported module or "from X import Y"
# target anywhere under backend/app/remediation/ would be an LLM-execution
# dependency this feature must never have (FR-005).
_FORBIDDEN_IMPORT_PREFIXES = ("app.llm", "mistralai")


def _imported_module_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_remediation_module_imports_the_llm_client():
    remediation_dir = Path(remediation_package.__file__).resolve().parent
    violations: dict[str, set[str]] = {}

    for py_file in remediation_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        imported = _imported_module_names(tree)
        forbidden = {
            name
            for name in imported
            if any(name == prefix or name.startswith(prefix + ".") for prefix in _FORBIDDEN_IMPORT_PREFIXES)
        }
        if forbidden:
            violations[str(py_file)] = forbidden

    assert not violations, f"remediation module(s) import the LLM client at execution time: {violations}"
