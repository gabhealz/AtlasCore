from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class GeneratedDocumentDraft(BaseModel):
    title: str
    markdown_content: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "markdown_content", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field cannot be blank.")

        return cleaned_value


class GeneratedDocumentResponse(GeneratedDocumentDraft):
    id: int
    onboarding_id: int
    step_name: str
    agent_name: str
    document_kind: str
    review_status: str
    review_feedback: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeneratedDeliverableResponse(BaseModel):
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


class GeneratedDeliverableListEnvelope(BaseModel):
    data: list[GeneratedDeliverableResponse]


class GeneratedDeliverableEnvelope(BaseModel):
    data: GeneratedDeliverableResponse
