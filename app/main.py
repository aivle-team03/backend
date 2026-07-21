from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from app.db.db import SessionLocal, get_db, engine, Base
import app.models
from app.api.routers import api_router
from app.core.exceptions import setup_logging, setup_exception_handlers

# 파일 로깅 활성화
setup_logging()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI Backend",
    description="시설 안전관리 AI 자동화 시스템",
    version="1.0.0"
)

# CORS 미들웨어 추가 설정 (프론트엔드 연동 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 예외 핸들러 적용
setup_exception_handlers(app)

# static 디렉토리 생성 및 정적 파일 마운트
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "MySQL 연결 성공!"}