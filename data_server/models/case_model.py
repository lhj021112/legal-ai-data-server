from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union

from sqlalchemy import Date, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(nullable=True)
    court: Mapped[Optional[str]] = mapped_column(nullable=True)
    case_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(nullable=True)
    issue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    facts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    judgment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_json: Mapped[Optional[Union[dict, list]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
