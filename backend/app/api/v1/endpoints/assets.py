from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.onboarding import Onboarding
from app.models.uploaded_asset import UploadedAsset
from app.schemas.asset import UploadedAssetEnvelope, UploadedAssetListEnvelope
from app.services.asset_service import AssetService

router = APIRouter()

allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])
allow_write = deps.RoleChecker(["admin", "operator"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
TRANSCRIPTION_ALLOWED_FILE_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}
TRANSCRIPTION_DEFAULT_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
IMAGE_ALLOWED_FILE_TYPES = {
    ".jpg": {"image/jpeg", "application/octet-stream"},
    ".jpeg": {"image/jpeg", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
    ".webp": {"image/webp", "application/octet-stream"},
    ".heic": {
        "image/heic",
        "image/heif",
        "image/heic-sequence",
        "image/heif-sequence",
        "application/octet-stream",
    },
    ".heif": {
        "image/heif",
        "image/heic",
        "image/heic-sequence",
        "image/heif-sequence",
        "application/octet-stream",
    },
}
IMAGE_DEFAULT_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}
ALLOWED_IMAGE_CATEGORIES = {
    "hero_image",
    "profile_picture",
    "environment_photo",
    "treatment_photo",
}


def get_asset_service() -> AssetService:
    return AssetService()


def _http_error(
    *,
    status_code: int,
    error_code: str,
    message: str,
):
    raise HTTPException(
        status_code=status_code,
        detail={"error_code": error_code, "message": message},
    )


def _validate_filename(upload: UploadFile) -> str:
    filename = (upload.filename or "").strip()
    is_path_like = (
        PurePosixPath(filename).name != filename
        or PureWindowsPath(filename).name != filename
    )
    has_control_characters = any(
        character in filename for character in ("\x00", "\r", "\n")
    )
    if (
        not filename
        or filename in {".", ".."}
        or is_path_like
        or has_control_characters
    ):
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_FILENAME",
            message="Nome de arquivo invalido.",
        )
    return filename


def _validate_file_type(
    upload: UploadFile,
    filename: str,
    *,
    allowed_file_types: dict[str, set[str]],
    default_content_types: dict[str, str],
    message: str,
) -> str:
    suffix = Path(filename).suffix.lower()
    allowed_content_types = allowed_file_types.get(suffix)
    if not allowed_content_types:
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="UNSUPPORTED_FILE_TYPE",
            message=message,
        )

    normalized_content_type = (upload.content_type or "").lower().strip()
    if normalized_content_type and normalized_content_type not in allowed_content_types:
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="UNSUPPORTED_FILE_TYPE",
            message=message,
        )

    if normalized_content_type:
        return normalized_content_type

    return default_content_types[suffix]


def _validate_image_category(asset_category: str) -> str:
    normalized_category = (asset_category or "").strip()
    if normalized_category not in ALLOWED_IMAGE_CATEGORIES:
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_ASSET_CATEGORY",
            message="Categoria de asset invalida.",
        )
    return normalized_category


def _validate_file_size(
    upload: UploadFile,
    *,
    too_large_message: str,
) -> int:
    upload.file.seek(0, 2)
    size_bytes = upload.file.tell()
    upload.file.seek(0)

    if size_bytes <= 0:
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="EMPTY_FILE",
            message="O arquivo enviado esta vazio.",
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        _http_error(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_code="FILE_TOO_LARGE",
            message=too_large_message,
        )

    return size_bytes


@router.get(
    "/onboarding/{onboarding_id}",
    response_model=UploadedAssetListEnvelope,
)
async def list_onboarding_assets(
    onboarding_id: int,
    _current_user=Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(select(Onboarding).where(Onboarding.id == onboarding_id))
    onboarding = result.scalars().first()
    if onboarding is None:
        _http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ONBOARDING_NOT_FOUND",
            message="Onboarding nao encontrado.",
        )

    assets_result = await db.execute(
        select(UploadedAsset)
        .where(UploadedAsset.onboarding_id == onboarding_id)
        .order_by(UploadedAsset.created_at.asc(), UploadedAsset.id.asc())
    )
    return {"data": assets_result.scalars().all()}


