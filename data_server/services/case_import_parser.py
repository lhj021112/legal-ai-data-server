from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any


def make_case_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def parse_json_text(text: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    stripped_text = text.strip()
    if not stripped_text.startswith(("{", "[")):
        return None

    try:
        data, _ = json.JSONDecoder().raw_decode(stripped_text)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        return data
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    return None


def parse_law_csv_text(source_name: str, text: str) -> list[dict[str, Any]] | None:
    lines = text.splitlines()
    first_line = lines[0].strip() if lines else ""
    if first_line != "law,article,title,summary":
        return None

    rows = csv.DictReader(io.StringIO(text))
    cases: list[dict[str, Any]] = []

    for row in rows:
        law = (row.get("law") or "").strip()
        article = (row.get("article") or "").strip()
        title = (row.get("title") or "").strip()
        summary = (row.get("summary") or "").strip()
        unique_value = f"{source_name}:{law}:{article}:{title}:{summary}"

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
                    "source_file": source_name,
                    "format": "law_csv_text",
                    "row": row,
                },
            }
        )

    return cases


def parse_plain_text(source_name: str, text: str) -> dict[str, Any]:
    title = Path(source_name).stem
    return {
        "case_id": make_case_id("txt", f"{source_name}:{text}"),
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
            "source_file": source_name,
            "format": "plain_text",
            "text": text,
        },
    }


def preserve_raw_json(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("raw_json") is None:
        item = {**item, "raw_json": item.copy()}
    return item


def parse_text_content(source_name: str, text: str) -> list[dict[str, Any]]:
    stripped_text = text.strip()
    if not stripped_text:
        return []

    json_data = parse_json_text(stripped_text)
    if isinstance(json_data, list):
        return [preserve_raw_json(item) for item in json_data]
    if isinstance(json_data, dict):
        return [preserve_raw_json(json_data)]

    law_csv_data = parse_law_csv_text(source_name, stripped_text)
    if law_csv_data is not None:
        return law_csv_data

    return [parse_plain_text(source_name, stripped_text)]


def load_json_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))

    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return [preserve_raw_json(item) for item in data]
    if isinstance(data, dict):
        return [preserve_raw_json(data)]
    raise ValueError(f"Unsupported JSON format: {path}")


def load_text_file(path: Path) -> list[dict[str, Any]]:
    return parse_text_content(path.name, path.read_text(encoding="utf-8-sig"))
