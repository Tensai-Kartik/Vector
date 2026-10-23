from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

ActionType = Literal[
    "navigate",
    "click",
    "fill",
    "select_option",
    "read_text",
    "extract_records",
    "wait_for_condition",
    "download_file",
    "api_operation",
    "request_clarification",
    "request_approval",
    "launch_app",
    "system_command"
]

RiskClassification = Literal["low", "medium", "high", "critical"]
ExecutionPreference = Literal["browser", "api", "auto"]
VerificationMethod = Literal[
    "url_match",
    "element_present",
    "element_value",
    "record_count",
    "file_downloaded",
    "api_status",
    "explicit_signal",
    "app_launched",
    "command_success",
    "none"
]

class ActionStep(BaseModel):
    step_id: str = Field(..., description="Stable unique step ID, e.g. step_1")
    action_type: ActionType = Field(..., description="The typed action operation")
    intent: str = Field(..., description="Human-readable explanation of this action")
    target_description: Optional[str] = Field(None, description="Semantic description of the target element")
    target_locator_strategy: Optional[str] = Field(None, description="role, text, label, placeholder, css, test_id")
    target_locator_value: Optional[str] = Field(None, description="Locator string / selector")
    input_value: Optional[str] = Field(None, description="Input text, URL, option value, or parameter payload")
    expected_preconditions: Optional[str] = Field(None, description="What must be true before this step runs")
    expected_postconditions: Optional[str] = Field(None, description="What must be true after this step runs")
    risk_classification: RiskClassification = Field("low", description="Risk level")
    execution_method_preference: ExecutionPreference = Field("auto", description="Execution method preference")
    timeout_ms: int = Field(15000, description="Step timeout in milliseconds")
    retry_policy: int = Field(2, description="Bounded retry attempts")
    verification_method: VerificationMethod = Field("none", description="Post-execution verification method")
    verification_target: Optional[str] = Field(None, description="Target URL, selector, or pattern to verify")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional step metadata")

class ActionPlan(BaseModel):
    task: str = Field(..., description="Original user task")
    reasoning: str = Field(..., description="High level reasoning for the plan")
    allowed_domains: List[str] = Field(default_factory=list, description="Domains allowed during execution")
    steps: List[ActionStep] = Field(..., description="Ordered list of typed actions to execute")
