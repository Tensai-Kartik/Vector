from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ArtifactMetadata(BaseModel):
    artifact_id: str
    filename: str
    file_path: str
    file_size_bytes: int
    content_type: str
    sha256_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ExecutionReport(BaseModel):
    mission_id: str
    task: str
    verdict: str  # "success", "partial_success", "failed", "rejected", "aborted"
    is_verified: bool
    verification_summary: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    rejected_steps: int
    api_steps_count: int
    browser_steps_count: int
    retry_count: int
    replanning_count: int
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    extracted_records: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[ArtifactMetadata] = Field(default_factory=list)
    guardrail_rejections: List[Dict[str, Any]] = Field(default_factory=list)
    unresolved_steps: List[str] = Field(default_factory=list)
    honest_limitations: List[str] = Field(default_factory=list)
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
