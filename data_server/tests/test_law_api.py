from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

import api.law_api as law_api
import services.law_service as law_service
from main import app
from services.law_service import LawService


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, statement):
        return self

    def all(self):
        return self.rows


def row(verified_law=None):
    return SimpleNamespace(
        case_id="law-001706-750",
        title="민법 제750조 불법행위의 내용",
        search_text="민법 제750조 손해배상",
        sub_category="민법",
        raw_json={"verified_law": verified_law} if verified_law else {},
    )


def verified_law():
    return {
        "article_id": "law-001-750-v1",
        "law_id": "001",
        "law_name": "민법",
        "article_number": "제750조",
        "text": "제750조(불법행위의 내용) 시험용 전문",
        "effective_from": "2020-01-01",
        "effective_to": None,
        "source_url": "https://www.law.go.kr/법령/민법/제750조",
        "retrieved_at": "2026-10-15",
        "covered_from": "2026-10-15",
        "covered_to": "2026-10-15",
    }


@pytest.fixture()
def client():
    app.dependency_overrides[law_api.get_db] = lambda: FakeSession([])
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_route_is_registered_and_empty_data_has_warning(client):
    response = client.get("/laws/search?q=민법&as_of=2026-10-15")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["as_of"] == "2026-10-15"
    assert response.json()["warnings"]
    assert "total" not in response.json()


def test_web_total_is_opt_in_and_legacy_response_stays_unchanged(client):
    app.dependency_overrides[law_api.get_db] = lambda: FakeSession([row(verified_law())])
    legacy = client.get("/laws/search?q=민법&as_of=2026-10-15")
    paged = client.get("/laws/search?q=민법&as_of=2026-10-15&include_total=true&offset=1")
    assert legacy.status_code == paged.status_code == 200
    assert set(legacy.json()) == {"items", "as_of", "warnings"}
    assert paged.json()["total"] == 1
    assert paged.json()["items"] == []


def test_stored_snapshot_uses_its_verified_date_without_live_api(client, monkeypatch):
    app.dependency_overrides[law_api.get_db] = lambda: FakeSession([row(verified_law())])
    monkeypatch.setenv("LAW_API_OC", "not-a-valid-oc")
    response = client.get("/laws/search?q=민법&snapshot=true&include_total=true")
    assert response.status_code == 200
    assert response.json()["as_of"] == "2026-10-15"
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert any("현재 법령과 일치" in warning for warning in response.json()["warnings"])
    assert client.get("/laws/search?q=민법&snapshot=true&as_of=2026-10-15").status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=21", "as_of=not-a-date", "q=%20%20"])
def test_invalid_query_returns_422(client, query):
    assert client.get(f"/laws/search?q=민법&{query}").status_code == 422


def test_unverified_legacy_row_is_not_presented_as_official_law():
    result = LawService(FakeSession([row()])).search("민법", 5, date(2026, 10, 15))
    assert result.items == []
    assert any("제외" in warning for warning in result.warnings)


def test_verified_row_is_returned_only_for_explicit_coverage():
    service = LawService(FakeSession([row(verified_law())]))
    current = service.search("민법 제750조", 5, date(2026, 10, 15))
    past = service.search("민법 제750조", 5, date(2020, 1, 1))
    assert [item.article_id for item in current.items] == ["law-001-750-v1"]
    assert past.items == []
    assert any("기준일" in warning for warning in past.warnings)


def test_law_search_reports_total_and_pages_without_repeating_rows():
    rows = []
    for index in range(3):
        article = verified_law()
        article["article_id"] = f"law-001-750-v{index}"
        item = row(article)
        item.case_id = f"stored-law-{index}"
        rows.append(item)
    service = LawService(FakeSession(rows))
    first = service.search("민법", 2, date(2026, 10, 15), offset=0, include_total=True)
    second = service.search("민법", 2, date(2026, 10, 15), offset=2, include_total=True)
    assert first.total == second.total == 3
    assert len(first.items) == 2
    assert len(second.items) == 1
    assert {item.article_id for item in first.items}.isdisjoint(item.article_id for item in second.items)


def test_missing_provenance_or_incomplete_article_is_excluded():
    incomplete = verified_law()
    incomplete["retrieved_at"] = None
    incomplete["text"] = ""
    result = LawService(FakeSession([row(incomplete)])).search("민법", 5, date(2026, 10, 15))
    assert result.items == []


def test_effective_to_is_exclusive():
    article = verified_law()
    article["effective_to"] = "2026-10-15"
    result = LawService(FakeSession([row(article)])).search("민법", 5, date(2026, 10, 15))
    assert result.items == []


def test_coverage_cannot_extend_beyond_official_retrieval():
    article = verified_law()
    article["covered_to"] = "2026-10-16"
    result = LawService(FakeSession([row(article)])).search("민법", 5, date(2026, 10, 15))
    assert result.items == []


def test_bundle_is_used_only_for_matching_database_version(monkeypatch):
    bundle = {
        "law-001706-750": {
            "source_mst": "284415",
            "source_article_key": "0750001",
            "verified_law": verified_law(),
        }
    }
    monkeypatch.setattr(law_service, "bundled_laws", lambda: bundle)
    case = row()
    case.raw_json = {"law": {"법령일련번호": "284415"}, "article": {"조문키": "0750001"}}
    service = LawService(FakeSession([case]))
    assert len(service.search("민법", 5, date(2026, 10, 15)).items) == 1
    case.raw_json["law"]["법령일련번호"] = "older-version"
    assert service.search("민법", 5, date(2026, 10, 15)).items == []


def test_current_query_does_not_mislabel_an_older_snapshot(monkeypatch):
    monkeypatch.setenv("LAW_API_OC", "not-a-valid-oc")
    result = LawService(FakeSession([row(verified_law())])).search("민법", 5, date.today())
    assert result.items == []
    assert any("기준일" in warning for warning in result.warnings)


def test_invalid_newer_snapshot_does_not_hide_valid_older_snapshot():
    invalid = verified_law()
    invalid["article_id"] = "law-001-750-invalid"
    invalid["covered_to"] = date.today().isoformat()
    older = row(verified_law())
    newer = row(invalid)
    newer.case_id = "invalid-stored-law"
    result = LawService(FakeSession([older, newer])).search(
        "민법", 5, date.today(), snapshot_mode=True
    )
    assert result.as_of == date(2026, 10, 15)
    assert len(result.items) == 1


def test_natural_language_terms_use_relevance_instead_of_strict_and_matching():
    relevant = verified_law()
    relevant.update(
        article_id="labor-60",
        law_id="labor",
        law_name="근로기준법",
        article_number="제60조",
        text="연차 유급 휴가의 기본 발생 기준을 정한다.",
        source_url="https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=1",
    )
    cross_reference = verified_law()
    cross_reference.update(
        article_id="other-law-1",
        law_id="other",
        law_name="다른 법률",
        article_number="제1조",
        text="근로기준법상 연차유급휴가의 기본 발생 기준을 참고한다.",
        source_url="https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=2",
    )
    relevant_row = row(relevant)
    relevant_row.title = "근로기준법 제60조 연차 유급 휴가"
    reference_row = row(cross_reference)
    reference_row.case_id = "law-reference"
    reference_row.title = "다른 법률 제1조"

    result = LawService(FakeSession([reference_row, relevant_row])).search(
        "근로기준법상 연차유급휴가의 기본 발생 기준", 5, date(2026, 10, 15)
    )

    assert [item.article_id for item in result.items] == ["labor-60", "other-law-1"]
