import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = os.getenv("DB_SCHEMA", "payment")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# Engine
engine = create_engine(DATABASE_URL, future=True)

# Session
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Base model
Base = declarative_base()


def init_schema():
    """
    Create schema if it doesn't exist.
    Each microservice owns its own schema.
    """
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))