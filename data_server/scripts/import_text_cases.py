from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.db import SessionLocal
from repositories.case_repository import CaseRepository
from services.case_import_parser import load_text_file
from schemas.case_schema import CaseCreate


def collect_text_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(input_path.glob("*.txt"))


def import_text_cases(input_path: Path) -> None:
    files = collect_text_files(input_path)
    if not files:
        print(f"No text files found: {input_path}")
        return

    created = 0
    updated = 0
    failed = 0

    db = SessionLocal()
    repository = CaseRepository(db)

    try:
        for file_path in files:
            for item in load_text_file(file_path):
                try:
                    case_data = CaseCreate.model_validate(item)
                    _, was_created = repository.upsert(case_data)
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except (ValidationError, IntegrityError, ValueError) as exc:
                    db.rollback()
                    failed += 1
                    print(f"Failed to import item from {file_path}: {exc}")
    finally:
        db.close()

    print(f"Text import complete. created={created}, updated={updated}, failed={failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import text legal data files into PostgreSQL.")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="data/raw_cases",
        help="Path to a text file or directory containing .txt files.",
    )
    args = parser.parse_args()

    import_text_cases(Path(args.input_path))


if __name__ == "__main__":
    main()
