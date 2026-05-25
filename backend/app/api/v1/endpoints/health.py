from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from botocore.exceptions import ClientError

from app.api import deps
from app.core.config import settings
from app.services.asset_service import AssetService

router = APIRouter()

@router.get("")
async def health_check(db: AsyncSession = Depends(deps.get_db)):
    health_status = {
        "status": "ok",
        "database": "unknown",
        "redis": "unknown",
        "minio": "unknown"
    }

    # Check Database
    try:
        await db.execute(text("SELECT 1"))
        health_status["database"] = "ok"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "error"

    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        health_status["redis"] = "ok"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "error"

    # Check MinIO
    try:
        asset_service = AssetService()
        asset_service.client.head_bucket(Bucket=settings.MINIO_BUCKET)
        health_status["minio"] = "ok"
    except ClientError as e:
        # If bucket doesn't exist (404), MinIO is up but bucket is missing. Let's still mark as error for the app context.
        health_status["minio"] = f"error: {str(e)}"
        health_status["status"] = "error"
    except Exception as e:
        health_status["minio"] = f"error: {str(e)}"
        health_status["status"] = "error"

    if health_status["status"] != "ok":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status
