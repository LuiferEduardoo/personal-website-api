from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import get_async_session, get_sync_session

AsyncDBSession = Annotated[AsyncSession, Depends(get_async_session)]
SyncDBSession = Annotated[Session, Depends(get_sync_session)]
