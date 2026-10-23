from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ElementObservation(BaseModel):
    selector: str = Field(..., description="Playwright-compatible or CSS/role selector")
    tag_name: str
    role: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    placeholder: Optional[str] = None
    input_type: Optional[str] = None
    value: Optional[str] = None
    is_visible: bool = True
    is_enabled: bool = True
    is_editable: bool = False
    options: List[str] = Field(default_factory=list)
    attributes: Dict[str, str] = Field(default_factory=dict)
    uniqueness_count: int = 1
    bounding_box: Optional[Dict[str, float]] = None

class PageObservation(BaseModel):
    url: str
    title: str
    domain: str
    interactive_elements: List[ElementObservation] = Field(default_factory=list)
    headings: List[str] = Field(default_factory=list)
    has_forms: bool = False
    total_elements_sampled: int = 0
    snapshot_timestamp: datetime = Field(default_factory=datetime.utcnow)
