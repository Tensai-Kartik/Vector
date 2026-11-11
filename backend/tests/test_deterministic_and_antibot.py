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
    assert plan.steps[1].timeout_ms == 12000
    assert plan.steps[1].verification_method == "element_present"
    assert plan.steps[2].timeout_ms == 12000
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

    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setattr(LocalStorageManager, "get_available_drives", staticmethod(lambda: []))
    monkeypatch.setattr(LocalStorageManager, "get_common_user_folders", staticmethod(lambda: {}))

    target_dir, label = LocalStorageManager.resolve_target_directory("play media from downloads")
    assert target_dir.exists()
    assert label

    plan = await MockPlanner().create_plan("play media from downloads", allowed_domains=["*"])
    assert len(plan.steps) >= 2
    nav_step = next(s for s in plan.steps if s.action_type == "navigate")
    assert (nav_step.input_value or "").startswith("file:")


@pytest.mark.asyncio
async def test_render_cloud_downloads_requests_local_media_picker(monkeypatch):
    """In Render cloud deployments, local folder requests prompt browser folder permission instead of opening Linux /root."""
    from app import orchestrator as orch_mod
    from app.guardrails.safety_gate import SafetyGate

    saved_events = []
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr(orch_mod.Database, "save_mission", lambda *_a, **_k: None)
    monkeypatch.setattr(orch_mod.Database, "save_event", lambda ev: saved_events.append(ev))

    plan = await MockPlanner().create_plan("play media from downloads", allowed_domains=["*"])
    assert len(plan.steps) == 1
    picker_step = plan.steps[0]
    assert picker_step.action_type == "request_clarification"
    assert picker_step.metadata.get("action_required") == "local_media_picker"

    validation = await SafetyGate.validate_action(
        step=picker_step,
        page=None,
        allowed_domains=["*"],
        demo_mode=False,
        approval_granted=True,
    )
    assert validation.can_proceed is True

    class FakePickerExecutor:
        def __init__(self, *args, **kwargs):
            self.page = SimpleNamespace(url="about:blank")

        async def initialize(self):
            return None

        def stop_streaming(self):
            return None

        async def close(self):
            return None

        def bring_to_foreground(self):
            return None

        async def execute_step(self, step, **kwargs):
            return {
                "success": True,
                "status": "completed",
                "verification": {"verified": True, "strategy": "none"},
                "result_data": {"success": True, **dict(step.metadata or {})},
            }

    monkeypatch.setattr(orch_mod, "PlaywrightExecutor", FakePickerExecutor)
    orch = orch_mod.MissionOrchestrator()
    req = MissionCreateRequest(task="play media from downloads", force_execution_method="browser")
    mission_id = "msn_test_local_picker"
    orch.active_missions[mission_id] = {
        "id": mission_id,
        "task": req.task,
        "status": "queued",
        "allowed_domains": ["*"],
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

    m = orch.active_missions[mission_id]
    assert m["status"] == "needs_input"
    assert m.get("needs_input_action") == "local_media_picker"
    assert any(
        ev.get("event_type") == "needs_input" and (ev.get("details") or {}).get("action_required") == "local_media_picker"
        for ev in saved_events
    )


@pytest.mark.asyncio
async def test_detect_anti_bot_gate_youtube_signin_marker():
    """YouTube's datacenter 'Sign in to confirm you're not a bot' gate is classified as anti-bot challenge."""
    async def fake_eval(_script):
        return 'Anti-bot gate phrase detected: "sign in to confirm you\'re not a bot"'

    dummy_page = SimpleNamespace(url="https://www.youtube.com/watch?v=abc", evaluate=fake_eval)
    gate = await detect_anti_bot_gate(dummy_page)
    assert gate["blocked"] is True
    assert gate["kind"] == "captcha_challenge"


@pytest.mark.asyncio
async def test_orchestrator_handles_safety_gate_rejection_captcha_and_recovery(monkeypatch):
    """SafetyGate rejection transitions to needs_input when CAPTCHA-gated, or recovers via Gemini when non-CAPTCHA."""
    from app import orchestrator as orch_mod

    monkeypatch.setattr(orch_mod.settings, "PLANNER_MODE", "deterministic")
    monkeypatch.setattr(orch_mod.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(orch_mod.settings, "GEMINI_API_KEY", "test-api-key")
    monkeypatch.setattr(orch_mod.Database, "save_mission", lambda *_a, **_k: None)
    monkeypatch.setattr(orch_mod.Database, "save_event", lambda *_a, **_k: None)

    class SingleStepDetPlanner:
        async def create_plan(self, task, allowed_domains=None, demo_mode=False):
            return ActionPlan(
                task=task,
                reasoning="deterministic attempt",
                allowed_domains=["youtube.com"],
                steps=[
                    ActionStep(step_id="step_1", action_type="click", intent="Click top video", target_locator_value="a#video-title")
                ],
            )

    class RecoveryGeminiPlanner:
        async def replan_on_failure(self, task, failed_step_id, failure_reason, current_page=None, allowed_domains=None):
            return ActionPlan(
                task=task,
                reasoning="gemini fallback selector",
                allowed_domains=["youtube.com"],
                steps=[
                    ActionStep(step_id="rec_1", action_type="read_text", intent="Recovered read", target_locator_value="h1")
                ],
            )

    async def no_dom_inspect(_page):
        return None

    monkeypatch.setattr(orch_mod, "MockPlanner", SingleStepDetPlanner)
    monkeypatch.setattr(orch_mod, "GeminiPlanner", RecoveryGeminiPlanner)
    monkeypatch.setattr(orch_mod.DOMInspector, "inspect_page", no_dom_inspect)

    # Case 1: CAPTCHA-gated rejection -> needs_input
    class CaptchaRejectedExecutor:
        def __init__(self, *args, **kwargs):
            self.page = SimpleNamespace(url="https://www.youtube.com/results?search_query=notyourtype")

        async def initialize(self): return None
        def stop_streaming(self): return None
        async def close(self): return None
        def bring_to_foreground(self): return None
        async def capture_frame(self): return None

        async def execute_step(self, step, **kwargs):
            return {
                "success": False,
                "status": "rejected",
                "requires_approval": False,
                "requires_replanning": True,
                "captcha_blocked": True,
                "anti_bot_gate": {"blocked": True, "kind": "captcha_challenge", "reason": "Sign in to confirm you're not a bot"},
                "error": "Target site displayed anti-bot verification gate.",
                "validation": {"can_proceed": False, "requires_replanning": True},
            }

    monkeypatch.setattr(orch_mod, "PlaywrightExecutor", CaptchaRejectedExecutor)
    orch = orch_mod.MissionOrchestrator()
    req = MissionCreateRequest(task="play latest video of notyourtype", force_execution_method="browser")
    orch.active_missions["msn_cap_rej"] = {
        "id": "msn_cap_rej", "task": req.task, "status": "queued", "allowed_domains": ["youtube.com"],
        "require_approval_for_high_risk": False, "demo_mode": False, "steps": [], "events": [],
        "extracted_data": [], "artifacts": [], "approval_granted": False, "paused": False, "cancelled": False,
    }
    await orch.run_pipeline("msn_cap_rej", req)
    assert orch.active_missions["msn_cap_rej"]["status"] == "needs_input"
    assert orch.active_missions["msn_cap_rej"]["captcha_blocked"] is True

    # Case 2: Non-CAPTCHA element-missing rejection -> Gemini recovery completes mission
    class RecoverableRejectedExecutor:
        def __init__(self, *args, **kwargs):
            self.page = SimpleNamespace(url="https://www.youtube.com/results?search_query=notyourtype")

        async def initialize(self): return None
        def stop_streaming(self): return None
        async def close(self): return None
        def bring_to_foreground(self): return None
        async def capture_frame(self): return None

        async def execute_step(self, step, **kwargs):
            if step.step_id == "step_1":
                return {
                    "success": False,
                    "status": "rejected",
                    "requires_approval": False,
                    "requires_replanning": True,
                    "captcha_blocked": False,
                    "anti_bot_gate": {"blocked": False},
                    "error": "Target element 'a#video-title' does not exist on the current page.",
                    "validation": {"can_proceed": False, "requires_replanning": True},
                }
            return {
                "success": True,
                "status": "completed",
                "verification": {"verified": True, "evidence": {"ok": True}},
                "result_data": {"success": True},
            }

    monkeypatch.setattr(orch_mod, "PlaywrightExecutor", RecoverableRejectedExecutor)
    orch2 = orch_mod.MissionOrchestrator()
    orch2.active_missions["msn_rec_rej"] = {
        "id": "msn_rec_rej", "task": req.task, "status": "queued", "allowed_domains": ["youtube.com"],
        "require_approval_for_high_risk": False, "demo_mode": False, "steps": [], "events": [],
        "extracted_data": [], "artifacts": [], "approval_granted": False, "paused": False, "cancelled": False,
    }
    await orch2.run_pipeline("msn_rec_rej", req)
    assert orch2.active_missions["msn_rec_rej"]["status"] == "completed"
    assert orch2.active_missions["msn_rec_rej"]["summary_report"]["replanning_count"] == 1


def test_youtube_resolver_extract_and_parse():
    """Verify lightweight YouTube query cleanup and organic/shorts/sorry HTML parsing."""
    from app.utils.youtube_resolver import extract_youtube_query, parse_youtube_search_html

    assert extract_youtube_query("play latest video of notyourtype in new chrome tab") == "notyourtype"
    assert extract_youtube_query("watch latest video of carryminati") == "carryminati"

    organic_html = (
        '{"videoRenderer":{"videoId":"dQw4w9WgXcQ","title":{"runs":[{"text":"Sample Video Title"}]}}}'
    )
    parsed = parse_youtube_search_html(organic_html)
    assert parsed is not None
    assert parsed["video_id"] == "dQw4w9WgXcQ"
    assert parsed["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert parsed["title"] == "Sample Video Title"

    shorts_html = '{"reelWatchEndpoint":{"videoId":"abc123XYZ90"}}'
    parsed_short = parse_youtube_search_html(shorts_html)
    assert parsed_short is not None
    assert parsed_short["url"] == "https://www.youtube.com/shorts/abc123XYZ90"

    blocked_html = "<html><body>Our systems have detected unusual traffic /sorry/index</body></html>"
    assert parse_youtube_search_html(blocked_html) is None


@pytest.mark.asyncio
async def test_render_cloud_downloads_picker_no_home_dir_and_no_duplicate_needs_input(monkeypatch):
    """Render 'play media from downloads' infers Downloads (not Home Directory) and emits needs_input once."""
    from app import orchestrator as orch_mod

    monkeypatch.setenv("RENDER", "true")
    saved_events = []
    monkeypatch.setattr(orch_mod.Database, "save_mission", lambda *args, **kwargs: None)
    monkeypatch.setattr(orch_mod.Database, "save_event", lambda ev: saved_events.append(ev))

    planner = MockPlanner()
    plan = await planner.create_plan("play media from downloads")
    assert len(plan.steps) == 1
    assert plan.steps[0].action_type == "request_clarification"
    assert "Downloads" in plan.steps[0].intent
    assert "Home Directory" not in plan.steps[0].intent

    class DummyExecutor:
        def __init__(self, *args, **kwargs):
            self.page = SimpleNamespace(url="about:blank")

        async def initialize(self): return None
        def stop_streaming(self): return None
        async def close(self): return None
        def bring_to_foreground(self): return None
        async def capture_frame(self): return None

        async def execute_step(self, step, **kwargs):
            return {
                "success": True,
                "status": "completed",
                "verification": {"verified": True, "evidence": {"note": "needs local folder picker"}},
                "result_data": {
                    "success": True,
                    **dict(step.metadata or {}),
                },
            }

    monkeypatch.setattr(orch_mod, "PlaywrightExecutor", DummyExecutor)
    orch = orch_mod.MissionOrchestrator()
    req = MissionCreateRequest(task="play media from downloads", force_execution_method="browser")
    orch.active_missions["msn_dl_once"] = {
        "id": "msn_dl_once", "task": req.task, "status": "queued", "allowed_domains": ["*"],
        "require_approval_for_high_risk": False, "demo_mode": False, "steps": [], "events": [],
        "extracted_data": [], "artifacts": [], "approval_granted": False, "paused": False, "cancelled": False,
    }
    await orch.run_pipeline("msn_dl_once", req)
    mission = orch.active_missions["msn_dl_once"]
    assert mission["status"] == "needs_input"
    assert mission["needs_input_action"] == "local_media_picker"
    assert "Downloads" in mission["needs_input_reason"]
    assert "Home Directory" not in mission["needs_input_reason"]
    needs_input_events = [e for e in saved_events if e.get("event_type") == "needs_input"]
    assert len(needs_input_events) == 1


@pytest.mark.asyncio
async def test_resolve_launch_target_routes_correctly(monkeypatch):
    """Verify /api/resolve-launch skips local folders, resolves YT video URLs, and falls back for missing apps."""
    from app.api import routes as routes_mod

    dl_res = await routes_mod.resolve_launch_target({"task": "play media from downloads"})
    assert dl_res["should_open_tab"] is False

    vid_res = await routes_mod.resolve_launch_target({"task": "play latest video from my videos"})
    assert vid_res["should_open_tab"] is False

    monkeypatch.setenv("RENDER", "true")
    wa_res = await routes_mod.resolve_launch_target({"task": "open whatsapp"})
    assert wa_res["should_open_tab"] is True
    assert wa_res["kind"] == "app_web_fallback"
    assert wa_res["launch_url"] == "https://web.whatsapp.com"
    assert wa_res["installed_locally"] is False

    async def fake_yt_resolve(query: str, timeout: float = 5.0):
        return {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": f"Top Result for {query}",
            "video_id": "dQw4w9WgXcQ",
            "resolved_direct": True,
        }

    monkeypatch.setattr(routes_mod, "resolve_youtube_top_video", fake_yt_resolve)
    yt_res = await routes_mod.resolve_launch_target({"task": "play latest video of notyourtype"})
    assert yt_res["should_open_tab"] is True
    assert yt_res["direct_tab_sufficient"] is True
    assert yt_res["kind"] == "youtube_video"
    assert yt_res["launch_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_orchestrator_client_handled_url_fast_path(monkeypatch):
    """Verify client_handled_url completes mission without launching server Chromium."""
    from app import orchestrator as orch_mod

    monkeypatch.setattr(orch_mod.Database, "save_mission", lambda *args, **kwargs: None)
    monkeypatch.setattr(orch_mod.Database, "save_event", lambda *args, **kwargs: None)

    def fail_if_playwright_launched(*args, **kwargs):
        raise AssertionError("PlaywrightExecutor should not launch when client_handled_url is supplied")

    monkeypatch.setattr(orch_mod, "PlaywrightExecutor", fail_if_playwright_launched)

    orch = orch_mod.MissionOrchestrator()
    target_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    req = MissionCreateRequest(task="play latest video of notyourtype", client_handled_url=target_url)
    orch.active_missions["msn_chrome_tab"] = {
        "id": "msn_chrome_tab", "task": req.task, "status": "queued", "allowed_domains": ["youtube.com"],
        "require_approval_for_high_risk": False, "demo_mode": False, "steps": [], "events": [],
        "extracted_data": [], "artifacts": [], "approval_granted": False, "paused": False, "cancelled": False,
    }
    await orch.run_pipeline("msn_chrome_tab", req)
    mission = orch.active_missions["msn_chrome_tab"]
    assert mission["status"] == "completed"
    assert mission["current_url"] == target_url
    assert mission["summary_report"]["verdict"] == "success"
    assert mission["summary_report"]["is_verified"] is True

    # Also verify local:// authorized-folder auto-play fast-path wording
    local_url = "local://Videos/sample.mp4"
    req_local = MissionCreateRequest(task="play media from videos", client_handled_url=local_url)
    orch.active_missions["msn_local_auto"] = {
        "id": "msn_local_auto", "task": req_local.task, "status": "queued", "allowed_domains": ["*"],
        "require_approval_for_high_risk": False, "demo_mode": False, "steps": [], "events": [],
        "extracted_data": [], "artifacts": [], "approval_granted": False, "paused": False, "cancelled": False,
    }
    await orch.run_pipeline("msn_local_auto", req_local)
    local_mission = orch.active_missions["msn_local_auto"]
    assert local_mission["status"] == "completed"
    assert local_mission["current_url"] == local_url
    assert "authorized folder" in local_mission["summary_report"]["verification_summary"].lower()
