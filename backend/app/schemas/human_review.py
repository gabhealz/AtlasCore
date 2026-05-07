from datetime import datetime

from pydantic import BaseModel, field_validator


class HumanReviewDocumentResponse(BaseModel):
    id: int
    onboarding_id: int
    step_name: str
    agent_name: str
    document_kind: str
    title: str
    content: str
    content_format: str
    review_status: str
    review_feedback: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class HumanReviewDocumentEnvelope(BaseModel):
    data: HumanReviewDocumentResponse


class HumanReviewApproveRequest(BaseModel):
    title: str
    content: str

    @field_validator("title", "content", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field cannot be blank.")

        return cleaned_value


class HumanReviewRejectRequest(BaseModel):
    feedback: str

    @field_validator("feedback", mode="before")
    @classmethod
    def strip_feedback(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field cannot be blank.")

        return cleaned_value


class HumanReviewActionResponse(BaseModel):
    onboarding_id: int
    status: str
    next_step_name: str | None = None


class HumanReviewActionEnvelope(BaseModel):
    data: HumanReviewActionResponse
