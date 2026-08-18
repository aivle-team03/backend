import json
import logging
import os

import httpx
from celery.exceptions import Retry

from app.celery_app import celery_app
from app.crud.education import save_generated_education
from app.db.db import SessionLocal
from app.models.video_generation_job import VideoGenerationJob
from app.crud.notification import create_notification


logger = logging.getLogger(__name__)
VIDEO_AGENT_URL = os.getenv("VIDEO_AGENT_URL", "http://127.0.0.1:8100").rstrip("/")
POLL_SECONDS = int(os.getenv("VIDEO_GENERATION_POLL_SECONDS", "5"))
MAX_POLLS = int(os.getenv("VIDEO_GENERATION_MAX_POLLS", "360"))


def _save_agent_state(job, status_info):
    job.agent_status = status_info.get("status") or job.agent_status
    job.progress_percent = int(status_info.get("progress_percent") or 0)
    job.video_url = status_info.get("video_url") or job.video_url
    job.error_message = status_info.get("error_message") or None
    if status_info.get("quality_report") is not None:
        job.quality_report_json = json.dumps(status_info["quality_report"], ensure_ascii=False)


@celery_app.task(bind=True)
def finalize_video_generation(self, task_id: str):
    """Persist one agent-status check and reschedule until it reaches a terminal state."""
    db = SessionLocal()
    try:
        job = db.get(VideoGenerationJob, task_id)
        if not job or job.publication_status in {"PUBLISHED", "REVIEW_REQUIRED", "FAILED", "TIMED_OUT"}:
            return

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(f"{VIDEO_AGENT_URL}/video/generate/{task_id}/status")
            if response.status_code != 404:
                response.raise_for_status()
        except httpx.HTTPError as error:
            job.error_message = f"VideoAgent status request failed: {error}"
            if self.request.retries >= MAX_POLLS:
                job.publication_status = "TIMED_OUT"
                db.commit()
                return
            db.commit()
            raise self.retry(exc=error, countdown=POLL_SECONDS, max_retries=MAX_POLLS)

        if response.status_code == 404:
            job.agent_status = "FAILED"
            job.publication_status = "FAILED"
            job.error_message = "VideoAgent task was not found."
            db.commit()
            return
        status_info = response.json()
        _save_agent_state(job, status_info)

        if job.agent_status == "FAILED":
            job.publication_status = "FAILED"
            db.commit()
            return

        if job.agent_status == "COMPLETED" and job.video_url:
            quality_report = status_info.get("quality_report") or {}
            if quality_report.get("hitl_required") is True:
                job.publication_status = "REVIEW_REQUIRED"
                db.commit()
                return

            education = save_generated_education(
                db,
                company_id=job.company_id,
                video_url=job.video_url,
                title=job.title or status_info.get("title"),
                category=job.category or status_info.get("category"),
                type=job.education_type or status_info.get("type"),
                due_date=job.due_date,
                video_url_en=status_info.get("video_url_en"),
            )
            job.education_id = education.education_id
            job.publication_status = "PUBLISHED"
            db.commit()

            video_title = job.title or status_info.get("title") or "안전 교육"
            create_notification(
                db=db,
                company_id=job.company_id,
                category="complete",
                title="교육 영상 생성 완료",
                message=f"요청하신 '{video_title}' 교육 영상 생성이 완료되었습니다.",
                path="/education-management",
                user_id=job.requested_by_uid
            )
            return

        if self.request.retries >= MAX_POLLS:
            job.publication_status = "TIMED_OUT"
            job.error_message = "Video generation timed out before completion."
            db.commit()
            return

        db.commit()
        raise self.retry(countdown=POLL_SECONDS, max_retries=MAX_POLLS)
    except Retry:
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to finalize VideoAgent task %s", task_id)
        raise
    finally:
        db.close()
