from typing import Dict, Any, Optional, Literal, Tuple
from app.models.actions import ActionStep

FailureClass = Literal[
    "transient_network",
    "element_not_ready",
    "stale_context",
    "selector_not_found",
    "permission_denied",
    "non_idempotent_risk",
    "fatal"
]

class RecoveryEngine:
    """
    Classifies execution failures, enforces bounded retries,
    safeguards non-idempotent operations, and coordinates replanning.
    """

    NON_IDEMPOTENT_ACTIONS = ["click", "submit"]

    @classmethod
    def classify_failure(cls, step: ActionStep, error_msg: str) -> FailureClass:
        msg = error_msg.lower()
        if "timeout" in msg or "waiting for selector" in msg:
            return "element_not_ready"
        if "stale" in msg or "execution context was destroyed" in msg:
            return "stale_context"
        if "net::err" in msg or "econnrefused" in msg:
            return "transient_network"
        if "not found" in msg or "missing" in msg:
            return "selector_not_found"
        if "allowlist" in msg or "permission" in msg or "private network" in msg:
            return "permission_denied"
        return "fatal"

    @classmethod
    def is_safe_to_retry(cls, step: ActionStep, current_retries: int, failure_class: FailureClass) -> Tuple[bool, str]:
        # Enforce retry boundary
        if current_retries >= step.retry_policy:
            return False, f"Maximum bounded retries ({step.retry_policy}) exhausted for step {step.step_id}."

        # Fatal and permission errors cannot be retried
        if failure_class in ["fatal", "permission_denied"]:
            return False, f"Failure class '{failure_class}' is non-recoverable."

        # Non-idempotent safety: if high risk form submission, do not repeat blindly
        if step.risk_classification in ["high", "critical"] and step.action_type in cls.NON_IDEMPOTENT_ACTIONS:
            return False, "Non-idempotent high-impact action cannot be automatically retried without state re-verification."

        # Transient network, element not ready, stale context can be retried
        if failure_class in ["element_not_ready", "transient_network", "stale_context"]:
            return True, f"Failure classified as '{failure_class}'. Bounded retry permitted ({current_retries + 1}/{step.retry_policy})."

        return False, "Retry denied by safety policy."
