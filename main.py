from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User
from user import get_users

app = FastAPI(
    title="FastAPI Backend",
    description="FastAPI 기본 프로젝트 구조",
    version="1.0.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "MySQL 연결 성공!"}

@app.get("/users")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()