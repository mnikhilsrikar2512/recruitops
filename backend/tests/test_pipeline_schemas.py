from app.schemas.pipeline import PipelineBoardFilters, PipelineStageMove


def test_pipeline_board_filters_normalize_stage() -> None:
    filters = PipelineBoardFilters(stage=" shortlisted ")
    assert filters.stage == "shortlisted"


def test_pipeline_stage_move_normalizes_text() -> None:
    payload = PipelineStageMove(
        to_stage=" client-round ",
        notes=" follow up ",
        rejection_reason=" not fit ",
    )
    assert payload.to_stage == "client-round"
    assert payload.notes == "follow up"
    assert payload.rejection_reason == "not fit"


def test_pipeline_stage_move_normalizes_blank_optional_text_to_none() -> None:
    payload = PipelineStageMove(
        to_stage=" joined ",
        notes="   ",
        rejection_reason="   ",
    )

    assert payload.notes is None
    assert payload.rejection_reason is None
