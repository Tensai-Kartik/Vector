import pytest
from types import SimpleNamespace

from app.config import Settings
from app.executor.anti_bot import detect_anti_bot_gate
from app.models.actions import ActionPlan, ActionStep
from app.models.mission import MissionCreateRequest
from app.orchestrator import MissionOrchestrator
from app.planner.mock_planner import MockPlanner
from app.verifier.outcome_verifier import OutcomeVerifier


def test_default_settings_deterministic_and_fast():
    """Verify deterministic planner is the default working model while gemini stays standby LLM."""
    s = Settings(_env_file=None)
    assert s.PLANNER_MODE == "deterministic"
    assert s.LLM_PROVIDER == "gemini"
    assert s.BROWSER_SLOWMO_MS == 0
    assert s.SCREENSHOT_STREAM_INTERVAL_MS >= 500


def test_orchestrator_uses_deterministic_even_when_gemini_configured(monkeypatch):
    """Having LLM_PROVIDER=gemini + API key keeps deterministic primary unless user selects gemini."""
    from app import orchestrator as orch_mod

    monkeypatch.setattr(orch_mod.settings, "PLANNER_MODE", "deterministic")
    monkeypatch.setattr(orch_mod.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(orch_mod.settings, "GEMINI_API_KEY", "test-api-key")

    default_cfg = MissionOrchestrator.resolve_planner_config(
        MissionCreateRequest(task="search wikipedia for python")
    )
    assert default_cfg["llm_ready"] is True
    assert default_cfg["use_gemini_primary"] is False

    override_cfg = MissionOrchestrator.resolve_planner_config(
        MissionCreateRequest(task="complex custom workflow", planner_mode="gemini")
    )
    assert override_cfg["use_gemini_primary"] is True


@pytest.mark.asyncio
async def test_orchestrator_falls_back_to_gemini_when_deterministic_step_fails(monkeypatch):
    """When deterministic planner fails a step at runtime and API key is set, Gemini recovers."""
    from app import orchestrator as orch_mod

    monkeypatch.setattr(orch_mod.settings, "PLANNER_MODE", "deterministic")
    monkeypatch.setattr(orch_mod.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(orch_mod.settings, "GEMINI_API_KEY", "test-api-key")
    monkeypatch.setattr(orch_mod.Database, "save_mission", lambda *_a, **_k: None)
    monkeypatch.setattr(orch_mod.Database, "save_event", lambda *_a, **_k: None)

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            self.page = SimpleNamespace(url="https://example.com")

        async def initialize(self):
            return None

        def stop_streaming(self):
            return None

        async def close(self):
            return None

        def bring_to_foreground(self):
            return None

        async def capture_frame(self):
            return None

        async def execute_step(self, step, **kwargs):
            if step.step_id == "step_1":
                return {
                    "success": False,
                    "status": "failed",
                    "error": "Selector '#broken' not found",
                    "verification": {"verified": False, "error": "Selector '#broken' not found"},
                }
            return {
                "success": True,
                "status": "completed",
                "verification": {"verified": True, "evidence": {"ok": True}},
                "result_data": {"success": True},
            }

    class BrokenDetPlanner:
        async def create_plan(self, task, allowed_domains=None, demo_mode=False):
            return ActionPlan(
                task=task,
                reasoning="deterministic attempt",
                allowed_domains=["example.com"],
                steps=[
                    ActionStep(step_id="step_1", action_type="click", intent="Broken det step", target_locator_value="#broken")
                ],
            )

    gemini_calls = {"replan": 0}

    class FakeGeminiPlanner:
        async def replan_on_failure(self, task, failed_step_id, failure_reason, current_page=None, allowed_domains=None):
            gemini_calls["replan"] += 1
            return ActionPlan(
                task=task,
                reasoning="gemini recovery",
                allowed_domains=["example.com"],
                steps=[
                    ActionStep(step_id="step_1", action_type="read_text", intent="Gemini recovered step", target_locator_value="h1")
                ],
            )

    monkeypatch.setattr(orch_mod, "PlaywrightExecutor", FakeExecutor)
    monkeypatch.setattr(orch_mod, "MockPlanner", BrokenDetPlanner)
    monkeypatch.setattr(orch_mod, "GeminiPlanner", FakeGeminiPlanner)

    async def no_dom_inspect(_page):
        return None

    monkeypatch.setattr(orch_mod.DOMInspector, "inspect_page", no_dom_inspect)

    orch = MissionOrchestrator()
    req = MissionCreateRequest(task="visit example.com and read heading", force_execution_method="browser")
    mission_id = "msn_test_rec"
    orch.active_missions[mission_id] = {
        "id": mission_id,
        "task": req.task,
        "status": "queued",
        "allowed_domains": ["example.com"],
        "require_approval_for_high_risk": False,
        "demo_mode": False,
        "steps": [],
        "events": [],
        "extracted_data": [],
        "artifacts": [],
        "approval_granted": False,
        "paused": False,
        "cancelled": False,
    }
    await orch.run_pipeline(mission_id, req)

    assert gemini_calls["replan"] == 1
    assert orch.active_missions[mission_id]["status"] == "completed"
    assert orch.active_missions[mission_id]["summary_report"]["verdict"] == "success"
    assert orch.active_missions[mission_id]["summary_report"]["replanning_count"] == 1


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


@pytest.mark.asyncio
async def test_play_media_from_downloads_without_windows_drives(monkeypatch):
    """Cloud Linux containers (no C:/D: drives or ~/Downloads) must not raise IndexError."""
    from app.utils.local_storage import LocalStorageManager

    monkeypatch.setattr(LocalStorageManager, "get_available_drives", staticmethod(lambda: []))
    monkeypatch.setattr(LocalStorageManager, "get_common_user_folders", staticmethod(lambda: {}))

    target_dir, label = LocalStorageManager.resolve_target_directory("play media from downloads")
    assert target_dir.exists()
    assert label

    plan = await MockPlanner().create_plan("play media from downloads", allowed_domains=["*"])
    assert len(plan.steps) >= 2
    nav_step = next(s for s in plan.steps if s.action_type == "navigate")
    assert (nav_step.input_value or "").startswith("file:")
