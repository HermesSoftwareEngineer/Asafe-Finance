from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

_url = settings.resolved_database_url
_is_sqlite = _url.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        _url,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL / Supabase
    # NullPool é essencial em ambientes serverless (Cloud Run):
    # evita esgotar as conexões do Supabase entre cold starts.
    # O pooling fica por conta do PgBouncer do próprio Supabase.
    engine = create_engine(
        _url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
