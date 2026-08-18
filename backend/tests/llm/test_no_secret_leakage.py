"""Static secret-scan (spec FR-008, SC-006): `MISTRAL_API_KEY` must only
ever be read via `os.environ`/`os.getenv`, never hardcoded as a string
literal assignment, anywhere in `backend/app/llm/`.
"""

import re
from pathlib import Path

LLM_MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "llm"

# Matches e.g. `MISTRAL_API_KEY = "..."` or `api_key="sk-..."` but not
# `os.environ["MISTRAL_API_KEY"]` / `os.environ.get("MISTRAL_API_KEY")`.
_HARDCODED_ASSIGNMENT = re.compile(
    r"""(?<!os\.environ\[)(?<!os\.environ\.get\()['"]?MISTRAL_API_KEY['"]?\s*[:=]\s*['"][^'"]+['"]"""
)


def test_no_hardcoded_mistral_api_key_in_llm_module_source():
    py_files = sorted(LLM_MODULE_DIR.glob("*.py"))
    assert py_files, "expected to find backend/app/llm/*.py files"

    violations = []
    for file_path in py_files:
        text = file_path.read_text(encoding="utf-8")
        if _HARDCODED_ASSIGNMENT.search(text):
            violations.append(file_path.name)

    assert not violations, f"possible hardcoded MISTRAL_API_KEY found in: {violations}"


def test_mistral_client_reads_key_only_via_environment():
    source = (LLM_MODULE_DIR / "mistral_client.py").read_text(encoding="utf-8")
    assert "os.environ" in source or "os.getenv" in source
    assert 'MISTRAL_API_KEY = "' not in source
    assert "MISTRAL_API_KEY = '" not in source
