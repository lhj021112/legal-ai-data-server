from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.db import get_db
from schemas.case_schema import CaseCreate, CaseResponse, CaseSearchResponse
from services.case_service import CaseService


router = APIRouter()


@router.post("/cases", response_model=CaseResponse, status_code=201)
def create_case(case_data: CaseCreate, db: Session = Depends(get_db)):
    return CaseService(db).create_case(case_data)


@router.get("/cases/search", response_model=CaseSearchResponse)
def search_cases(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    cases = CaseService(db).search_cases(q)
    return CaseSearchResponse(total=len(cases), items=cases)


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    return CaseService(db).get_case(case_id)