@router.post(
    "/upload",
    response_model=UploadedAssetEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    onboarding_id: int = Form(...),
    file: UploadFile = File(...),
    _current_user=Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
    asset_service: AssetService = Depends(get_asset_service),
):
    filename = _validate_filename(file)
    content_type = _validate_file_type(
        file,
        filename,
        allowed_file_types=TRANSCRIPTION_ALLOWED_FILE_TYPES,
        default_content_types=TRANSCRIPTION_DEFAULT_CONTENT_TYPES,
        message="Apenas arquivos PDF, TXT ou DOCX sao permitidos.",
    )
    size_bytes = _validate_file_size(
        file,
        too_large_message="O limite de upload para transcricoes e de 50MB.",
    )

    result = await db.execute(
        select(Onboarding).where(Onboarding.id == onboarding_id)
    )
    onboarding = result.scalars().first()
    if onboarding is None:
        _http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ONBOARDING_NOT_FOUND",
            message="Onboarding nao encontrado.",
        )

    try:
        object_key = asset_service.upload_transcription(
            onboarding_id=onboarding_id,
            file_obj=file.file,
            original_filename=filename,
            content_type=content_type,
        )
    except Exception:
        _http_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ASSET_UPLOAD_FAILED",
            message="Nao foi possivel enviar o arquivo para o storage.",
        )

    uploaded_asset = UploadedAsset(
        onboarding_id=onboarding_id,
        asset_kind="transcription",
        original_filename=filename,
        object_key=object_key,
        content_type=content_type,
        size_bytes=size_bytes,
    )

    db.add(uploaded_asset)
    try:
        await db.commit()
        await db.refresh(uploaded_asset)
    except Exception:
        await db.rollback()
        try:
            asset_service.delete_object(object_key)
        except Exception:
            pass
        _http_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ASSET_UPLOAD_FAILED",
            message="Nao foi possivel salvar os metadados do upload.",
        )

    return {"data": uploaded_asset}


@router.post(
    "/upload-image",
    response_model=UploadedAssetEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image_asset(
    onboarding_id: int = Form(...),
    asset_category: str | None = Form(None),
    file: UploadFile = File(...),
    _current_user=Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
    asset_service: AssetService = Depends(get_asset_service),
):
    normalized_category = _validate_image_category(asset_category)
    filename = _validate_filename(file)
    content_type = _validate_file_type(
        file,
        filename,
        allowed_file_types=IMAGE_ALLOWED_FILE_TYPES,
        default_content_types=IMAGE_DEFAULT_CONTENT_TYPES,
        message="Apenas imagens JPG, PNG, WebP, HEIC ou HEIF sao permitidas.",
    )
    size_bytes = _validate_file_size(
        file,
        too_large_message="O limite de upload para assets fotograficos e de 50MB.",
    )

    result = await db.execute(select(Onboarding).where(Onboarding.id == onboarding_id))
    onboarding = result.scalars().first()
    if onboarding is None:
        _http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ONBOARDING_NOT_FOUND",
            message="Onboarding nao encontrado.",
        )

    try:
        object_key = asset_service.upload_image(
            onboarding_id=onboarding_id,
            asset_category=normalized_category,
            file_obj=file.file,
            original_filename=filename,
            content_type=content_type,
        )
        storage_url = asset_service.build_storage_url(object_key)
    except Exception:
        _http_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ASSET_UPLOAD_FAILED",
            message="Nao foi possivel enviar o arquivo para o storage.",
        )

    uploaded_asset = UploadedAsset(
        onboarding_id=onboarding_id,
        asset_kind="image",
        asset_category=normalized_category,
        original_filename=filename,
        object_key=object_key,
        storage_url=storage_url,
        content_type=content_type,
        size_bytes=size_bytes,
    )

    db.add(uploaded_asset)
    try:
        await db.commit()
        await db.refresh(uploaded_asset)
    except Exception:
        await db.rollback()
        try:
            asset_service.delete_object(object_key)
        except Exception:
            pass
        _http_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ASSET_UPLOAD_FAILED",
            message="Nao foi possivel salvar os metadados do upload.",
        )

    return {"data": uploaded_asset}
