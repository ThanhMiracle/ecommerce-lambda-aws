import os
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")
DB_SCHEMA = os.getenv("DB_SCHEMA", "auth")

# Lambda-friendly default: avoid pooled connections piling up under scaling
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _quote_ident(ident: str) -> str:
    # Safe-ish quoting for Postgres identifiers (schema/table)
    return '"' + ident.replace('"', '""') + '"'


@event.listens_for(engine, "connect")
def _set_search_path(dbapi_conn, _):
    # Ensures every new connection uses the schema
    schema = _quote_ident(DB_SCHEMA)
    cur = dbapi_conn.cursor()
    cur.execute(f"SET search_path TO {schema}")
    cur.close()


def init_schema():
    """
    Optional helper. Prefer running schema/migrations at deploy-time,
    not on Lambda cold starts.
    """
    schema = _quote_ident(DB_SCHEMA)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.execute(text(f"SET search_path TO {schema}"))