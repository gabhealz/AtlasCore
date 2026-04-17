"""Benchmark routes — trigger generation, view results, approve/reject."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.transcript import Transcript
from app.models.benchmark import Benchmark
from app.models.user import User
from app.schemas import BenchmarkResponse, BenchmarkApproval

router = APIRouter(prefix="/clients/{client_id}/benchmarks", tags=["benchmarks"])


async def _get_client_or_404(client_id: UUID, user: User, db: AsyncSession) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.owner_id == user.id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


@router.get("/", response_model=list[BenchmarkResponse])
async def list_benchmarks(
    client_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all benchmarks for a client."""
    await _get_client_or_404(client_id, user, db)
    result = await db.execute(
        select(Benchmark)
        .where(Benchmark.client_id == client_id)
        .order_by(Benchmark.created_at.desc())
    )
    return result.scalars().all()


@router.post("/generate", response_model=BenchmarkResponse, status_code=status.HTTP_201_CREATED)
async def generate_benchmark(
    client_id: UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger benchmark generation using AI agent.

    This creates a benchmark record in 'generating' status and starts
    the AI processing in the background.
    """
    client = await _get_client_or_404(client_id, user, db)

    # Check that at least one transcript exists
    result = await db.execute(
        select(Transcript).where(Transcript.client_id == client_id)
    )
    transcripts = result.scalars().all()
    if not transcripts:
        raise HTTPException(
            status_code=400,
            detail="É necessário pelo menos uma transcrição para gerar o benchmark",
        )

    # Create benchmark record
    benchmark = Benchmark(
        client_id=client_id,
        generated_by=user.id,
        status="generating",
        content={},
    )
    db.add(benchmark)
    await db.flush()
    await db.refresh(benchmark)

    # Queue background task for AI generation
    # NOTE: The actual benchmark_service will be called here once OpenAI API key is available
    # For now, we create the record and the service can be triggered manually
    # background_tasks.add_task(run_benchmark_generation, str(benchmark.id))

    return benchmark


@router.get("/{benchmark_id}", response_model=BenchmarkResponse)
async def get_benchmark(
    client_id: UUID,
    benchmark_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific benchmark."""
    await _get_client_or_404(client_id, user, db)
    result = await db.execute(
        select(Benchmark).where(
            Benchmark.id == benchmark_id, Benchmark.client_id == client_id
        )
    )
    benchmark = result.scalar_one_or_none()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark não encontrado")
    return benchmark


@router.post("/{benchmark_id}/approve", response_model=BenchmarkResponse)
async def approve_benchmark(
    client_id: UUID,
    benchmark_id: UUID,
    data: BenchmarkApproval,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a benchmark (HITL)."""
    client = await _get_client_or_404(client_id, user, db)
    result = await db.execute(
        select(Benchmark).where(
            Benchmark.id == benchmark_id, Benchmark.client_id == client_id
        )
    )
    benchmark = result.scalar_one_or_none()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark não encontrado")

    if benchmark.status not in ("draft", "generating"):
        raise HTTPException(status_code=400, detail="Benchmark não está em status de revisão")

    if data.approved:
        benchmark.status = "approved"
        benchmark.approved_by = user.id
        benchmark.approved_at = datetime.now(timezone.utc)
        client.status = "benchmark_approved"
    else:
        benchmark.status = "rejected"
        benchmark.rejection_notes = data.notes

    await db.flush()
    await db.refresh(benchmark)
    return benchmark
