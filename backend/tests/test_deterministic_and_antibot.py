import pytest
from types import SimpleNamespace

from app.config import Settings
from app.executor.anti_bot import detect_anti_bot_gate
from app.models.actions import ActionStep
from app.planner.mock_planner import MockPlanner
from app.verifier.outcome_verifier import OutcomeVerifier


def test_default_settings_deterministic_and_fast():
    """Verify deterministic planner is default with zero Playwright slow-mo latency."""
    s = Settings(_env_file=None)
    assert s.LLM_PROVIDER == "deterministic"
    assert s.BROWSER_SLOWMO_MS == 0
    assert s.SCREENSHOT_STREAM_INTERVAL_MS >= 500


@pytest.mark.asyncio
async def test_youtube_latest_video_query_extraction():
    """Ensure natural-language prefixes like 'play latest video of ' are stripped from YouTube queries."""
    planner = MockPlanner()
    plan = await planner.create_plan("play latest video of tseries", allowed_domains=["*"])
    nav_step = plan.steps[0]
    assert nav_step.action_type == "navigate"
    assert "search_query=tseries" in (nav_step.input_value or "")
    assert "latest+video+of" not in (nav_step.input_value or "")
    assert plan.steps[1].timeout_ms == 6000
    assert plan.steps[3].timeout_ms == 6000


@pytest.mark.asyncio
async def test_general_autonomous_domain_and_search_planning():
    """Deterministic planner handles bare domains, portals, and generic web searches cleanly."""
    planner = MockPlanner()

    hn_plan = await planner.create_plan("check top posts on hacker news", allowed_domains=["*"])
    assert "news.ycombinator.com" in (hn_plan.steps[0].input_value or "")

    dom_plan = await planner.create_plan("open openai.com", allowed_domains=["*"])
    assert (dom_plan.steps[0].input_value or "").startswith("https://openai.com")

    ddg_plan = await planner.create_plan("search for fast playwright tips", allowed_domains=["*"])
    assert "duckduckgo.com/?q=" in (ddg_plan.steps[0].input_value or "")

    g_plan = await planner.create_plan("google playwright tips", allowed_domains=["*"])
    assert "google.com/search?q=" in (g_plan.steps[0].input_value or "")


@pytest.mark.asyncio
async def test_outcome_verifier_rejects_sorry_captcha_url_match():
    """Google /sorry/index?continue=...watch?v=... must fail fast instead of matching url_match."""
    gate_page = SimpleNamespace(
        url="https://www.google.com/sorry/index?continue=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DTfxs7tZFmv4"
    )
    step = ActionStep(
        step_id="step_3",
        action_type="click",
        intent="Click top video result",
        target_locator_value="a[href*='/watch?v=']",
        verification_method="url_match",
        verification_target="watch?v=, youtube.com/watch",
    )
    res = await OutcomeVerifier.verify_step_outcome(step=step, page=gate_page, execution_result={"success": True})
    assert res["verified"] is False
    assert res.get("captcha_blocked") is True
    assert res.get("evidence", {}).get("blocked") is True


@pytest.mark.asyncio
async def test_detect_anti_bot_gate_evaluate_hit():
    """detect_anti_bot_gate surfaces DOM CAPTCHA markers returned from page.evaluate."""
    async def fake_eval(_script):
        return 'Anti-bot gate phrase detected: "unusual traffic from your computer network"'

    dummy_page = SimpleNamespace(url="https://www.youtube.com/watch?v=123", evaluate=fake_eval)
    gate = await detect_anti_bot_gate(dummy_page)
    assert gate["blocked"] is True
    assert gate["kind"] == "captcha_challenge"
