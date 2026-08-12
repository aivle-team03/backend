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
connect_args = {}
# MySQL일 경우에만 SSL 인증서 적용
if DATABASE_URL and DATABASE_URL.startswith("mysql"):
    # 프로젝트 최상단(root)의 ca.pem을 가리키도록 수정
    ca_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ca.pem"))
    if os.path.exists(ca_path):
        connect_args["ssl"] = {"ca": ca_path}
    else:
        print(f"[DB] WARNING: CA 인증서 파일을 찾을 수 없습니다: {ca_path}")

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=2,
    pool_recycle=1800,
    connect_args=connect_args,
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