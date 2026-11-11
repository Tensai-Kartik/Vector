import pytest
from app.utils.system_operator import AppLauncher, SystemOptimizer
from app.planner.mock_planner import MockPlanner

def test_app_launcher_matching():
    wa = AppLauncher.match_app("open whatsapp")
    assert wa is not None
    assert wa[0] == "whatsapp"
    assert wa[1]["name"] == "WhatsApp"
    assert "whatsapp:" in wa[1]["protocols"]

    epic = AppLauncher.match_app("open epic games home")
    assert epic is not None
    assert epic[0] == "epic games"
    assert epic[1]["name"] == "Epic Games Launcher"

    calc = AppLauncher.match_app("open calculator")
    assert calc is not None
    assert calc[0] == "calculator"

def test_system_optimizer_metrics():
    metrics = SystemOptimizer.get_system_metrics()
    assert "total_ram_gb" in metrics
    assert "used_ram_gb" in metrics
    assert metrics["total_ram_gb"] > 0
    assert metrics["ram_percent"] > 0

    procs = SystemOptimizer.get_top_memory_processes(limit=3)
    assert len(procs) > 0
    assert "name" in procs[0]
    assert "ram_mb" in procs[0]

@pytest.mark.asyncio
async def test_planner_app_launcher():
    planner = MockPlanner()
    plan_wa = await planner.create_plan("open whatsapp")
    assert len(plan_wa.steps) >= 1
    assert plan_wa.steps[0].action_type == "launch_app"
    assert plan_wa.steps[0].input_value == "whatsapp"

    plan_epic = await planner.create_plan("open epic games home")
    assert len(plan_epic.steps) >= 1
    assert plan_epic.steps[0].action_type == "launch_app"
    assert plan_epic.steps[0].input_value == "epic games"

@pytest.mark.asyncio
async def test_planner_pc_optimizer():
    planner = MockPlanner()
    plan_opt = await planner.create_plan("my pc is slow then clear extra ram stop unncecsarry processes")
    assert len(plan_opt.steps) >= 1
    assert plan_opt.steps[0].action_type == "system_command"
    assert plan_opt.steps[0].input_value == "optimize_pc"
    assert plan_opt.steps[0].verification_method == "command_success"


@pytest.mark.asyncio
async def test_app_launcher_verifies_local_install_before_web_fallback(monkeypatch):
    """When an app is not locally installed (or on cloud Render), check & fall back to browser URL."""
    monkeypatch.setenv("RENDER", "true")
    avail = AppLauncher.check_app_availability("open whatsapp")
    assert avail["installed_locally"] is False
    assert avail["mode"] == "web_fallback"
    assert avail["web_fallback"] == "https://web.whatsapp.com"

    launch_res = AppLauncher.launch("open whatsapp")
    assert launch_res["success"] is True
    assert launch_res["installed_locally"] is False
    assert launch_res["mode"] == "web_fallback"
    assert launch_res["web_url"] == "https://web.whatsapp.com"

    # Mocked desktop case: neither executable nor protocol handler registered on local PC
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setattr(AppLauncher, "find_local_executable", classmethod(lambda cls, *a, **kw: None))
    monkeypatch.setattr(AppLauncher, "is_protocol_registered", classmethod(lambda cls, proto: False))

    desktop_miss = AppLauncher.launch("open figma")
    assert desktop_miss["success"] is True
    assert desktop_miss["installed_locally"] is False
    assert desktop_miss["mode"] == "web_fallback"
    assert desktop_miss["web_url"] == "https://www.figma.com"

    # MockPlanner Scenario 7B appends step_2 navigate when not installed locally
    planner = MockPlanner()
    plan_wa = await planner.create_plan("open whatsapp")
    assert len(plan_wa.steps) == 2
    assert plan_wa.steps[0].action_type == "launch_app"
    assert plan_wa.steps[1].action_type == "navigate"
    assert plan_wa.steps[1].input_value == "https://web.whatsapp.com"
