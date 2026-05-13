from __future__ import annotations

import argparse
import csv
import hashlib
import io
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


def make_case_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def parse_json_text(text: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    if not text.startswith(("{", "[")):
        return None

    try:
        data, _ = json.JSONDecoder().raw_decode(text)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        return data
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    return None


def parse_law_csv_text(path: Path, text: str) -> list[dict[str, Any]] | None:
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if first_line != "law,article,title,summary":
        return None

    rows = csv.DictReader(io.StringIO(text))
    cases: list[dict[str, Any]] = []

    for row in rows:
        law = (row.get("law") or "").strip()
        article = (row.get("article") or "").strip()
        title = (row.get("title") or "").strip()
        summary = (row.get("summary") or "").strip()
        unique_value = f"{path.name}:{law}:{article}:{title}:{summary}"

        cases.append(
            {
                "case_id": make_case_id("law", unique_value),
                "title": f"{law} {article} {title}".strip(),
                "court": None,
                "case_number": article,
                "decision_date": None,
                "category": "법령",
                "sub_category": law,
                "issue": title,
                "summary": summary,
                "facts": None,
                "judgment": None,
                "reasoning": None,
                "search_text": " ".join(part for part in [law, article, title, summary] if part),
                "raw_json": {
                    "source_file": path.name,
                    "format": "law_csv_text",
                    "row": row,
                },
            }
        )

    return cases


def parse_plain_text(path: Path, text: str) -> dict[str, Any]:
    title = path.stem
    return {
        "case_id": make_case_id("txt", f"{path.name}:{text}"),
        "title": title,
        "court": None,
        "case_number": None,
        "decision_date": None,
        "category": "텍스트",
        "sub_category": None,
        "issue": title,
        "summary": text[:500],
        "facts": None,
        "judgment": None,
        "reasoning": None,
        "search_text": text,
        "raw_json": {
            "source_file": path.name,
            "format": "plain_text",
            "text": text,
        },
    }


def parse_text_file(path: Path) -> list[dict[str, Any]]:
    text = read_text(path)
    if not text:
        return []

    json_data = parse_json_text(text)
    if isinstance(json_data, list):
        return json_data
    if isinstance(json_data, dict):
        return [json_data]

    law_csv_data = parse_law_csv_text(path, text)
    if law_csv_data is not None:
        return law_csv_data

    return [parse_plain_text(path, text)]


def preserve_raw_json(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("raw_json") is None:
        item = {**item, "raw_json": item.copy()}
    return item


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
    skipped = 0
    failed = 0

    db = SessionLocal()
    repository = CaseRepository(db)

    try:
        for file_path in files:
            for item in parse_text_file(file_path):
                try:
                    item = preserve_raw_json(item)
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

    print(f"Text import complete. created={created}, skipped={skipped}, failed={failed}")


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
