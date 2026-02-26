import os
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

DATABASE_URL = os.environ["DATABASE_URL"]
DB_SCHEMA = os.getenv("DB_SCHEMA", "product")

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,   # Lambda-friendly
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _quote_ident(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


@event.listens_for(engine, "connect")
def _set_search_path(dbapi_conn, _):
    schema = _quote_ident(DB_SCHEMA)
    cur = dbapi_conn.cursor()
    cur.execute(f"SET search_path TO {schema}")
    cur.close()


def init_schema():
    """
    Optional helper. Prefer migrations/deploy-time for Lambda.
    """
    schema = _quote_ident(DB_SCHEMA)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.execute(text(f"SET search_path TO {schema}"))