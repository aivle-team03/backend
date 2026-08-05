import logging
import os
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import api_router
from app.core.exceptions import (
    setup_exception_handlers,
    setup_logging,
)
from app.crud.inspection import (
    generate_scheduled_inspection_histories,
)
from app.db.db import (
    Base,
    SessionLocal,
    engine,
)

import app.models


logger = logging.getLogger("app.scheduler")


# 경로 설정

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

AI_DIR = PROJECT_DIR / "AI"
AI_VIDEO_DIR = AI_DIR / "videos"
AI_OUTPUT_DIR = AI_DIR / "outputs"

STATIC_DIR = BACKEND_DIR / "static"
STATIC_UPLOAD_DIR = STATIC_DIR / "uploads"


# 필요한 폴더가 없으면 자동 생성
STATIC_UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AI_VIDEO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AI_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# 파일 로깅 활성화
setup_logging()


# DB 테이블 생성
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="FastAPI Backend",
    description="시설 안전관리 AI 자동화 시스템",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 예외 핸들러 적용
setup_exception_handlers(app)


# ---------------------------------------------------------
# 정적 파일 마운트
# ---------------------------------------------------------

# 기존 static 파일
app.mount(
    "/static",
    StaticFiles(
        directory=str(STATIC_DIR),
    ),
    name="static",
)


# AI 원본 영상
# AI/videos/test2.mp4
# → http://127.0.0.1:8000/ai-videos/test2.mp4
app.mount(
    "/ai-videos",
    StaticFiles(
        directory=str(AI_VIDEO_DIR),
    ),
    name="ai-videos",
)


# AI 분석 결과 영상
# AI/outputs/result.mp4
# → http://127.0.0.1:8000/ai-results/result.mp4
app.mount(
    "/ai-results",
    StaticFiles(
        directory=str(AI_OUTPUT_DIR),
    ),
    name="ai-results",
)


# API 라우터 등록
app.include_router(
    api_router,
    prefix="/api",
)


@app.get("/")
def read_root():
    return {
        "message": "MySQL 연결 성공!",
        "ai_video_directory": str(
            AI_VIDEO_DIR
        ),
        "ai_output_directory": str(
            AI_OUTPUT_DIR
        ),
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "ai_directory_exists": (
            AI_DIR.exists()
        ),
        "video_directory_exists": (
            AI_VIDEO_DIR.exists()
        ),
        "output_directory_exists": (
            AI_OUTPUT_DIR.exists()
        ),
    }


def run_daily_inspection_job():
    """매일 자정에 실행되는 스케줄러 작업"""

    db = SessionLocal()

    try:
        generate_scheduled_inspection_histories(
            db
        )

        logger.info(
            "매일 정기 점검 이력 자동 생성 완료"
        )

    except Exception as error:
        logger.error(
            (
                "스케줄러 작업 실행 중 "
                f"오류 발생: {error}"
            ),
            exc_info=True,
        )

    finally:
        db.close()


scheduler = BackgroundScheduler()

scheduler.add_job(
    run_daily_inspection_job,
    trigger="cron",
    hour=0,
    minute=0,
    id="daily_inspection_job",
    replace_existing=True,
)

scheduler.start()