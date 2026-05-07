from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PipelineStartResponse(BaseModel):
    onboarding_id: int
    status: str


class PipelineStartEnvelope(BaseModel):
    data: PipelineStartResponse


class PipelineEventResponse(BaseModel):
    id: int
    onboarding_id: int
    step_name: str
    from_status: str
    to_status: str
    payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
