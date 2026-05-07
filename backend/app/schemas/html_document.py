from pydantic import BaseModel, ConfigDict, field_validator


class GeneratedHtmlDocumentDraft(BaseModel):
    title: str
    html_content: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "html_content", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Field cannot be blank.")

        return cleaned_value
