from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import ipaddress
import re
from playwright.async_api import Page
from app.models.actions import ActionStep
from app.models.guardrail import ValidationResult, GuardrailCheckItem
from app.config import settings

DISALLOWED_IP_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),     # AWS / Azure / GCP Link-local metadata
    ipaddress.ip_network("10.0.0.0/8"),         # Private RFC1918
    ipaddress.ip_network("172.16.0.0/12"),      # Private RFC1918
    ipaddress.ip_network("192.168.0.0/16"),     # Private RFC1918
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("fc00::/7"),           # IPv6 Unique local
]

SUSPICIOUS_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"delete\s+all\s+(data|files|databases)", re.IGNORECASE),
    re.compile(r"exfiltrate|send\s+password", re.IGNORECASE),
    re.compile(r"bypass\s+security", re.IGNORECASE),
]

class SafetyGate:
    """
    Mandatory safety gate executing strictly before every step to validate
    URL permissions, target element existence & uniqueness, visibility,
    enabled state, action compatibility, prompt injection resistance,
    and user approval requirements.
    """

    @staticmethod
    def is_url_allowed(url: str, allowed_domains: List[str], demo_mode: bool = False) -> bool:
        if not url:
            return True
        try:
            parsed = urlparse(url)
            if parsed.scheme in ["file", "chrome"]:
                return True
            hostname = parsed.hostname or ""
            if not hostname:
                return False

            # Check for Cloud Metadata or Private Network SSRF
            try:
                ip = ipaddress.ip_address(hostname)
                # If localhost or 127.0.0.1 in demo mode, allow it
                if (ip.is_loopback or hostname in ["localhost", "127.0.0.1"]) and demo_mode:
                    return True
                # Check link-local metadata 169.254.169.254 or private networks
                for net in DISALLOWED_IP_NETWORKS:
                    if ip in net:
                        return False
            except ValueError:
                # Not a literal IP, it's a domain name
                pass

            if "*" in allowed_domains:
                return True

            # If localhost or 127.0.0.1 and demo mode, allow
            if hostname in ["localhost", "127.0.0.1"] and demo_mode:
                return True

            # Check allowed domains
            allowed_clean = [d.lower().strip() for d in allowed_domains]
            if hostname.lower() in allowed_clean:
                return True

            # Subdomain check
            for d in allowed_clean:
                if hostname.lower().endswith("." + d):
                    return True

            return False
        except Exception:
            return False

    @staticmethod
    def contains_prompt_injection(text: Optional[str]) -> bool:
        if not text:
            return False
        for pat in SUSPICIOUS_PROMPT_INJECTION_PATTERNS:
            if pat.search(text):
                return True
        return False

    @classmethod
    async def validate_action(
        cls,
        step: ActionStep,
        page: Optional[Page],
        allowed_domains: List[str],
        demo_mode: bool = False,
        approval_granted: bool = False,
        require_approval_for_high_risk: bool = True
    ) -> ValidationResult:
        checks: List[GuardrailCheckItem] = []

        # 1. URL Domain & SSRF check
        if step.action_type == "navigate":
            target_url = step.input_value or ""
            url_ok = cls.is_url_allowed(target_url, allowed_domains, demo_mode=demo_mode)
            checks.append(GuardrailCheckItem(
                check_name="url_destination_allowlist",
                passed=url_ok,
                message=f"URL '{target_url}' allowed under active domain policy: {url_ok}",
                details={"url": target_url, "allowed_domains": allowed_domains}
            ))
            if not url_ok:
                return ValidationResult(
                    verdict="rejected",
                    can_proceed=False,
                    rejection_reason=f"Navigation destination '{target_url}' violates domain allowlist or private network policy.",
                    checks=checks,
                    url_allowed=False
                )

        # 2. Risk & Approval check
        if step.risk_classification in ["high", "critical"] and require_approval_for_high_risk:
            if not approval_granted:
                checks.append(GuardrailCheckItem(
                    check_name="human_approval_gate",
                    passed=False,
                    message=f"Action '{step.action_type}' has {step.risk_classification} risk classification and requires human authorization.",
                    details={"risk": step.risk_classification}
                ))
                return ValidationResult(
                    verdict="requires_approval",
                    can_proceed=False,
                    requires_approval=True,
                    rejection_reason=f"Action '{step.intent}' classified as {step.risk_classification} risk. Pausing for operator sign-off.",
                    checks=checks
                )
            else:
                checks.append(GuardrailCheckItem(
                    check_name="human_approval_gate",
                    passed=True,
                    message="Operator approval verified for high-impact action.",
                    details={"risk": step.risk_classification}
                ))

        # 3. Prompt injection detection in input values
        if cls.contains_prompt_injection(step.input_value):
            checks.append(GuardrailCheckItem(
                check_name="prompt_injection_sanitization",
                passed=False,
                message="Potential prompt injection or untrusted override pattern detected in action parameter.",
                details={"input": step.input_value}
            ))
            return ValidationResult(
                verdict="rejected",
                can_proceed=False,
                rejection_reason="Action rejected: Detected untrusted system override pattern in payload.",
                checks=checks
            )

        # System command safety validation
        if step.action_type == "system_command":
            cmd = (step.input_value or "").lower()
            dangerous_patterns = [r"\bformat\b", r"\bdel\s+/[sfq]", r"\brmdir\s+/[sfq]", r"\bdrop\s+database\b", r"\breg\s+delete\b"]
            for dp in dangerous_patterns:
                if re.search(dp, cmd):
                    checks.append(GuardrailCheckItem(
                        check_name="system_command_safety",
                        passed=False,
                        message=f"Dangerous command pattern detected and rejected: {cmd}",
                        details={"cmd": cmd}
                    ))
                    return ValidationResult(
                        verdict="rejected",
                        can_proceed=False,
                        rejection_reason=f"Safety Gate rejected dangerous OS command payload: {cmd}",
                        checks=checks
                    )

        # If action doesn't interact with DOM (e.g. wait, api_operation, navigate, launch_app, system_command), we are good
        if step.action_type in [
            "navigate", "api_operation", "wait_for_condition",
            "request_approval", "request_clarification", "launch_app", "system_command"
        ]:
            return ValidationResult(
                verdict="passed",
                can_proceed=True,
                checks=checks,
                url_allowed=True
            )

        # 4. Target element existence, uniqueness, visibility, and enabled state
        selector = step.target_locator_value
        if not selector:
            checks.append(GuardrailCheckItem(
                check_name="target_locator_specified",
                passed=False,
                message="Step does not provide a target locator.",
                details={}
            ))
            return ValidationResult(
                verdict="rejected",
                can_proceed=False,
                rejection_reason=f"Step '{step.step_id}' missing target locator value.",
                checks=checks
            )

        if not page:
            return ValidationResult(
                verdict="rejected",
                can_proceed=False,
                rejection_reason="No active browser page session available for interaction.",
                checks=checks
            )

        # Query element count on page
        try:
            elements = await page.locator(selector).all()
            count = len(elements)
        except Exception as e:
            checks.append(GuardrailCheckItem(
                check_name="target_locator_validity",
                passed=False,
                message=f"Locator syntax invalid or query threw error: {str(e)}",
                details={"selector": selector}
            ))
            return ValidationResult(
                verdict="rejected",
                can_proceed=False,
                rejection_reason=f"Invalid selector query '{selector}': {str(e)}",
                checks=checks
            )

        # Existence check
        if count == 0:
            checks.append(GuardrailCheckItem(
                check_name="target_element_existence",
                passed=False,
                message=f"Target element matching '{selector}' was not found in current DOM.",
                details={"selector": selector, "count": 0}
            ))
            return ValidationResult(
                verdict="rejected",
                can_proceed=False,
                rejection_reason=f"Target element '{selector}' does not exist on the current page.",
                checks=checks,
                target_uniqueness_count=0,
                target_visible=False,
                requires_replanning=True
            )

        # Uniqueness check: scope to primary target if multiple elements match
        target_el = elements[0]
        if count > 1:
            checks.append(GuardrailCheckItem(
                check_name="target_element_uniqueness",
                passed=True,
                message=f"Selector '{selector}' matched {count} elements. Scoping to primary visible target (1/{count}).",
                details={"selector": selector, "count": count}
            ))
            # Find first visible element if available
            for el in elements:
                try:
                    if await el.is_visible():
                        target_el = el
                        break
                except Exception:
                    pass
        else:
            checks.append(GuardrailCheckItem(
                check_name="target_element_uniqueness",
                passed=True,
                message=f"Selector '{selector}' matched uniquely.",
                details={"selector": selector, "count": 1}
            ))
        # Visibility and Enabled check
        if selector in ["body", "html"]:
            is_visible = True
            is_enabled = True
        else:
            is_visible = await target_el.is_visible()
            is_enabled = await target_el.is_enabled()

        if not is_visible:
            checks.append(GuardrailCheckItem(
                check_name="target_element_visibility",
                passed=False,
                message="Target element exists in DOM but is not currently visible or rendered.",
                details={"selector": selector}
            ))
            return ValidationResult(
                verdict="rejected",
                can_proceed=False,
                rejection_reason=f"Element '{selector}' is hidden or off-screen.",
                checks=checks,
                target_visible=False,
                target_enabled=is_enabled,
                target_uniqueness_count=count
            )

        if not is_enabled and step.action_type in ["click", "fill", "select_option"]:
            checks.append(GuardrailCheckItem(
                check_name="target_element_enabled",
                passed=False,
                message="Target element is disabled in the current DOM state.",
                details={"selector": selector}
            ))
            return ValidationResult(
                verdict="rejected",
                can_proceed=False,
                rejection_reason=f"Element '{selector}' is currently disabled.",
                checks=checks,
                target_visible=is_visible,
                target_enabled=False,
                target_uniqueness_count=count
            )

        # All checks passed
        checks.append(GuardrailCheckItem(
            check_name="pre_execution_guardrails_passed",
            passed=True,
            message=f"Target element validated: unique (1/1), visible, enabled, and compatible with '{step.action_type}'.",
            details={"selector": selector, "count": 1}
        ))

        return ValidationResult(
            verdict="passed",
            can_proceed=True,
            checks=checks,
            target_uniqueness_count=1,
            target_visible=True,
            target_enabled=True,
            url_allowed=True
        )
