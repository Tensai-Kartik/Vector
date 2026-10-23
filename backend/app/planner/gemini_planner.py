import json
import re
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from app.planner.base import BasePlanner
from app.models.actions import ActionPlan, ActionStep
from app.models.inspector import PageObservation
from app.config import settings

PLANNER_SYSTEM_PROMPT = """
You are VECTOR, an advanced autonomous web operator planning engine.
Your mission is to decompose a natural language user task into a strict, validated, typed action plan.

CRITICAL CONSTRAINTS:
1. You MUST NEVER generate arbitrary Python code, shell commands, or unconstrained JavaScript execution payloads.
2. Only select from authorized action types:
   - 'navigate': Navigate to a permitted URL.
   - 'click': Click a unique interactive element.
   - 'fill': Fill an input or textarea.
   - 'select_option': Select a dropdown option.
   - 'read_text': Read text content of an element.
   - 'extract_records': Extract table or repeating list records.
   - 'wait_for_condition': Wait for selector or condition.
   - 'download_file': Trigger a file download.
   - 'api_operation': Query direct authorized REST API (e.g. GitHub).
   - 'request_approval': Request operator approval for high risk actions.
   - 'request_clarification': Ask user for guidance if ambiguous.
3. Every step MUST have:
   - 'step_id' (e.g. 'step_1', 'step_2')
   - 'action_type'
   - 'intent' (concise description)
   - 'target_locator_strategy' (css, role, text, label, placeholder)
   - 'target_locator_value'
   - 'risk_classification' ('low', 'medium', 'high', 'critical')
   - 'verification_method' ('url_match', 'element_present', 'element_value', 'record_count', 'file_downloaded', 'api_status', 'none')
   - 'verification_target'
4. High-impact operations (e.g. form submit, delete, payment) MUST have risk_classification='high' or 'critical'.
5. Return ONLY a valid JSON object matching the ActionPlan schema. No markdown backticks, no commentary.
"""

class GeminiPlanner(BasePlanner):
    """
    Google Gemini LLM planning engine using structured JSON outputs.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        if self.api_key:
            genai.configure(api_key=self.api_key)

    async def create_plan(
        self,
        task: str,
        current_page: Optional[PageObservation] = None,
        allowed_domains: Optional[List[str]] = None,
        demo_mode: bool = False
    ) -> ActionPlan:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings. Set the API key or switch to Mock Planner.")

        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=PLANNER_SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json"}
        )

        context = {
            "task": task,
            "demo_mode": demo_mode,
            "allowed_domains": allowed_domains or settings.allowed_domains_list,
            "current_page": current_page.model_dump() if current_page else None
        }

        prompt = f"Generate an ActionPlan for the following mission:\n{json.dumps(context, indent=2, default=str)}"
        
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        
        # Clean markdown code blocks if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            
        plan_dict = json.loads(text)
        return ActionPlan.model_validate(plan_dict)

    async def replan_on_failure(
        self,
        task: str,
        failed_step_id: str,
        failure_reason: str,
        current_page: Optional[PageObservation] = None,
        allowed_domains: Optional[List[str]] = None
    ) -> ActionPlan:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=PLANNER_SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json"}
        )

        context = {
            "mode": "REPLANNING_AFTER_FAILURE",
            "task": task,
            "failed_step_id": failed_step_id,
            "failure_reason": failure_reason,
            "allowed_domains": allowed_domains or settings.allowed_domains_list,
            "current_page": current_page.model_dump() if current_page else None
        }

        prompt = f"The previous step failed. Replan a safe recovery action plan from the current page state:\n{json.dumps(context, indent=2, default=str)}"
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            
        plan_dict = json.loads(text)
        return ActionPlan.model_validate(plan_dict)
