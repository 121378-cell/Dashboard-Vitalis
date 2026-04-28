"""
ATLAS Memory API Endpoints
===========================

REST endpoints for managing ATLAS Long-Term Memory (LTM).

Autor: ATLAS Team
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.deps import get_db
from app.services.memory_service import MemoryService

router = APIRouter()


class MemoryEntryRequest(BaseModel):
    type: str  # injury, achievement, pattern, preference, milestone
    content: str
    date: Optional[str] = None  # YYYY-MM-DD, default today
    importance: int = 5  # 1-10
    source: str = "user"


class MemoryEntryResponse(BaseModel):
    id: int
    type: str
    content: str
    date: str
    importance: int
    source: str


class MemorySummaryResponse(BaseModel):
    memories: List[dict]
    count: int
    period_days: int


@router.get("/summary", response_model=MemorySummaryResponse)
def get_memory_summary(
    days: int = 90,
    types: Optional[str] = None,  # comma-separated list
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Get memory summary for AI context injection.

    - days: how far back to look (default 90)
    - types: comma-separated filter (e.g. "injury,achievement")
    """
    type_list = types.split(",") if types else None
    result = MemoryService.get_memory_summary(db, user_id, days=days, types=type_list)
    return MemorySummaryResponse(**result)


@router.post("/entry", response_model=MemoryEntryResponse)
def create_memory_entry(
    request: MemoryEntryRequest,
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """Manually add a memory entry."""
    if request.type not in ("injury", "achievement", "pattern", "preference", "milestone"):
        raise HTTPException(status_code=400, detail=f"Invalid memory type: {request.type}")

    entry = MemoryService.add_memory(
        db=db,
        user_id=user_id,
        memory_type=request.type,
        content=request.content,
        importance=request.importance,
        memory_date=request.date,
        source=request.source
    )

    return MemoryEntryResponse(
        id=entry.id,
        type=entry.type,
        content=entry.content,
        date=entry.date,
        importance=entry.importance,
        source=entry.source
    )
