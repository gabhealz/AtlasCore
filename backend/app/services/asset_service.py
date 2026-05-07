import re
from io import BytesIO
from uuid import uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from docx import Document
from pypdf import PdfReader

from app.core.config import settings


class AssetService:
    def __init__(self):
        session = boto3.session.Session()
        self.bucket_name = settings.MINIO_BUCKET
        self.region_name = settings.MINIO_REGION
        self.public_base_url = settings.MINIO_PUBLIC_URL.rstrip("/")
        self.client = session.client(
            "s3",
            endpoint_url=settings.MINIO_URL,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name=self.region_name,
            config=BotoConfig(s3={"addressing_style": "path"}),
        )

    def ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return
        except ClientError:
            pass

        create_bucket_kwargs = {"Bucket": self.bucket_name}
        if self.region_name != "us-east-1":
            create_bucket_kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": self.region_name
            }

        self.client.create_bucket(**create_bucket_kwargs)

    def _sanitize_filename(self, original_filename: str) -> str:
        safe_filename = re.sub(r"[^A-Za-z0-9._-]+", "-", original_filename).strip("-")
        if not safe_filename:
            return "upload"

        return safe_filename

    def _build_object_key(
        self,
        *,
        onboarding_id: int,
        original_filename: str,
        kind: str,
        asset_category: str | None = None,
    ) -> str:
        safe_filename = self._sanitize_filename(original_filename)

        if kind == "transcription":
            prefix = f"onboardings/{onboarding_id}/transcriptions"
        elif kind == "image" and asset_category:
            prefix = f"onboardings/{onboarding_id}/images/{asset_category}"
        else:
            prefix = f"onboardings/{onboarding_id}/uploads"

        return f"{prefix}/{uuid4()}-{safe_filename}"

    def build_storage_url(self, object_key: str) -> str:
        return f"{self.public_base_url}/{self.bucket_name}/{object_key}"

    def _upload_file(
        self,
        *,
        object_key: str,
        file_obj,
        content_type: str,
    ) -> None:
        self.ensure_bucket_exists()
        self.client.upload_fileobj(
            Fileobj=file_obj,
            Bucket=self.bucket_name,
            Key=object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def upload_transcription(
        self,
        *,
        onboarding_id: int,
        file_obj,
        original_filename: str,
        content_type: str,
    ) -> str:
        object_key = self._build_object_key(
            onboarding_id=onboarding_id,
            original_filename=original_filename,
            kind="transcription",
        )
        self._upload_file(
            object_key=object_key,
            file_obj=file_obj,
            content_type=content_type,
        )
        return object_key

    def upload_image(
        self,
        *,
        onboarding_id: int,
        asset_category: str,
        file_obj,
        original_filename: str,
        content_type: str,
    ) -> str:
        object_key = self._build_object_key(
            onboarding_id=onboarding_id,
            original_filename=original_filename,
            kind="image",
            asset_category=asset_category,
        )
        self._upload_file(
            object_key=object_key,
            file_obj=file_obj,
            content_type=content_type,
        )
        return object_key

    def delete_object(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=object_key)

    def read_binary_object(self, object_key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()

    def read_text_object(self, object_key: str, *, encoding: str = "utf-8") -> str:
        raw_content = self.read_binary_object(object_key)

        return raw_content.decode(encoding, errors="ignore")

    def read_pdf_object(self, object_key: str) -> str:
        raw_content = self.read_binary_object(object_key)
        reader = PdfReader(BytesIO(raw_content))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                pages.append(page_text.strip())
        return "\n\n".join(pages).strip()

    def read_docx_object(self, object_key: str) -> str:
        raw_content = self.read_binary_object(object_key)
        document = Document(BytesIO(raw_content))
        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        return "\n\n".join(paragraphs).strip()
