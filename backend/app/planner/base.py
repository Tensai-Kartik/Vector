from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.models.actions import ActionPlan
from app.models.inspector import PageObservation

class BasePlanner(ABC):
    """
    Abstract base class for all LLM planners producing structured ActionPlans.
    """

    @abstractmethod
    async def create_plan(
        self,
        task: str,
        current_page: Optional[PageObservation] = None,
        allowed_domains: Optional[List[str]] = None,
        demo_mode: bool = False
    ) -> ActionPlan:
        pass

    @abstractmethod
    async def replan_on_failure(
        self,
        task: str,
        failed_step_id: str,
        failure_reason: str,
        current_page: Optional[PageObservation] = None,
        allowed_domains: Optional[List[str]] = None
    ) -> ActionPlan:
        pass
