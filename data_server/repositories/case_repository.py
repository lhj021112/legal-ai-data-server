from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.case_model import Case
from schemas.case_schema import CaseCreate


class CaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, case_data: CaseCreate) -> Case:
        case = Case(**case_data.model_dump())
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def upsert(self, case_data: CaseCreate) -> tuple[Case, bool]:
        existing_case = self.get_by_case_id(case_data.case_id)
        if not existing_case:
            return self.create(case_data), True

        for field, value in case_data.model_dump().items():
            setattr(existing_case, field, value)

        self.db.commit()
        self.db.refresh(existing_case)
        return existing_case, False

    def get_by_case_id(self, case_id: str) -> Case | None:
        statement = select(Case).where(Case.case_id == case_id)
        return self.db.scalar(statement)

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        updated_after: datetime | None = None,
    ) -> list[Case]:
        statement = select(Case)
        if updated_after is not None:
            statement = statement.where(Case.updated_at > updated_after)

        statement = statement.order_by(Case.id.asc()).limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def count(self, updated_after: datetime | None = None) -> int:
        statement = select(func.count()).select_from(Case)
        if updated_after is not None:
            statement = statement.where(Case.updated_at > updated_after)

        return int(self.db.scalar(statement) or 0)

    def search(self, query: str, limit: int = 50) -> list[Case]:
        pattern = f"%{query}%"
        statement = (
            select(Case)
            .where(
                or_(
                    Case.search_text.ilike(pattern),
                    Case.title.ilike(pattern),
                    Case.issue.ilike(pattern),
                    Case.summary.ilike(pattern),
                )
            )
            .order_by(Case.decision_date.desc().nullslast(), Case.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())
