from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CTAButtonCreate(BaseModel):
    name: str
    button_text: str
    css_id: str

    @field_validator("name", "button_text", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field cannot be blank.")

        return cleaned_value

    @field_validator("css_id", mode="before")
    @classmethod
    def normalize_css_id(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        cleaned_value = value.strip().lower()
        if not cleaned_value:
            raise ValueError("Field cannot be blank.")

        return cleaned_value


class CTAButtonResponse(BaseModel):
    id: int
    onboarding_id: int
    name: str
    button_text: str
    css_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CTAButtonEnvelope(BaseModel):
    data: CTAButtonResponse


class CTAButtonListEnvelope(BaseModel):
    data: list[CTAButtonResponse]


class TrackingSheetRowResponse(BaseModel):
    name: str
    css_id: str
    suggested_event: str


class TrackingSheetEnvelope(BaseModel):
    data: list[TrackingSheetRowResponse]
