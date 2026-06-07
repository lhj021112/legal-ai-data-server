from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class CaseBase(BaseModel):
    case_id: str
    title: Optional[str] = None
    court: Optional[str] = None
    case_number: Optional[str] = None
    decision_date: Optional[date] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    issue: Optional[str] = None
    summary: Optional[str] = None
    facts: Optional[str] = None
    judgment: Optional[str] = None
    reasoning: Optional[str] = None
    search_text: str = Field(..., min_length=1)
    raw_json: Optional[Union[Dict[str, Any], List[Any]]] = None


class CaseCreate(CaseBase):
    pass


class CaseResponse(CaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CaseListResponse(BaseModel):
    total: int
    items: List[CaseResponse]


class CaseSearchResponse(CaseListResponse):
    pass
