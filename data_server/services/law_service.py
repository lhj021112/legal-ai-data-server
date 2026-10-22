from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.case_model import Case
from schemas.law_schema import LawArticle, LawSearchResponse


_QUERY_SUFFIXES = tuple(sorted((
    "으로부터", "에게서", "으로는", "에서는", "으로", "에게", "에서", "부터",
    "까지", "처럼", "보다", "마다", "에게는", "에는", "으로서", "으로써",
    "상", "의", "은", "는", "이", "가", "을", "를", "에", "와", "과",
), key=len, reverse=True))
_QUERY_STOPWORDS = {"기본", "기준", "내용", "관련", "알려줘", "알려주세요", "무엇", "경우"}


def _query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for raw_term in query.casefold().split():
        term = raw_term.strip(".,!?()[]{}\"'“”‘’·:;")
        for suffix in _QUERY_SUFFIXES:
            if term.endswith(suffix) and len(term) - len(suffix) >= 2:
                term = term[:-len(suffix)]
                break
        if len(term) >= 2 and term not in _QUERY_STOPWORDS and term not in terms:
            terms.append(term)
    return terms


@lru_cache(maxsize=1)
def bundled_laws() -> dict[str, dict]:
    path = Path(__file__).resolve().parents[1] / "data" / "verified_laws.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {row["case_id"]: row for row in payload.get("rows", [])}


class LawService:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self, q: str, limit: int, as_of: date, offset: int = 0,
        include_total: bool = False, snapshot_mode: bool = False,
    ) -> LawSearchResponse:
        # The legacy law rows are search snapshots, not verified article versions.
        rows = self.db.scalars(select(Case).where(Case.category == "법령")).all()
        items: list[LawArticle] = []
        matching_unverified = False
        coverage_missing = False
        seen_ids: set[str] = set()
        terms = q.casefold().split()
        snapshot = bundled_laws()
        matched: list[tuple[int, dict | None]] = []

        for row in rows:
            raw = row.raw_json if isinstance(row.raw_json, dict) else {}
            verified = raw.get("verified_law")
            bundle_row = snapshot.get(row.case_id)
            if (
                verified is None
                and bundle_row
                and isinstance(raw.get("law"), dict)
                and isinstance(raw.get("article"), dict)
                and str(raw["law"].get("법령일련번호")) == bundle_row.get("source_mst")
                and str(raw["article"].get("조문키")) == bundle_row.get("source_article_key")
            ):
                verified = bundle_row.get("verified_law")
            searchable_fields = [row.title, row.search_text, row.sub_category]
            if isinstance(verified, dict):
                searchable_fields.extend(verified.get(key) for key in ("law_name", "article_number", "text"))
            searchable = " ".join(str(part or "") for part in searchable_fields).casefold()
            compact_query = "".join(q.casefold().split())
            compact_searchable = "".join(searchable.split())
            exact_phrase = compact_query in compact_searchable
            matched_terms = sum(
                term in searchable or (len(term) >= 4 and term in compact_searchable)
                for term in terms
            )
            minimum_matches = 1 if len(terms) <= 2 else 2
            if not exact_phrase and matched_terms < minimum_matches:
                continue
            law_name = str(verified.get("law_name") or "").casefold() if isinstance(verified, dict) else ""
            article_number = str(verified.get("article_number") or "").casefold() if isinstance(verified, dict) else ""
            title = str(row.title or "").casefold()
            score = (
                (100 if law_name and "".join(law_name.split()) in compact_query else 0)
                + (60 if any(term in article_number for term in terms) else 0)
                + (30 if compact_query and compact_query in "".join(title.split()) else 0)
                + matched_terms * 10
                + (5 if exact_phrase else 0)
            )
            matched.append((score, verified))

        matched.sort(key=lambda match: match[0], reverse=True)

        if snapshot_mode:
            dates: list[date] = []
            for _, verified in matched:
                if not isinstance(verified, dict):
                    continue
                try:
                    article = LawArticle.model_validate(
                        {key: value for key, value in verified.items() if key not in ("covered_from", "covered_to")}
                    )
                    covered_from = date.fromisoformat(verified["covered_from"])
                    covered_to = date.fromisoformat(verified["covered_to"])
                except (ValidationError, KeyError, TypeError, ValueError):
                    continue
                if (
                    covered_from <= covered_to <= article.retrieved_at <= date.today()
                    and article.effective_from <= covered_to
                    and (article.effective_to is None or covered_to < article.effective_to)
                ):
                    dates.append(covered_to)
            if dates:
                as_of = max(dates)

        for _, verified in matched:
            if not isinstance(verified, dict):
                matching_unverified = True
                continue
            try:
                article = LawArticle.model_validate(
                    {key: value for key, value in verified.items() if key not in ("covered_from", "covered_to")}
                )
                covered_from = date.fromisoformat(verified["covered_from"])
                covered_to = date.fromisoformat(verified["covered_to"])
            except (ValidationError, ValueError, KeyError, TypeError):
                matching_unverified = True
                continue

            # Coverage is explicit: a missing end date never implies historical support.
            if not (covered_from <= as_of <= covered_to):
                coverage_missing = True
                continue
            if not (article.effective_from <= as_of):
                coverage_missing = True
                continue
            if article.effective_to is not None and as_of >= article.effective_to:
                coverage_missing = True
                continue
            if (
                article.retrieved_at > date.today()
                or covered_from > covered_to
                or covered_to > article.retrieved_at
                or article.effective_from > covered_to
            ):
                matching_unverified = True
                continue
            if article.article_id in seen_ids:
                matching_unverified = True
                continue
            seen_ids.add(article.article_id)
            items.append(article)

        warnings: list[str] = []
        if matching_unverified:
            warnings.append("공식 원문 확인일 또는 조문 버전 검증이 없는 저장 자료는 제외했습니다.")
        if coverage_missing:
            warnings.append("요청한 기준일을 지원하는 검증된 조문 버전이 없습니다.")
        if snapshot_mode and items and as_of < date.today():
            latest_retrieval = max(item.retrieved_at for item in items).isoformat()
            warnings.append(
                f"저장 자료의 기준일은 {as_of.isoformat()}이며 공식 확인일은 최대 {latest_retrieval}입니다. "
                "그 이후 개정 여부와 현재 법령과 일치하는지는 확인되지 않았습니다."
            )
        if not items and not warnings:
            warnings.append("검색어와 일치하는 검증된 법령 조문이 없습니다.")
        warnings.append("부칙·별표·경과 규정의 수록 범위는 별도로 확인해야 합니다.")
        return LawSearchResponse(
            items=items[offset:offset + limit],
            as_of=as_of,
            warnings=warnings,
            total=len(items) if include_total else None,
        )
