from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text

from app.dependencies.db import AsyncDBSession

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str


@router.get("", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check(session: AsyncDBSession) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"
    return HealthResponse(status="ok", database=db_status)
