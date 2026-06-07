from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import verify_admin_api_key
from schemas.case_schema import CaseCreate, CaseListResponse, CaseResponse, CaseSearchResponse
from services.case_import_parser import parse_text_content
from services.case_service import CaseService


router = APIRouter()


@router.post(
    "/cases",
    response_model=CaseResponse,
    status_code=201,
    dependencies=[Depends(verify_admin_api_key)],
)
def create_case(case_data: CaseCreate, db: Session = Depends(get_db)):
    return CaseService(db).create_case(case_data)


@router.get("/cases", response_model=CaseListResponse)
def list_cases(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    updated_after: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
):
    total, cases = CaseService(db).list_cases(
        limit=limit,
        offset=offset,
        updated_after=updated_after,
    )
    return CaseListResponse(total=total, items=cases)


@router.get("/cases/search", response_model=CaseSearchResponse)
def search_cases(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    cases = CaseService(db).search_cases(q)
    return CaseSearchResponse(total=len(cases), items=cases)


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    return CaseService(db).get_case(case_id)


@router.post("/cases/import-file", dependencies=[Depends(verify_admin_api_key)])
async def import_case_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    text = content.decode("utf-8-sig")
    case_items = parse_text_content(file.filename or "uploaded_file", text)
    result = CaseService(db).import_cases(case_items)
    return {
        "filename": file.filename,
        "total": len(case_items),
        **result,
    }
