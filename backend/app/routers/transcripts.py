"""Transcript routes — upload, list, and parse transcriptions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas import TranscriptResponse, TranscriptCreate

router = APIRouter(prefix="/clients/{client_id}/transcripts", tags=["transcripts"])


async def _get_client_or_404(client_id: UUID, user: User, db: AsyncSession) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.owner_id == user.id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


@router.get("/", response_model=list[TranscriptResponse])
async def list_transcripts(
    client_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all transcripts for a client."""
    await _get_client_or_404(client_id, user, db)
    result = await db.execute(
        select(Transcript)
        .where(Transcript.client_id == client_id)
        .order_by(Transcript.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=TranscriptResponse, status_code=status.HTTP_201_CREATED)
async def create_transcript(
    client_id: UUID,
    data: TranscriptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a transcript from raw text (manual input)."""
    client = await _get_client_or_404(client_id, user, db)

    transcript = Transcript(
        client_id=client_id,
        uploaded_by=user.id,
        title=data.title,
        source=data.source,
        raw_text=data.raw_text,
    )
    db.add(transcript)
    await db.flush()
    await db.refresh(transcript)

    # Update client status
    if client.status == "data_pending":
        client.status = "transcript_uploaded"

    return transcript


@router.post("/upload", response_model=TranscriptResponse, status_code=status.HTTP_201_CREATED)
async def upload_transcript(
    client_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    source: str = Form(default="manual"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a transcript file (.txt, .docx, .pdf) and extract text."""
    client = await _get_client_or_404(client_id, user, db)

    # Read file content
    content = await file.read()
    file_type = file.content_type or ""
    file_name = file.filename or "unknown"

    # Extract text based on file type
    raw_text = ""

    if file_name.endswith(".txt") or "text/plain" in file_type:
        raw_text = content.decode("utf-8", errors="replace")

    elif file_name.endswith(".docx"):
        import io
        from docx import Document
        doc = Document(io.BytesIO(content))
        raw_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif file_name.endswith(".pdf"):
        import io
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content))
        raw_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Formato não suportado. Use .txt, .docx ou .pdf",
        )

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Não foi possível extrair texto do arquivo")

    transcript = Transcript(
        client_id=client_id,
        uploaded_by=user.id,
        title=title,
        source=source,
        raw_text=raw_text,
        file_name=file_name,
        file_type=file_type,
    )
    db.add(transcript)
    await db.flush()
    await db.refresh(transcript)

    # Update client status
    if client.status == "data_pending":
        client.status = "transcript_uploaded"

    return transcript


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(
    client_id: UUID,
    transcript_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific transcript."""
    await _get_client_or_404(client_id, user, db)
    result = await db.execute(
        select(Transcript).where(
            Transcript.id == transcript_id, Transcript.client_id == client_id
        )
    )
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")
    return transcript


@router.delete("/{transcript_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcript(
    client_id: UUID,
    transcript_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a transcript."""
    await _get_client_or_404(client_id, user, db)
    result = await db.execute(
        select(Transcript).where(
            Transcript.id == transcript_id, Transcript.client_id == client_id
        )
    )
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")
    await db.delete(transcript)
