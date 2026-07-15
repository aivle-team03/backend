import app.models as models
from app.db.db import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.routers import api_router

app = FastAPI(
    title="FastAPI Backend",
    description="시설 안전관리 AI 자동화 시스템",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실제 배포 시에는 ["http://localhost:3000"] 처럼 프론트 주소만 적는 게 안전합니다.
    allow_credentials=True,
    allow_methods=["*"], # GET, POST, PUT, DELETE 모두 허용
    allow_headers=["*"], # 모든 헤더 허용
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"Hello": "World"}