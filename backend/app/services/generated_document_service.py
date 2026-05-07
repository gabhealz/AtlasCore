from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generated_document import GeneratedDocument

DOCUMENT_REVIEW_STATUS_AWAITING = "AWAITING_REVIEW"
DOCUMENT_REVIEW_STATUS_APPROVED = "APPROVED"
DOCUMENT_REVIEW_STATUS_REJECTED = "REJECTED"


class GeneratedDocumentService:
    async def save_document(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
        step_name: str,
        agent_name: str,
        document_kind: str,
        title: str,
        markdown_content: str,
        review_status: str = DOCUMENT_REVIEW_STATUS_APPROVED,
        review_feedback: str | None = None,
        reviewed_at: datetime | None = None,
        auto_commit: bool = True,
    ) -> GeneratedDocument:
        result = await db.execute(
            select(GeneratedDocument).where(
                GeneratedDocument.onboarding_id == onboarding_id,
                GeneratedDocument.document_kind == document_kind,
            )
        )
        document = result.scalars().first()
        now = datetime.now(UTC)

        if document is None:
            document = GeneratedDocument(
                onboarding_id=onboarding_id,
                step_name=step_name,
                agent_name=agent_name,
                document_kind=document_kind,
                title=title,
                markdown_content=markdown_content,
                review_status=review_status,
                review_feedback=review_feedback,
                reviewed_at=reviewed_at,
                updated_at=now,
            )
            db.add(document)
        else:
            document.step_name = step_name
            document.agent_name = agent_name
            document.title = title
            document.markdown_content = markdown_content
            document.review_status = review_status
            document.review_feedback = review_feedback
            document.reviewed_at = reviewed_at
            document.updated_at = now

        if auto_commit:
            await db.commit()
            await db.refresh(document)
        else:
            await db.flush()
        return document

    async def list_documents(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
        review_status: str | None = None,
    ) -> list[GeneratedDocument]:
        query = (
            select(GeneratedDocument)
            .where(GeneratedDocument.onboarding_id == onboarding_id)
            .order_by(GeneratedDocument.created_at.asc(), GeneratedDocument.id.asc())
        )
        if review_status is not None:
            query = query.where(GeneratedDocument.review_status == review_status)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_pending_document(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
        for_update: bool = False,
    ) -> GeneratedDocument | None:
        query = (
            select(GeneratedDocument)
            .where(
                GeneratedDocument.onboarding_id == onboarding_id,
                GeneratedDocument.review_status == DOCUMENT_REVIEW_STATUS_AWAITING,
            )
            .order_by(GeneratedDocument.updated_at.desc(), GeneratedDocument.id.desc())
        )
        if for_update:
            query = query.with_for_update()

        result = await db.execute(query)
        return result.scalars().first()

    async def apply_human_review(
        self,
        *,
        db: AsyncSession,
        document: GeneratedDocument,
        review_status: str,
        title: str | None = None,
        markdown_content: str | None = None,
        review_feedback: str | None = None,
        reviewed_at: datetime | None = None,
        auto_commit: bool = True,
    ) -> GeneratedDocument:
        now = reviewed_at or datetime.now(UTC)
        resolved_reviewed_at = reviewed_at
        if resolved_reviewed_at is None and review_status in {
            DOCUMENT_REVIEW_STATUS_APPROVED,
            DOCUMENT_REVIEW_STATUS_REJECTED,
        }:
            resolved_reviewed_at = now

        if title is not None:
            document.title = title
        if markdown_content is not None:
            document.markdown_content = markdown_content

        document.review_status = review_status
        document.review_feedback = review_feedback
        document.reviewed_at = resolved_reviewed_at
        document.updated_at = now

        if auto_commit:
            await db.commit()
            await db.refresh(document)
        else:
            await db.flush()
        return document
