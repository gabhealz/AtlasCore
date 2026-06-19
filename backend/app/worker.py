"""Celery application configuration.

Uses Redis as both broker and result backend.
Import this module to access the shared Celery app instance.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "atlas_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Beat schedule — runs every 6 hours
    beat_schedule={
        "sync-all-clients-every-6h": {
            "task": "app.tasks.sync_ads.sync_all_clients",
            "schedule": 6 * 60 * 60,  # 6 hours in seconds
        },
    },
)

# Auto-discover tasks in the app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])

# Explicit imports to guarantee task registration
import app.tasks.sync_ads  # noqa: F401, E402


# Resolve SQLAlchemy mappers in each worker process AFTER the prefork fork.
# configure_mappers() pre-fork é insuficiente porque o fork pode capturar estado parcial.
from celery.signals import worker_process_init  # noqa: E402


@worker_process_init.connect
def _init_sqlalchemy_mappers(**kwargs):  # noqa: ANN003
    import app.db.base  # noqa: F401 — registra todos os modelos
    from sqlalchemy.orm import configure_mappers
    configure_mappers()
