from datetime import UTC, datetime

from sqlalchemy import select, update
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
        search_sources: str | None = None,
        auto_commit: bool = True,
    ) -> GeneratedDocument:
        # Before saving new document, mark old ones as not current
        # (requires is_current column — added via migration)
        if hasattr(GeneratedDocument, "is_current"):
            await db.execute(
                update(GeneratedDocument)
                .where(
                    GeneratedDocument.onboarding_id == onboarding_id,
                    GeneratedDocument.step_name == step_name,
                    GeneratedDocument.is_current == True,  # noqa: E712
                )
                .values(is_current=False)
            )

        result = await db.execute(
            select(GeneratedDocument).where(
                GeneratedDocument.onboarding_id == onboarding_id,
                GeneratedDocument.document_kind == document_kind,
            )
        )
        document = result.scalars().first()
        now = datetime.now(UTC)

        if document is None:
            new_doc_kwargs: dict = dict(
                onboarding_id=onboarding_id,
                step_name=step_name,
                agent_name=agent_name,
                document_kind=document_kind,
                title=title,
                markdown_content=markdown_content,
                review_status=review_status,
                review_feedback=review_feedback,
                reviewed_at=reviewed_at,
                search_sources=search_sources,
                updated_at=now,
            )
            if hasattr(GeneratedDocument, "is_current"):
                new_doc_kwargs["is_current"] = True
            document = GeneratedDocument(**new_doc_kwargs)
            db.add(document)
        else:
            document.step_name = step_name
            document.agent_name = agent_name
            document.title = title
            document.markdown_content = markdown_content
            document.review_status = review_status
            document.review_feedback = review_feedback
            document.reviewed_at = reviewed_at
            if search_sources is not None:
                document.search_sources = search_sources
            document.updated_at = now
            if hasattr(document, "is_current"):
                document.is_current = True

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
