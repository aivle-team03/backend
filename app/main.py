from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.db.db import SessionLocal, get_db
from app.models.models import User
from app.api.routers import api_router

app = FastAPI(
    title="FastAPI Backend",
    description="FastAPI 기본 프로젝트 구조",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "MySQL 연결 성공!"}

@app.get("/users")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()