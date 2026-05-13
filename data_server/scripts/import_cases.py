from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.db import SessionLocal
from repositories.case_repository import CaseRepository
from schemas.case_schema import CaseCreate


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"Unsupported JSON format: {path}")


def collect_json_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(input_path.glob("*.json"))


def import_cases(input_path: Path) -> None:
    files = collect_json_files(input_path)
    if not files:
        print(f"No JSON files found: {input_path}")
        return

    created = 0
    skipped = 0
    failed = 0

    db = SessionLocal()
    repository = CaseRepository(db)

    try:
        for file_path in files:
            for item in load_json(file_path):
                try:
                    case_data = CaseCreate.model_validate(item)
                    if repository.get_by_case_id(case_data.case_id):
                        skipped += 1
                        continue

                    repository.create(case_data)
                    created += 1
                except (ValidationError, IntegrityError, ValueError) as exc:
                    db.rollback()
                    failed += 1
                    print(f"Failed to import item from {file_path}: {exc}")
    finally:
        db.close()

    print(f"Import complete. created={created}, skipped={skipped}, failed={failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legal case JSON files into PostgreSQL.")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="data/raw_cases",
        help="Path to a JSON file or directory containing JSON files.",
    )
    args = parser.parse_args()

    import_cases(Path(args.input_path))


if __name__ == "__main__":
    main()
