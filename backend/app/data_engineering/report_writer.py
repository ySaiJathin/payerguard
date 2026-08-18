"""Persists profiling output as durable, reviewable artifacts on disk.

Writes a human-readable Markdown narrative plus machine-readable JSON (the
full report and a standalone column-category mapping) per research.md
("Report artifacts as Markdown + JSON pair"). Each write overwrites any
prior report rather than merging with it (spec Edge Cases -- re-running
profiling after the source file changes must regenerate fresh, not append).
"""

import json
from pathlib import Path

from app.data_engineering.paths import reports_dir as default_reports_dir
from app.data_engineering.schemas import ColumnProfile, ProfilingReport

PROFILING_REPORT_JSON = "profiling_report.json"
PROFILING_REPORT_MD = "profiling_report.md"
COLUMN_CATEGORIES_JSON = "column_categories.json"


def write_profiling_report(report: ProfilingReport, out_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or default_reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / PROFILING_REPORT_JSON
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    md_path = out_dir / PROFILING_REPORT_MD
    md_path.write_text(_render_markdown(report), encoding="utf-8")

    categories_path = out_dir / COLUMN_CATEGORIES_JSON
    categories = {col.column_name: col.category.value for col in report.columns}
    categories_path.write_text(json.dumps(categories, indent=2), encoding="utf-8")

    return {"json": json_path, "markdown": md_path, "categories": categories_path}


def read_profiling_report(out_dir: Path | None = None) -> ProfilingReport | None:
    out_dir = out_dir or default_reports_dir()
    json_path = out_dir / PROFILING_REPORT_JSON
    if not json_path.exists():
        return None
    return ProfilingReport.model_validate_json(json_path.read_text(encoding="utf-8"))


def _column_notes(col: ColumnProfile) -> str:
    if col.numeric_stats:
        s = col.numeric_stats
        return f"mean={s.mean:.2f} median={s.median:.2f} std={s.std:.2f} min={s.min:.2f} max={s.max:.2f}"
    if col.date_format_observed:
        return f"format={col.date_format_observed} min={col.date_min} max={col.date_max}"
    if col.categorical_top_values:
        top = ", ".join(f"{v.value}={v.count}" for v in col.categorical_top_values[:3])
        return f"top: {top}"
    return "—"


def _render_markdown(report: ProfilingReport) -> str:
    lines = [
        "# Data Profiling Report",
        "",
        f"- Source file: `{report.source_file}`",
        f"- Generated at: {report.generated_at.isoformat()}",
        f"- Total rows: {report.total_rows}",
        f"- Total columns: {report.total_columns}",
        f"- Unique claims (CLM_ID): {report.unique_claim_count}",
        f"- Unique beneficiaries (BENE_ID): {report.unique_beneficiary_count}",
        f"- Lines per claim: mean {report.lines_per_claim_mean:.2f}, median {report.lines_per_claim_median:.2f}",
        f"- Duplicate rows: {report.duplicate_row_count}",
        "",
        "## Columns",
        "",
        "| Column | Category | Dtype | Missing % | Cardinality | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for col in report.columns:
        lines.append(
            f"| {col.column_name} | {col.category.value} | {col.dtype_observed} | "
            f"{col.missing_pct:.2f} | {col.cardinality} | {_column_notes(col)} |"
        )
    lines.append("")
    return "\n".join(lines)
