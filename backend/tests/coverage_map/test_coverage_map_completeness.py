"""Asserts docs/testing/phase15_coverage_map.md accounts for every test
scenario MVP_CONTEXT.md Section 5 / Phase 15 names (spec 015 FR-001,
SC-001).

The expected scenario list below is hardcoded straight from
MVP_CONTEXT.md's Phase 15 description rather than parsed out of it, per
research.md's documented decision: prior specs are free-form Markdown
prose, not structured data, so scanning them for scenario keywords would
be fragile. A hardcoded list plus a parsed table gives the same guarantee
(nothing goes unaccounted for) while staying robust and human-auditable.
"""

import re
from pathlib import Path

import pytest

COVERAGE_MAP_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "testing" / "phase15_coverage_map.md"
)

VALID_STATUSES = {"covered_by_prior_phase", "new_test_added", "limitation_documented"}

# Sourced verbatim from MVP_CONTEXT.md Phase 15's six category bullets.
EXPECTED_SCENARIOS: list[tuple[str, str]] = [
    ("Data", "missing values"),
    ("Data", "duplicates"),
    ("Data", "invalid types/values/dates"),
    ("Data", "missing columns"),
    ("Data", "empty files"),
    ("Anomaly", "injected-anomaly detection accuracy"),
    ("Anomaly", "false positives"),
    ("Anomaly", "false negatives"),
    ("Anomaly", "detection latency"),
    ("Anomaly", "model stability"),
    ("Risk", "data-leakage test"),
    ("Risk", "temporal-split-correctness test"),
    ("Risk", "false negatives"),
    ("Risk", "model calibration"),
    ("Risk", "drift sensitivity"),
    ("LLM", "hallucination"),
    ("LLM", "unsupported claims"),
    ("LLM", "insufficient-evidence handling"),
    ("LLM", "incorrect-recommendation detection"),
    ("HITL", "accept → fix → revalidate"),
    ("HITL", "reject → feedback → recalculate → re-review"),
    ("Ingestion", "large files"),
    ("Ingestion", "malformed batches"),
    ("Ingestion", "repeated/continuous uploads"),
]

# A `Reference` this short is a placeholder, not a real citation -- the
# whole point of the map is that a reader can open what it points at.
MIN_REFERENCE_LENGTH = 20


def _parse_rows() -> list[dict[str, str]]:
    """Parses the `Category | Scenario | Status | Reference` table,
    skipping the separate Summary table (whose rows have 2 columns, not
    4) and the header/separator lines."""
    rows = []
    for line in COVERAGE_MAP_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 4:
            continue  # Summary table or malformed line
        if cells[0] in ("Category", "---") or set(cells[0]) <= {"-", ":"}:
            continue  # header or separator
        rows.append(
            {"category": cells[0], "scenario": cells[1], "status": cells[2], "reference": cells[3]}
        )
    return rows


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    assert COVERAGE_MAP_PATH.exists(), f"Coverage map not found at {COVERAGE_MAP_PATH}"
    parsed = _parse_rows()
    assert parsed, "Parsed zero rows from the coverage map -- has the table format changed?"
    return parsed


def test_every_named_scenario_appears_exactly_once(rows):
    """SC-001: zero unaccounted-for scenarios."""
    seen = [(r["category"], r["scenario"]) for r in rows]
    for expected in EXPECTED_SCENARIOS:
        count = seen.count(expected)
        assert count == 1, (
            f"Scenario {expected} appears {count} times in the coverage map; expected exactly 1."
        )


def test_no_unexpected_scenarios_present(rows):
    """Guards the reverse direction: a row that doesn't correspond to a
    real MVP_CONTEXT.md scenario means the map (or this list) drifted."""
    expected = set(EXPECTED_SCENARIOS)
    for row in rows:
        key = (row["category"], row["scenario"])
        assert key in expected, f"Coverage map row {key} is not a MVP_CONTEXT.md Phase 15 scenario."


def test_every_row_has_a_valid_status(rows):
    for row in rows:
        assert row["status"] in VALID_STATUSES, (
            f"Row {row['category']}/{row['scenario']} has invalid status {row['status']!r}; "
            f"expected one of {sorted(VALID_STATUSES)}."
        )


def test_every_row_has_a_substantive_reference(rows):
    """FR-001/FR-008: a row with an empty or placeholder Reference is
    exactly the silent gap this map exists to prevent."""
    for row in rows:
        reference = row["reference"]
        assert reference, f"Row {row['category']}/{row['scenario']} has an empty Reference."
        assert len(reference) >= MIN_REFERENCE_LENGTH, (
            f"Row {row['category']}/{row['scenario']}'s Reference is too short to be a real "
            f"citation: {reference!r}"
        )
        # Deliberately excludes the word "placeholder": several legitimate
        # references describe `app/ingestion/` as an unimplemented *Phase-0
        # placeholder*, which is substantive prose, not an unfilled cell.
        # TBD/TODO/FIXME have no such legitimate use here.
        assert not re.search(r"\b(TBD|TODO|FIXME)\b", reference, re.IGNORECASE), (
            f"Row {row['category']}/{row['scenario']} still has an unfilled Reference: "
            f"{reference!r}"
        )


def test_limitation_rows_carry_a_real_explanation(rows):
    """FR-008: `limitation_documented` must explain *why*, not just
    assert a limitation exists -- otherwise it's a silent skip wearing a
    label."""
    limitation_rows = [r for r in rows if r["status"] == "limitation_documented"]
    assert limitation_rows, (
        "Expected at least the three descoped Ingestion rows to be marked limitation_documented."
    )
    for row in limitation_rows:
        assert len(row["reference"]) >= 80, (
            f"Row {row['category']}/{row['scenario']} is marked limitation_documented but its "
            f"Reference is too brief to explain why: {row['reference']!r}"
        )


def test_referenced_test_files_actually_exist(rows):
    """Every `backend/tests/...py` path named anywhere in the map must
    resolve on disk -- a citation pointing at a file that doesn't exist
    is worse than no citation, since it reads as coverage."""
    repo_root = COVERAGE_MAP_PATH.resolve().parents[2]
    missing = []
    for row in rows:
        for path_str in re.findall(r"backend/tests/[\w/]+\.py", row["reference"]):
            if not (repo_root / path_str).exists():
                missing.append(f"{row['category']}/{row['scenario']} -> {path_str}")
    assert not missing, "Coverage map cites test files that do not exist:\n" + "\n".join(missing)
