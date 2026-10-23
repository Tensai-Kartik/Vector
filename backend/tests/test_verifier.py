import pytest
from pathlib import Path
import tempfile
from app.verifier.outcome_verifier import OutcomeVerifier
from app.models.actions import ActionStep

@pytest.mark.asyncio
async def test_file_download_verifier_valid_file(tmp_path):
    test_file = tmp_path / "valid_invoice.csv"
    test_file.write_text("id,amount\nINV-001,$5000\n", encoding="utf-8")

    step = ActionStep(
        step_id="step_dl",
        action_type="download_file",
        intent="Download file",
        verification_method="file_downloaded"
    )

    res = await OutcomeVerifier.verify_step_outcome(
        step=step,
        page=None,
        artifact_path=test_file
    )
    assert res["verified"] is True
    assert res["evidence"]["filename"] == "valid_invoice.csv"
    assert res["evidence"]["size_bytes"] > 0
    assert len(res["evidence"]["sha256"]) == 64

@pytest.mark.asyncio
async def test_file_download_verifier_rejects_empty_file(tmp_path):
    empty_file = tmp_path / "empty_corrupt.csv"
    empty_file.write_text("", encoding="utf-8")

    step = ActionStep(
        step_id="step_dl_empty",
        action_type="download_file",
        intent="Download file",
        verification_method="file_downloaded"
    )

    res = await OutcomeVerifier.verify_step_outcome(
        step=step,
        page=None,
        artifact_path=empty_file
    )
    assert res["verified"] is False
    assert "0 bytes" in res["evidence"]["error"]

@pytest.mark.asyncio
async def test_record_count_verifier():
    step = ActionStep(
        step_id="step_rec",
        action_type="extract_records",
        intent="Extract 5 items",
        verification_method="record_count",
        verification_target="5"
    )

    # Passing case (5 records)
    res_pass = await OutcomeVerifier.verify_step_outcome(
        step=step,
        page=None,
        execution_result={"records": [{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}, {"a": 5}]}
    )
    assert res_pass["verified"] is True

    # Failing case (3 records < 5)
    res_fail = await OutcomeVerifier.verify_step_outcome(
        step=step,
        page=None,
        execution_result={"records": [{"a": 1}, {"a": 2}, {"a": 3}]}
    )
    assert res_fail["verified"] is False

@pytest.mark.asyncio
async def test_url_match_unquoted_verifier():
    class DummyPage:
        url = "file:///C:/Users/Kartik/Downloads/16_11_2025%2C%2011_53_34%20am%20-%20Webcam.webm"
    
    step = ActionStep(
        step_id="step_match",
        action_type="navigate",
        intent="Check media url",
        verification_method="url_match",
        verification_target="16_11_2025,"
    )
    res = await OutcomeVerifier.verify_step_outcome(step=step, page=DummyPage())
    assert res["verified"] is True

@pytest.mark.asyncio
async def test_downloads_planner_typo_resilience():
    from app.planner.mock_planner import MockPlanner
    planner = MockPlanner()
    plan = await planner.create_plan("opwn downloads and play first media")
    assert len(plan.steps) >= 3
    assert any("downloads" in str(s.input_value).lower() for s in plan.steps if s.input_value)
    assert any(s.action_type == "launch_app" for s in plan.steps)

