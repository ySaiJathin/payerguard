import pytest

from app.llm.errors import MalformedResponseError
from app.llm.response_parser import validate_and_tag
from tests.llm._fixtures import make_draft


def test_complete_draft_passes_with_all_six_sections_intact():
    draft = make_draft()
    validated, insufficient = validate_and_tag(draft)

    for field in (
        "summary",
        "likely_root_cause",
        "evidence",
        "business_impact_narrative",
        "recommended_fix",
        "prevention_recommendation",
    ):
        value = getattr(validated, field)
        assert isinstance(value, str)
        assert value.strip()
    assert insufficient is False


@pytest.mark.parametrize(
    "empty_field",
    ["summary", "likely_root_cause", "evidence", "business_impact_narrative", "recommended_fix", "prevention_recommendation"],
)
def test_any_empty_section_raises_malformed_response_error(empty_field):
    draft = make_draft()
    draft = draft.model_copy(update={empty_field: "   "})  # whitespace-only

    with pytest.raises(MalformedResponseError):
        validate_and_tag(draft)
