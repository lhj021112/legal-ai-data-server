from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

import api.case_api as case_api
from main import app


def make_case(case_id: str, row_id: int) -> dict:
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    return {
        "case_id": case_id,
        "title": f"Case {row_id}",
        "court": "대법원",
        "case_number": f"2026다{row_id}",
        "decision_date": "2026-06-01",
        "category": "민사",
        "sub_category": "명의신탁",
        "issue": "issue",
        "summary": "summary",
        "facts": "facts",
        "judgment": "judgment",
        "reasoning": "reasoning",
        "search_text": f"명의신탁 case {row_id}",
        "raw_json": {"source": "test"},
        "id": row_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture()
def client(monkeypatch):
    app.dependency_overrides[case_api.get_db] = lambda: object()
    yield TestClient(app)
    app.dependency_overrides.clear()


def patch_service(monkeypatch, cases: list[dict]):
    class FakeCaseService:
        def __init__(self, db):
            self.db = db

        def list_cases(self, limit: int, offset: int, updated_after=None):
            return len(cases), cases[offset : offset + limit]

        def search_cases(self, query: str):
            return cases

        def get_case(self, case_id: str):
            return next(case for case in cases if case["case_id"] == case_id)

    monkeypatch.setattr(case_api, "CaseService", FakeCaseService)


def test_get_cases_returns_total_and_items(client, monkeypatch):
    patch_service(monkeypatch, [make_case("case-1", 1)])

    response = client.get("/cases")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["case_id"] == "case-1"


def test_get_cases_applies_limit_and_offset(client, monkeypatch):
    cases = [make_case(f"case-{index}", index) for index in range(1, 6)]
    patch_service(monkeypatch, cases)

    response = client.get("/cases?limit=2&offset=2")

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 5
    assert [item["case_id"] for item in body["items"]] == ["case-3", "case-4"]


def test_get_cases_rejects_limit_above_maximum(client, monkeypatch):
    patch_service(monkeypatch, [])

    response = client.get("/cases?limit=501")

    assert response.status_code == 422


def test_get_cases_pages_do_not_overlap(client, monkeypatch):
    cases = [make_case(f"case-{index}", index) for index in range(1, 5)]
    patch_service(monkeypatch, cases)

    first_page = client.get("/cases?limit=2&offset=0").json()["items"]
    second_page = client.get("/cases?limit=2&offset=2").json()["items"]

    first_ids = {item["case_id"] for item in first_page}
    second_ids = {item["case_id"] for item in second_page}
    assert first_ids.isdisjoint(second_ids)


def test_get_cases_returns_empty_structure_for_empty_database(client, monkeypatch):
    patch_service(monkeypatch, [])

    response = client.get("/cases")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}


def test_search_cases_keeps_total_items_structure(client, monkeypatch):
    patch_service(monkeypatch, [make_case("case-1", 1)])

    response = client.get("/cases/search?q=명의신탁")

    assert response.status_code == 200
    assert set(response.json().keys()) == {"total", "items"}
    assert response.json()["total"] == 1


def test_get_case_keeps_existing_response_shape(client, monkeypatch):
    patch_service(monkeypatch, [make_case("case-1", 1)])

    response = client.get("/cases/case-1")

    assert response.status_code == 200
    assert response.json()["case_id"] == "case-1"
    assert "items" not in response.json()


def test_post_cases_still_requires_admin_api_key(client, monkeypatch):
    patch_service(monkeypatch, [])

    response = client.post("/cases", json=make_case("case-1", 1))

    assert response.status_code == 401
