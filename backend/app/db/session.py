import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from pathlib import Path
from urllib.parse import urlparse

_db_url = settings.DATABASE_URL

if _db_url.startswith("sqlite:///"):
    _db_path = _db_url.replace("sqlite:///", "")
elif _db_url.startswith("sqlite:////"):
    _db_path = _db_url.replace("sqlite:////", "/")
else:
    _db_path = _db_url.replace("sqlite://", "")

if _db_path.startswith("/") or (len(_db_path) > 1 and _db_path[1] == ":"):
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Generator function to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
