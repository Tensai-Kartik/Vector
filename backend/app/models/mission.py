from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import uuid

MissionStatus = Literal[
    "queued",
    "inspecting",
    "planning",
    "awaiting_approval",
    "running",
    "validating",
    "retrying",
    "completed",
    "failed",
    "cancelled",
    "needs_input"
]

StepStatus = Literal[
    "pending",
    "validating",
    "running",
    "verifying",
    "retrying",
    "completed",
    "failed",
    "rejected",
    "skipped",
    "awaiting_approval"
]

EventType = Literal[
    "mission_created",
    "inspection_started",
    "inspection_completed",
    "plan_generated",
    "step_validated",
    "step_rejected",
    "api_route_selected",
    "browser_action_started",
    "browser_action_completed",
    "verification_passed",
    "verification_failed",
    "retry_started",
    "replanning_occurred",
    "approval_requested",
    "approval_granted",
    "artifact_created",
    "mission_completed",
    "mission_failed",
    "mission_cancelled",
    "needs_input"
]

class MissionEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str
    step_id: Optional[str] = None
    event_type: EventType
    category: Literal["system", "browser", "api", "guardrail", "recovery", "verification", "artifact"]
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MissionStepState(BaseModel):
    step_id: str
    action_type: str
    intent: str
    target_description: Optional[str] = None
    target_locator_value: Optional[str] = None
    input_value: Optional[str] = None
    status: StepStatus = "pending"
    execution_method: Optional[Literal["browser", "api"]] = None
    validation_status: Optional[str] = None
    validation_message: Optional[str] = None
    verification_status: Optional[str] = None
    verification_evidence: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

class MissionCreateRequest(BaseModel):
    task: str = Field(..., description="Natural language task prompt")
    start_url: Optional[str] = Field(None, description="Initial target URL if known")
    allowed_domains: Optional[List[str]] = Field(None, description="Explicit domain allowlist")
    require_approval_for_high_risk: bool = Field(True, description="Pause and ask for approval on high/critical actions")
    force_execution_method: Optional[Literal["browser", "api", "auto"]] = Field("auto")
    demo_mode: bool = Field(False, description="Run against built-in local synthetic demo site")
    open_browser_window: bool = Field(False, description="Open visible headed browser window on desktop")

class MissionResponse(BaseModel):
    id: str
    task: str
    status: MissionStatus
    start_url: Optional[str] = None
    allowed_domains: List[str]
    current_step_id: Optional[str] = None
    steps: List[MissionStepState] = Field(default_factory=list)
    events: List[MissionEvent] = Field(default_factory=list)
    extracted_data: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    summary_report: Optional[Dict[str, Any]] = None
