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
