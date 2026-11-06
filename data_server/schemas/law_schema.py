from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LawArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    law_id: str = Field(min_length=1)
    law_name: str = Field(min_length=1)
    article_number: str = Field(min_length=1)
    text: str = Field(min_length=1)
    effective_from: date
    effective_to: Optional[date] = None
    source_url: str = Field(pattern=r"^https://www\.law\.go\.kr/[^\s]+$")
    retrieved_at: date


class LawSearchResponse(BaseModel):
    items: list[LawArticle]
    as_of: date
    warnings: list[str]
    total: Optional[int] = Field(default=None, ge=0)
