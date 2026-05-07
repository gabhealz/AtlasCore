from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class OnboardingBase(BaseModel):
    doctor_name: str
    specialty: str | None = None
    target_audience: str | None = None
    differentials: str | None = None
    tone_of_voice: str | None = None

    @field_validator("doctor_name", mode="before")
    @classmethod
    def strip_and_validate_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field cannot be blank.")

        return cleaned_value

    @field_validator(
        "specialty",
        "target_audience",
        "differentials",
        "tone_of_voice",
        mode="before",
    )
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        cleaned_value = value.strip()
        return cleaned_value or None


class OnboardingCreate(OnboardingBase):
    pass


class OnboardingListItem(BaseModel):
    id: int
    doctor_name: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OnboardingListResponse(BaseModel):
    data: list[OnboardingListItem]


class OnboardingDetailResponse(OnboardingBase):
    id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OnboardingDetailEnvelope(BaseModel):
    data: OnboardingDetailResponse
