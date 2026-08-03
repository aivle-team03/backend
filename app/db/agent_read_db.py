import os
from typing import Generator

from dotenv import load_dotenv
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.db import DATABASE_URL

load_dotenv()

AGENT_READ_DATABASE_URL = os.getenv("AGENT_READ_DATABASE_URL")
if (
    os.getenv("ENV") == "production"
    and AGENT_READ_DATABASE_URL == DATABASE_URL
):
    raise ValueError(
        "AGENT_READ_DATABASE_URL must use a separate read-only account in production."
    )


def _engine_options(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}

    options = {
        "pool_size": 3,
        "max_overflow": 1,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }
    ssl_ca = os.getenv("AGENT_READ_DB_SSL_CA")
    if ssl_ca:
        options["connect_args"] = {"ssl": {"ca": ssl_ca}}
    return options


agent_read_engine = None
AgentReadSessionLocal = None
if AGENT_READ_DATABASE_URL:
    agent_read_engine = create_engine(
        AGENT_READ_DATABASE_URL,
        **_engine_options(AGENT_READ_DATABASE_URL),
    )
    AgentReadSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=agent_read_engine,
    )


def get_agent_read_db() -> Generator[Session, None, None]:
    if AgentReadSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent read-only database is not configured.",
        )
    db = AgentReadSessionLocal()
    try:
        yield db
    finally:
        db.close()
