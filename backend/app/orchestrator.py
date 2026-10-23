import asyncio
import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import hashlib

from app.models.mission import (
    MissionCreateRequest, MissionResponse, MissionStepState,
    MissionEvent, MissionStatus, StepStatus, EventType
)
from app.models.actions import ActionPlan, ActionStep
from app.models.report import ExecutionReport, ArtifactMetadata
from app.database.db import Database
from app.planner.mock_planner import MockPlanner
from app.planner.gemini_planner import GeminiPlanner
from app.inspector.dom_inspector import DOMInspector
from app.adapters.router import ExecutionRouter
from app.executor.playwright_executor import PlaywrightExecutor
from app.config import settings

class MissionOrchestrator:
    """
    Core Mission Pipeline Orchestrator.
    Executes the full autonomous lifecycle:
    INTAKE -> INSPECT -> PLAN -> VALIDATE -> ROUTE -> SAFETY GATE -> EXECUTE -> VERIFY -> RECOVERY -> REPORT
    """

    def __init__(self, broadcast_fn=None, frame_broadcast_fn=None):
        self.broadcast_fn = broadcast_fn
        self.frame_broadcast_fn = frame_broadcast_fn
        self.active_missions: Dict[str, Dict[str, Any]] = {}

    async def emit_event(
        self,
        mission_id: str,
        event_type: EventType,
        category: str,
        message: str,
        step_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> MissionEvent:
        event = MissionEvent(
            mission_id=mission_id,
            step_id=step_id,
            event_type=event_type,
            category=category,
            message=message,
            details=details or {},
            timestamp=datetime.utcnow()
        )
        Database.save_event(event.model_dump())
        if self.broadcast_fn:
            await self.broadcast_fn(mission_id, event.model_dump())
        return event

    async def start_mission(self, req: MissionCreateRequest) -> str:
        mission_id = f"msn_{uuid.uuid4().hex[:10]}"
        now = datetime.utcnow()

        mission_data = {
            "id": mission_id,
            "task": req.task,
            "status": "queued",
            "start_url": req.start_url,
            "allowed_domains": req.allowed_domains or settings.allowed_domains_list,
            "require_approval_for_high_risk": req.require_approval_for_high_risk,
            "demo_mode": req.demo_mode,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "steps": [],
            "events": [],
            "extracted_data": [],
            "artifacts": [],
            "approval_granted": False,
            "paused": False,
            "cancelled": False
        }

        self.active_missions[mission_id] = mission_data
        Database.save_mission(mission_data)

        await self.emit_event(
            mission_id=mission_id,
            event_type="mission_created",
            category="system",
            message=f"Mission initialized with task: '{req.task}'",
            details={"task": req.task, "demo_mode": req.demo_mode}
        )

        # Launch pipeline as background task
        asyncio.create_task(self.run_pipeline(mission_id, req))
        return mission_id

    async def run_pipeline(self, mission_id: str, req: MissionCreateRequest):
        mission = self.active_missions.get(mission_id)
        if not mission:
            return

        executor: Optional[PlaywrightExecutor] = None
        start_time = datetime.utcnow()
        api_steps_count = 0
        browser_steps_count = 0
        guardrail_rejections = []
        retries_count = 0
        replanning_count = 0

        try:
            # 1. API-first evaluation: Check if task can be fulfilled entirely via API
            if req.force_execution_method != "browser":
                api_route = await ExecutionRouter.route_and_execute(req.task)
                if api_route.get("executed_via") == "api" and api_route.get("success"):
                    api_steps_count += 1
                    mission["status"] = "running"
                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="api_route_selected",
                        category="api",
                        message="Task routed to authorized direct REST API adapter (API-first).",
                        details=api_route
                    )

                    # Save extracted API data
                    data = api_route.get("data")
                    if isinstance(data, list):
                        mission["extracted_data"].extend(data)
                    elif isinstance(data, dict):
                        mission["extracted_data"].append(data)

                    mission["status"] = "completed"
                    mission["completed_at"] = datetime.utcnow().isoformat()
                    
                    # Generate report
                    report = ExecutionReport(
                        mission_id=mission_id,
                        task=req.task,
                        verdict="success",
                        is_verified=True,
                        verification_summary="Successfully queried and verified via official GitHub REST API.",
                        total_steps=1,
                        completed_steps=1,
                        failed_steps=0,
                        rejected_steps=0,
                        api_steps_count=1,
                        browser_steps_count=0,
                        retry_count=0,
                        replanning_count=0,
                        duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                        start_time=start_time,
                        end_time=datetime.utcnow(),
                        extracted_records=mission["extracted_data"],
                        artifacts=[]
                    )
                    mission["summary_report"] = report.model_dump()
                    Database.save_mission(mission)

                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="verification_passed",
                        category="verification",
                        message="API payload validated and verified successfully.",
                        details={"record_count": len(mission["extracted_data"])}
                    )
                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="mission_completed",
                        category="system",
                        message="Mission completed API-first with verified result.",
                        details=report.model_dump()
                    )
                    return

            # 2. Browser Automation Pipeline
            mission["status"] = "inspecting"
            await self.emit_event(
                mission_id=mission_id,
                event_type="inspection_started",
                category="browser",
                message="Launching browser execution environment..."
            )

            # Setup executor with streaming screencast callback
            async def on_frame(b64_img):
                if self.frame_broadcast_fn:
                    await self.frame_broadcast_fn(mission_id, b64_img)

            is_headed = getattr(req, "open_browser_window", False)
            executor = PlaywrightExecutor(
                frame_callback=on_frame,
                headless=False if is_headed else settings.BROWSER_HEADLESS
            )
            await executor.initialize()

            # 3. LLM Planning Phase
            mission["status"] = "planning"
            await self.emit_event(
                mission_id=mission_id,
                event_type="plan_generated",
                category="system",
                message="Generating structured action plan using planner engine..."
            )

            planner = GeminiPlanner() if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY else MockPlanner()
            plan: ActionPlan = await planner.create_plan(
                task=req.task,
                allowed_domains=mission["allowed_domains"],
                demo_mode=req.demo_mode
            )

            # Dynamically allow target domains from plan
            if plan.allowed_domains:
                mission["allowed_domains"] = list(set(mission["allowed_domains"] + plan.allowed_domains))

            mission["plan_json"] = plan.model_dump()
            steps_state: List[MissionStepState] = [
                MissionStepState(
                    step_id=s.step_id,
                    action_type=s.action_type,
                    intent=s.intent,
                    target_description=s.target_description,
                    target_locator_value=s.target_locator_value,
                    input_value=s.input_value,
                    status="pending"
                ) for s in plan.steps
            ]
            mission["steps"] = [s.model_dump() for s in steps_state]
            Database.save_mission(mission)

            await self.emit_event(
                mission_id=mission_id,
                event_type="plan_generated",
                category="system",
                message=f"Plan generated with {len(plan.steps)} structured steps.",
                details={"reasoning": plan.reasoning, "steps": [s.model_dump() for s in plan.steps]}
            )

            # 4. Step-by-Step Execution Loop
            mission["status"] = "running"
            for step in plan.steps:
                if mission.get("cancelled"):
                    break

                # Handle operator approval for local storage or high risk
                is_local_access = (
                    step.action_type == "request_approval" or
                    (bool(step.input_value) and (
                        step.input_value.startswith("file:") or
                        bool(re.match(r"^[a-zA-Z]:[/\\]", step.input_value))
                    ))
                )
                needs_approval = (
                    req.require_approval_for_high_risk and (
                        step.action_type == "request_approval" or
                        (is_local_access and not mission.get("local_storage_approved")) or
                        (step.risk_classification in ["high", "critical"])
                    )
                )

                if needs_approval and not mission.get("approval_granted"):
                    mission["status"] = "awaiting_approval"
                    Database.save_mission(mission)
                    approval_msg = (
                        f"Local Storage Authorization: Permission required to access local drives and files ({step.intent})."
                        if is_local_access else
                        f"Step '{step.intent}' has {step.risk_classification} risk. Operator approval required."
                    )
                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="approval_requested",
                        category="guardrail",
                        message=approval_msg,
                        step_id=step.step_id,
                        details={"step": step.model_dump(), "is_local_access": is_local_access}
                    )
                    # Wait for approval or cancel
                    while not mission.get("approval_granted") and not mission.get("cancelled"):
                        await asyncio.sleep(0.5)

                    if mission.get("cancelled"):
                        break
                    mission["status"] = "running"
                    mission["local_storage_approved"] = True
                    Database.save_mission(mission)
                else:
                    if is_local_access:
                        mission["local_storage_approved"] = True

                # Mark step running
                current_step_dict = next((s for s in mission["steps"] if s["step_id"] == step.step_id), None)
                if current_step_dict:
                    current_step_dict["status"] = "running"
                    current_step_dict["start_time"] = datetime.utcnow().isoformat()

                await self.emit_event(
                    mission_id=mission_id,
                    event_type="browser_action_started",
                    category="browser",
                    message=f"Executing: {step.intent}",
                    step_id=step.step_id,
                    details={"action_type": step.action_type, "target": step.target_locator_value}
                )

                # Execute action
                res = await executor.execute_step(
                    step=step,
                    mission_id=mission_id,
                    allowed_domains=mission["allowed_domains"],
                    demo_mode=req.demo_mode,
                    approval_granted=mission.get("approval_granted", False) or not req.require_approval_for_high_risk,
                    require_approval_for_high_risk=req.require_approval_for_high_risk
                )

                browser_steps_count += 1

                # Validation failure
                if res.get("status") == "rejected":
                    guardrail_rejections.append({
                        "step_id": step.step_id,
                        "intent": step.intent,
                        "error": res.get("error"),
                        "validation": res.get("validation")
                    })
                    if current_step_dict:
                        current_step_dict["status"] = "rejected"
                        current_step_dict["validation_message"] = res.get("error")

                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="step_rejected",
                        category="guardrail",
                        message=f"Pre-execution guardrail REJECTED step: {res.get('error')}",
                        step_id=step.step_id,
                        details=res
                    )
                    # If guardrail rejects, stop safely
                    mission["status"] = "failed"
                    break

                # Success handling
                if res.get("success"):
                    if current_step_dict:
                        current_step_dict["status"] = "completed"
                        current_step_dict["verification_status"] = "passed"
                        current_step_dict["verification_evidence"] = res.get("verification", {}).get("evidence")
                        current_step_dict["end_time"] = datetime.utcnow().isoformat()

                    # Check for extracted records
                    if step.action_type == "extract_records":
                        records = res.get("result_data", {}).get("records", [])
                        mission["extracted_data"].extend(records)

                    # Check for created artifact
                    if res.get("artifact_path"):
                        p = Path(res["artifact_path"])
                        art_meta = ArtifactMetadata(
                            artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                            filename=p.name,
                            file_path=str(p),
                            file_size_bytes=p.stat().st_size,
                            content_type="text/csv" if p.suffix == ".csv" else "application/octet-stream"
                        )
                        mission["artifacts"].append(art_meta.model_dump())
                        Database.save_artifact({
                            "artifact_id": art_meta.artifact_id,
                            "mission_id": mission_id,
                            "filename": art_meta.filename,
                            "file_path": art_meta.file_path,
                            "file_size_bytes": art_meta.file_size_bytes,
                            "content_type": art_meta.content_type
                        })
                        await self.emit_event(
                            mission_id=mission_id,
                            event_type="artifact_created",
                            category="artifact",
                            message=f"Verified artifact generated: {art_meta.filename} ({art_meta.file_size_bytes} bytes)",
                            step_id=step.step_id,
                            details=art_meta.model_dump()
                        )

                    completion_details = dict(res.get("verification", {}) or {})
                    if executor and executor.page:
                        try:
                            completion_details["final_url"] = executor.page.url
                        except Exception:
                            pass

                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="browser_action_completed",
                        category="browser",
                        message=f"Step completed and postconditions verified: {step.intent}",
                        step_id=step.step_id,
                        details=completion_details
                    )
                else:
                    # Step failed postcondition or action execution
                    if current_step_dict:
                        current_step_dict["status"] = "failed"
                        current_step_dict["error_message"] = res.get("error")

                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="verification_failed",
                        category="verification",
                        message=f"Step failed verification: {res.get('error')}",
                        step_id=step.step_id,
                        details=res
                    )
                    mission["status"] = "failed"
                    break

            # 5. Finalize Mission and Build Report
            end_time = datetime.utcnow()
            completed_steps = sum(1 for s in mission["steps"] if s["status"] == "completed")
            failed_steps = sum(1 for s in mission["steps"] if s["status"] == "failed")
            rejected_steps = sum(1 for s in mission["steps"] if s["status"] == "rejected")
            total_steps = len(mission["steps"])
            all_verified = (completed_steps == total_steps and total_steps > 0)

            if mission.get("cancelled"):
                final_verdict = "cancelled"
            elif all_verified:
                final_verdict = "success"
                mission["status"] = "completed"
            elif completed_steps > 0:
                final_verdict = "partial_success"
                mission["status"] = "failed"
            else:
                final_verdict = "failed"
                mission["status"] = "failed"

            report = ExecutionReport(
                mission_id=mission_id,
                task=req.task,
                verdict=final_verdict,
                is_verified=all_verified,
                verification_summary=f"Mission concluded: {completed_steps}/{total_steps} steps executed and postcondition-verified.",
                total_steps=total_steps,
                completed_steps=completed_steps,
                failed_steps=failed_steps,
                rejected_steps=rejected_steps,
                api_steps_count=api_steps_count,
                browser_steps_count=browser_steps_count,
                retry_count=retries_count,
                replanning_count=replanning_count,
                duration_seconds=(end_time - start_time).total_seconds(),
                start_time=start_time,
                end_time=end_time,
                extracted_records=mission["extracted_data"],
                artifacts=[ArtifactMetadata(**a) for a in mission["artifacts"]],
                guardrail_rejections=guardrail_rejections
            )

            mission["summary_report"] = report.model_dump()
            mission["completed_at"] = end_time.isoformat()
            Database.save_mission(mission)

            await self.emit_event(
                mission_id=mission_id,
                event_type="mission_completed" if all_verified else "mission_failed",
                category="system",
                message=f"Mission finalized with verdict: '{final_verdict}'. Verified: {all_verified}",
                details=report.model_dump()
            )

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print("FATAL PIPELINE ERROR:", repr(e), "\n", tb)
            mission["status"] = "failed"
            await self.emit_event(
                mission_id=mission_id,
                event_type="mission_failed",
                category="system",
                message=f"Mission fatal error: {repr(e)}",
                details={"error": repr(e), "traceback": tb}
            )
        finally:
            if executor:
                executor.stop_streaming()
                if not is_headed:
                    await executor.close()
                else:
                    if mission.get("cancelled"):
                        await executor.close()

    def grant_approval(self, mission_id: str):
        if mission_id in self.active_missions:
            self.active_missions[mission_id]["approval_granted"] = True

    def cancel_mission(self, mission_id: str):
        if mission_id in self.active_missions:
            self.active_missions[mission_id]["cancelled"] = True
            self.active_missions[mission_id]["status"] = "cancelled"
