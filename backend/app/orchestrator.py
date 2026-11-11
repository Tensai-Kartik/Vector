import os
import sys
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
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.active_executors: Dict[str, Any] = {}

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
        event_payload = event.model_dump(mode='json')
        Database.save_event(event_payload)
        if self.broadcast_fn:
            await self.broadcast_fn(mission_id, event_payload)
        return event

    @staticmethod
    def resolve_planner_config(req: MissionCreateRequest) -> Dict[str, Any]:
        """
        Resolve active planner selection cleanly:
        - Default working planner is always 'deterministic' unless user explicitly requests 'gemini'.
        - LLM_PROVIDER='gemini' with GEMINI_API_KEY registers Gemini as the standby/selectable LLM.
        """
        requested_mode = (req.planner_mode or settings.PLANNER_MODE or "deterministic").strip().lower()
        if requested_mode == "mock":
            requested_mode = "deterministic"
        llm_provider = (settings.LLM_PROVIDER or "gemini").strip().lower()
        llm_ready = (llm_provider == "gemini" and bool(settings.GEMINI_API_KEY))
        use_gemini_primary = (requested_mode == "gemini" and llm_ready)
        return {
            "requested_mode": requested_mode,
            "llm_provider": llm_provider,
            "llm_ready": llm_ready,
            "use_gemini_primary": use_gemini_primary,
        }

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
        task_handle = asyncio.create_task(self.run_pipeline(mission_id, req))
        self.active_tasks[mission_id] = task_handle
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

            is_render = bool(os.getenv("RENDER"))
            # On desktop: launch visible browser window unless explicitly headless or on Render
            is_headed = (getattr(req, "open_browser_window", True) or not settings.BROWSER_HEADLESS) and not is_render
            executor = PlaywrightExecutor(
                frame_callback=on_frame,
                headless=not is_headed
            )
            self.active_executors[mission_id] = executor
            try:
                await asyncio.wait_for(executor.initialize(), timeout=90)
            except Exception as init_err:
                err_text = f"Browser initialization failed: {init_err}"
                print(f"[Orchestrator] {err_text}")
                mission["status"] = "failed"
                await self.emit_event(
                    mission_id=mission_id,
                    event_type="mission_failed",
                    category="browser",
                    message=err_text,
                    details={"error": str(init_err)}
                )
                raise RuntimeError(err_text)

            # 3. Planning Phase (Deterministic working model by default; Gemini only when user selects it or deterministic fails)
            mission["status"] = "planning"
            planner_cfg = self.resolve_planner_config(req)
            use_gemini_primary = planner_cfg["use_gemini_primary"]
            llm_ready = planner_cfg["llm_ready"]
            requested_mode = planner_cfg["requested_mode"]

            if requested_mode == "gemini" and not llm_ready:
                await self.emit_event(
                    mission_id=mission_id,
                    event_type="replanning_occurred",
                    category="system",
                    message="Gemini LLM selected, but GEMINI_API_KEY is not configured. Using Deterministic Planner."
                )

            planner_label = "Gemini LLM" if use_gemini_primary else "Deterministic Planner"
            await self.emit_event(
                mission_id=mission_id,
                event_type="plan_generated",
                category="system",
                message=f"Generating structured action plan using {planner_label}..."
            )

            used_gemini_for_plan = use_gemini_primary
            planner = GeminiPlanner() if use_gemini_primary else MockPlanner()
            try:
                plan: ActionPlan = await planner.create_plan(
                    task=req.task,
                    allowed_domains=mission["allowed_domains"],
                    demo_mode=req.demo_mode
                )
            except Exception as plan_err:
                if isinstance(planner, GeminiPlanner):
                    print(f"[Orchestrator] GeminiPlanner failed ({plan_err}). Falling back to Deterministic Planner...")
                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="replanning_occurred",
                        category="system",
                        message=f"Gemini API warning: {plan_err}. Falling back to Deterministic Planner..."
                    )
                    used_gemini_for_plan = False
                    planner = MockPlanner()
                    plan = await planner.create_plan(
                        task=req.task,
                        allowed_domains=mission["allowed_domains"],
                        demo_mode=req.demo_mode
                    )
                elif llm_ready:
                    print(f"[Orchestrator] Deterministic planner failed ({plan_err}). Falling back to Gemini LLM...")
                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="replanning_occurred",
                        category="system",
                        message=f"Deterministic planner failed ({plan_err}). Falling back to configured Gemini LLM..."
                    )
                    used_gemini_for_plan = True
                    planner = GeminiPlanner()
                    plan = await planner.create_plan(
                        task=req.task,
                        allowed_domains=mission["allowed_domains"],
                        demo_mode=req.demo_mode
                    )
                else:
                    raise plan_err

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

            # 4. Step-by-Step Execution Loop (with automatic Gemini LLM recovery when deterministic fails)
            mission["status"] = "running"
            step_queue: List[ActionStep] = list(plan.steps)
            step_idx = 0
            while step_idx < len(step_queue):
                step = step_queue[step_idx]
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

                current_url = None
                if executor and executor.page:
                    try:
                        current_url = executor.page.url
                        mission["current_url"] = current_url
                    except Exception:
                        pass

                # Validation failure (defer hard rejection when CAPTCHA-gated or recoverable via Gemini standby)
                if res.get("status") == "rejected" and not res.get("captcha_blocked") and not (
                    res.get("requires_replanning")
                    and not used_gemini_for_plan
                    and llm_ready
                    and not req.demo_mode
                    and replanning_count == 0
                ):
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
                    if current_url:
                        completion_details["final_url"] = current_url

                    await self.emit_event(
                        mission_id=mission_id,
                        event_type="browser_action_completed",
                        category="browser",
                        message=f"Step completed and postconditions verified: {step.intent}",
                        step_id=step.step_id,
                        details=completion_details
                    )
                    if is_headed and executor:
                        executor.bring_to_foreground()

                    r_data_ok = res.get("result_data") or {}
                    if r_data_ok.get("action_required") == "local_media_picker":
                        folder_label = r_data_ok.get("requested_folder") or "Downloads"
                        picker_msg = (
                            f"Cloud deployment cannot access your PC's local {folder_label} folder directly. "
                            f"Grant {folder_label} folder permission in your browser to play local media."
                        )
                        mission["needs_input_action"] = "local_media_picker"
                        mission["needs_input_reason"] = picker_msg
                        await self.emit_event(
                            mission_id=mission_id,
                            event_type="needs_input",
                            category="system",
                            message=picker_msg,
                            step_id=step.step_id,
                            details={
                                "action_required": "local_media_picker",
                                "requested_folder": folder_label,
                                "wants_media_playback": bool(r_data_ok.get("wants_media_playback", True)),
                            },
                        )
                        mission["status"] = "needs_input"
                        break
                else:
                    # Step failed postcondition or action execution
                    v_info = res.get("verification") or {}
                    r_data = res.get("result_data") or {}
                    gate = (
                        res.get("anti_bot_gate")
                        or v_info.get("anti_bot_gate")
                        or (v_info.get("evidence") if v_info.get("captcha_blocked") else None)
                        or r_data.get("anti_bot_gate")
                        or {}
                    )
                    is_captcha_gate = bool(res.get("captcha_blocked") or v_info.get("captcha_blocked") or gate.get("blocked"))

                    error_description = (
                        res.get("error") or
                        v_info.get("error") or
                        f"Postcondition verification failed for strategy '{v_info.get('strategy', 'unknown')}'"
                    )
                    if current_step_dict:
                        current_step_dict["status"] = "failed"
                        current_step_dict["error_message"] = error_description
                        current_step_dict["end_time"] = datetime.utcnow().isoformat()

                    failure_details = dict(res)
                    if current_url:
                        failure_details["final_url"] = current_url

                    if is_captcha_gate:
                        mission["captcha_blocked"] = True
                        mission["needs_input_reason"] = error_description
                        if executor:
                            try:
                                await executor.capture_frame()
                            except Exception:
                                pass
                        await self.emit_event(
                            mission_id=mission_id,
                            event_type="needs_input",
                            category="system",
                            message=error_description,
                            step_id=step.step_id,
                            details=failure_details
                        )
                        mission["status"] = "needs_input"
                        break

                    # If Deterministic Planner hit a non-CAPTCHA runtime failure and Gemini API key is configured,
                    # automatically inspect the live DOM and ask GeminiPlanner to replan recovery steps.
                    if (
                        not used_gemini_for_plan
                        and llm_ready
                        and not req.demo_mode
                        and replanning_count == 0
                    ):
                        page_obs = None
                        if executor and executor.page:
                            try:
                                page_obs = await DOMInspector.inspect_page(executor.page)
                            except Exception:
                                page_obs = None
                        try:
                            await self.emit_event(
                                mission_id=mission_id,
                                event_type="replanning_occurred",
                                category="recovery",
                                step_id=step.step_id,
                                message=(
                                    f"Deterministic step '{step.step_id}' failed ({error_description}). "
                                    "Invoking Gemini LLM for adaptive recovery..."
                                ),
                            )
                            recovery_plan = await GeminiPlanner().replan_on_failure(
                                task=req.task,
                                failed_step_id=step.step_id,
                                failure_reason=error_description,
                                current_page=page_obs,
                                allowed_domains=mission["allowed_domains"],
                            )
                            if recovery_plan and recovery_plan.steps:
                                if recovery_plan.allowed_domains:
                                    mission["allowed_domains"] = list(
                                        set(mission["allowed_domains"] + recovery_plan.allowed_domains)
                                    )
                                rec_prefix = f"rec_{replanning_count + 1}_"
                                normalized_rec_steps: List[ActionStep] = []
                                new_step_states: List[Dict[str, Any]] = []
                                for idx_r, rs in enumerate(recovery_plan.steps, start=1):
                                    rs_copy = rs.model_copy(update={"step_id": f"{rec_prefix}{rs.step_id or idx_r}"})
                                    normalized_rec_steps.append(rs_copy)
                                    new_step_states.append(
                                        MissionStepState(
                                            step_id=rs_copy.step_id,
                                            action_type=rs_copy.action_type,
                                            intent=rs_copy.intent,
                                            target_description=rs_copy.target_description,
                                            target_locator_value=rs_copy.target_locator_value,
                                            input_value=rs_copy.input_value,
                                            status="pending",
                                        ).model_dump()
                                    )

                                if current_step_dict:
                                    current_step_dict["status"] = "skipped"
                                    current_step_dict["error_message"] = (
                                        f"Recovered via Gemini LLM after error: {error_description}"
                                    )

                                # Replace remaining deterministic steps with Gemini recovery steps
                                mission["steps"] = [
                                    s for s in mission["steps"]
                                    if s["status"] in ("completed", "skipped", "failed", "rejected")
                                ] + new_step_states
                                Database.save_mission(mission)

                                step_queue = step_queue[: step_idx + 1] + normalized_rec_steps
                                replanning_count += 1
                                await self.emit_event(
                                    mission_id=mission_id,
                                    event_type="replanning_occurred",
                                    category="recovery",
                                    step_id=step.step_id,
                                    message=f"Gemini LLM generated {len(normalized_rec_steps)} recovery step(s).",
                                    details={"steps": [s.model_dump() for s in normalized_rec_steps], "replaced_tail": True},
                                )
                                step_idx += 1
                                continue
                        except Exception as llm_rec_err:
                            await self.emit_event(
                                mission_id=mission_id,
                                event_type="replanning_occurred",
                                category="recovery",
                                step_id=step.step_id,
                                message=f"Gemini recovery attempt failed: {llm_rec_err}",
                            )

                    if res.get("status") == "rejected":
                        guardrail_rejections.append({
                            "step_id": step.step_id,
                            "intent": step.intent,
                            "error": error_description,
                            "validation": res.get("validation"),
                        })
                        if current_step_dict:
                            current_step_dict["status"] = "rejected"
                            current_step_dict["validation_message"] = error_description
                        await self.emit_event(
                            mission_id=mission_id,
                            event_type="step_rejected",
                            category="guardrail",
                            message=f"Pre-execution guardrail REJECTED step: {error_description}",
                            step_id=step.step_id,
                            details=res,
                        )
                    else:
                        await self.emit_event(
                            mission_id=mission_id,
                            event_type="verification_failed",
                            category="verification",
                            message=f"Step failed verification: {error_description}",
                            step_id=step.step_id,
                            details=failure_details,
                        )
                    mission["status"] = "failed"
                    break

                step_idx += 1

            # 5. Finalize Mission and Build Report
            end_time = datetime.utcnow()
            completed_steps = sum(1 for s in mission["steps"] if s["status"] == "completed")
            failed_steps = sum(1 for s in mission["steps"] if s["status"] == "failed")
            rejected_steps = sum(1 for s in mission["steps"] if s["status"] == "rejected")
            skipped_steps = sum(1 for s in mission["steps"] if s["status"] == "skipped")
            total_steps = len(mission["steps"])
            effective_total = total_steps - skipped_steps
            all_verified = (
                completed_steps == effective_total
                and completed_steps > 0
                and failed_steps == 0
                and rejected_steps == 0
            )

            needs_user_action = bool(mission.get("captcha_blocked") or mission.get("needs_input_action"))
            if mission.get("cancelled"):
                final_verdict = "cancelled"
                mission["status"] = "cancelled"
            elif needs_user_action:
                final_verdict = "partial_success" if completed_steps > 0 else "failed"
                mission["status"] = "needs_input"
            elif all_verified:
                final_verdict = "success"
                mission["status"] = "completed"
            elif completed_steps > 0:
                final_verdict = "partial_success"
                mission["status"] = "failed"
            else:
                final_verdict = "failed"
                mission["status"] = "failed"

            summary_text = (
                mission.get("needs_input_reason")
                if needs_user_action and mission.get("needs_input_reason")
                else f"Mission concluded: {completed_steps}/{effective_total} steps executed and postcondition-verified."
            )

            report = ExecutionReport(
                mission_id=mission_id,
                task=req.task,
                verdict=final_verdict,
                is_verified=all_verified,
                verification_summary=summary_text,
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

            final_event_type = (
                "needs_input"
                if needs_user_action
                else ("mission_completed" if all_verified else "mission_failed")
            )
            final_msg = (
                summary_text
                if mission.get("needs_input_action")
                else (
                    f"Human verification required: {summary_text}"
                    if mission.get("captcha_blocked")
                    else f"Mission finalized with verdict: '{final_verdict}'. Verified: {all_verified}"
                )
            )
            await self.emit_event(
                mission_id=mission_id,
                event_type=final_event_type,
                category="system",
                message=final_msg,
                details={
                    **report.model_dump(),
                    "captcha_blocked": bool(mission.get("captcha_blocked")),
                    "action_required": mission.get("needs_input_action"),
                }
            )

        except asyncio.CancelledError:
            mission["status"] = "cancelled"
            Database.save_mission(mission)
        except Exception as e:
            if mission.get("cancelled") or "TargetClosedError" in type(e).__name__:
                mission["status"] = "cancelled"
                Database.save_mission(mission)
            else:
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
                if not is_headed or mission.get("cancelled"):
                    executor.stop_streaming()
                    await executor.close()

    def grant_approval(self, mission_id: str):
        if mission_id in self.active_missions:
            self.active_missions[mission_id]["approval_granted"] = True

    async def cancel_mission(self, mission_id: str):
        if mission_id in self.active_missions:
            m = self.active_missions[mission_id]
            m["cancelled"] = True
            m["status"] = "cancelled"
            Database.save_mission(m)

        executor: Optional[PlaywrightExecutor] = self.active_executors.pop(mission_id, None)
        if executor:
            executor.is_cancelled = True
            executor.stop_streaming()
            try:
                await executor.close()
            except Exception:
                pass

        task_handle = self.active_tasks.pop(mission_id, None)
        if task_handle and not task_handle.done():
            try:
                task_handle.cancel()
            except Exception:
                pass

    async def kill_all_active_missions(self):
        for m_id in list(self.active_missions.keys()):
            await self.cancel_mission(m_id)
        for m_id, executor in list(self.active_executors.items()):
            try:
                executor.is_cancelled = True
                executor.stop_streaming()
                await executor.close()
            except Exception:
                pass
        self.active_executors.clear()
        self.active_tasks.clear()
