from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

ValidationVerdict = Literal["passed", "rejected", "requires_approval", "warning"]

class GuardrailCheckItem(BaseModel):
    check_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ValidationResult(BaseModel):
    verdict: ValidationVerdict
    can_proceed: bool
    rejection_reason: Optional[str] = None
    checks: List[GuardrailCheckItem] = Field(default_factory=list)
    target_uniqueness_count: Optional[int] = None
    target_visible: Optional[bool] = None
    target_enabled: Optional[bool] = None
    url_allowed: Optional[bool] = None
    requires_approval: bool = False
    requires_replanning: bool = False
