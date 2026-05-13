from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import is_placeholder_database_url, settings


if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and update it.")
if is_placeholder_database_url(settings.DATABASE_URL):
    raise RuntimeError(
        "DATABASE_URL still contains placeholder values. "
        "Update .env with your real Supabase/PostgreSQL connection string."
    )


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
