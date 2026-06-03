from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from repositories.case_repository import CaseRepository
from schemas.case_schema import CaseCreate


class CaseService:
    def __init__(self, db: Session):
        self.repository = CaseRepository(db)

    def create_case(self, case_data: CaseCreate):
        existing_case = self.repository.get_by_case_id(case_data.case_id)
        if existing_case:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Case already exists: {case_data.case_id}",
            )

        try:
            return self.repository.create(case_data)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to create case because of a database constraint.",
            ) from exc

    def get_case(self, case_id: str):
        case = self.repository.get_by_case_id(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case not found: {case_id}",
            )
        return case

    def search_cases(self, query: str):
        cleaned_query = query.strip()
        if not cleaned_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must not be empty.",
            )
        return self.repository.search(cleaned_query)

    def import_cases(self, case_items: list[dict]):
        created = 0
        updated = 0
        failed = 0
        errors = []

        for item in case_items:
            try:
                case_data = CaseCreate.model_validate(item)
                _, was_created = self.repository.upsert(case_data)
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                failed += 1
                errors.append(str(exc))

        return {
            "created": created,
            "updated": updated,
            "failed": failed,
            "errors": errors[:10],
        }
