from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadedAssetResponse(BaseModel):
    id: int
    onboarding_id: int
    asset_kind: str
    asset_category: str | None = None
    original_filename: str
    storage_url: str | None = None
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadedAssetEnvelope(BaseModel):
    data: UploadedAssetResponse


class UploadedAssetListEnvelope(BaseModel):
    data: list[UploadedAssetResponse]
