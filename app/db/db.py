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

# RDS 는 EC2 와 같은 VPC 안에서 통신하므로 별도 CA 인증서를 붙이지 않는다.
# (Aiven 은 공용 인터넷을 거쳐서 ca.pem 이 필요했다.)
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=2,
    pool_recycle=1800,
    # 모든 SQL 이 로그로 남아 디스크를 채우고 파라미터 값까지 노출되므로 기본은 끈다.
    # 로컬에서 쿼리를 보려면 .env 에 SQL_ECHO=true 를 넣는다.
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()