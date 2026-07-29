import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    if os.getenv("ENV") == "production":
        raise ValueError("CRITICAL: Production environment requires DATABASE_URL to be explicitly defined in .env!")
    else:
        DATABASE_URL = "sqlite:///./app.db"
        print("[DB] NOTICE: DATABASE_URL not set in .env, falling back to local SQLite: sqlite:///./app.db")

# app/db/db.py
engine = create_engine(
    DATABASE_URL,
    pool_size=5,        
    max_overflow=2,     
    pool_recycle=1800,
    connect_args={"ssl": {"ca": "ca.pem"}}, # ca.pem SSL 인증서 지정
    echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()