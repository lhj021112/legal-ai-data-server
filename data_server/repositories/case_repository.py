from __future__ import annotations

from sqlalchemy import or_, select
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
