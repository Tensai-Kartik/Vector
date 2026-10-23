from app.recovery.engine import RecoveryEngine
from app.models.actions import ActionStep

def test_classify_failure_types():
    step = ActionStep(step_id="s1", action_type="click", intent="Click button")
    assert RecoveryEngine.classify_failure(step, "Timeout 15000ms exceeded waiting for selector") == "element_not_ready"
    assert RecoveryEngine.classify_failure(step, "Execution context was destroyed, most likely because of a navigation.") == "stale_context"
    assert RecoveryEngine.classify_failure(step, "net::ERR_CONNECTION_REFUSED") == "transient_network"
    assert RecoveryEngine.classify_failure(step, "Destination violates allowlist policy") == "permission_denied"

def test_bounded_retry_exhaustion():
    step = ActionStep(step_id="s1", action_type="click", intent="Click button", retry_policy=2)
    can_retry_1, _ = RecoveryEngine.is_safe_to_retry(step, current_retries=0, failure_class="element_not_ready")
    assert can_retry_1 is True

    can_retry_2, _ = RecoveryEngine.is_safe_to_retry(step, current_retries=1, failure_class="element_not_ready")
    assert can_retry_2 is True

    can_retry_3, msg = RecoveryEngine.is_safe_to_retry(step, current_retries=2, failure_class="element_not_ready")
    assert can_retry_3 is False
    assert "exhausted" in msg

def test_non_idempotent_high_risk_submit_protection():
    step = ActionStep(
        step_id="submit_step",
        action_type="click",
        intent="Submit financial order",
        risk_classification="high",
        retry_policy=2
    )
    can_retry, msg = RecoveryEngine.is_safe_to_retry(step, current_retries=0, failure_class="element_not_ready")
    assert can_retry is False
    assert "non-idempotent" in msg.lower()
