"""Persists FeatureDropDecision[] and the final SelectedFeatureSet as
data/features/feature_drop_decisions.json and
data/features/selected_feature_set.json (spec FR-009).

Each write overwrites the prior file, mirroring Phase 3/5's `*_log.py`
precedent, so re-running selection on an unmodified batch produces
identical persisted files, not accumulating ones.
"""

import json
from pathlib import Path

from app.data_engineering.paths import features_dir
from app.features.selection.schemas import FeatureDropDecision, SelectedFeatureSet

DROP_DECISIONS_FILENAME = "feature_drop_decisions.json"
SELECTED_FEATURE_SET_FILENAME = "selected_feature_set.json"


def _decisions_path(out_dir: Path | None = None) -> Path:
    return (out_dir or features_dir()) / DROP_DECISIONS_FILENAME


def write_drop_decisions(decisions: list[FeatureDropDecision], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or features_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _decisions_path(out_dir)
    payload = [json.loads(d.model_dump_json()) for d in decisions]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_drop_decisions(stage: int | None = None, out_dir: Path | None = None) -> list[FeatureDropDecision]:
    path = _decisions_path(out_dir)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    decisions = [FeatureDropDecision.model_validate(row) for row in payload]
    if stage is not None:
        decisions = [d for d in decisions if d.stage == stage]
    return decisions


def _selected_feature_set_path(out_dir: Path | None = None) -> Path:
    return (out_dir or features_dir()) / SELECTED_FEATURE_SET_FILENAME


def write_selected_feature_set(feature_set: SelectedFeatureSet, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or features_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _selected_feature_set_path(out_dir)
    path.write_text(feature_set.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_selected_feature_set(out_dir: Path | None = None) -> SelectedFeatureSet | None:
    path = _selected_feature_set_path(out_dir)
    if not path.exists():
        return None
    return SelectedFeatureSet.model_validate(json.loads(path.read_text(encoding="utf-8")))
