from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.db import get_db
from schemas.law_schema import LawSearchResponse
from services.law_service import LawService


router = APIRouter()


@router.get("/laws/search", response_model=LawSearchResponse, response_model_exclude_none=True)
def search_laws(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    offset: int = Query(default=0, ge=0),
    include_total: bool = Query(default=False),
    snapshot: bool = Query(default=False),
    as_of: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = q.strip()
    if not q:
        raise HTTPException(status_code=422, detail="검색어를 입력해 주세요.")
    if snapshot and as_of is not None:
        raise HTTPException(status_code=422, detail="저장본 조회에는 기준일을 함께 지정할 수 없습니다.")
    return LawService(db).search(
        q=q, limit=limit, offset=offset, as_of=as_of or date.today(),
        include_total=include_total, snapshot_mode=snapshot,
    )
