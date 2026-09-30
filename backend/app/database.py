"""SQLAlchemy engine, session factory and startup initialisation."""
import logging
import os
import time
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger("resume_analyzer.db")

_url = get_settings().database_url.replace("postgres://", "postgresql://", 1)
_connect_args: dict = {}

if _url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    _path = _url.replace("sqlite:///", "", 1)
    if _path and _path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(_path)), exist_ok=True)

engine = create_engine(_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 15, delay: float = 3.0) -> None:
    """Create tables, waiting for the database to accept connections."""
    from app import models  # noqa: F401  (registers the tables)

    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == retries:
                raise
            logger.warning("Database not ready (attempt %s/%s), retrying...", attempt, retries)
            time.sleep(delay)
