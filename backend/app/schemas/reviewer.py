from pydantic import BaseModel, ConfigDict, field_validator


class ReviewerDecision(BaseModel):
    approved: bool
    feedback_summary: str
    violations: list[str]
    rewrite_instructions: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("feedback_summary", "rewrite_instructions", mode="before")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        return value.strip()

    @field_validator("violations", mode="before")
    @classmethod
    def normalize_violations(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []

        return [
            item.strip() for item in value if isinstance(item, str) and item.strip()
        ]
