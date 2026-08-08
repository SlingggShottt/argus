"""Database engine and session factory. Every other module gets a DB session
through get_db() or init_db() defined here — nobody else calls create_engine()."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, guarantees it's closed after the
    request even if the handler raises."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates every table from models.py if it doesn't already exist. No
    migration tool (e.g. Alembic) for this project — the schema is fixed for
    a one-week build with a single batch pipeline, so create_all() is enough.
    A production system with an evolving schema would want real migrations."""
    Base.metadata.create_all(bind=engine)
