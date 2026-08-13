from datetime import date
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os

import httpx

from app.crud.auth import get_current_admin, get_current_user
from app.crud.education import get_education_attendees
from app.schemas.education import EducationAttendeeListResponse
from app.crud.education import (
    complete_education,
    update_education_progress,
    get_education_by_id,
    get_education_status_summaries,
    get_my_education_list,
    get_user_by_uid,
    get_user_education_for_admin,
    get_user_education_statuses,
    get_user_education_summary_counts, # 유저용 교육 요약 건수
    get_user_completion_rates, # 유저용 교육 이수 현황 백분율 조회
    get_category_completion_stats, # 관리자용 카테고리별 이수 현황 그래프 통계 조회
    get_admin_education_dashboard,
    save_generated_education, # 영상 생성 서비스 결과의 Education 영속화
)
from app.db.db import get_db
from app.models.video_generation_job import VideoGenerationJob
from app.tasks.video_generation import finalize_video_generation
from app.models import User
from app.schemas.education import (
    EducationCompletionFilter,
    EducationCompletionResponse,
    EducationProgressUpdate,
    EducationResponse,
    EducationStatusResponse,
    EducationStatusSummaryResponse,
    UserEducationResponse,
    UserEducationSummaryResponse, # 유저용 교육 요약 건수 응답모델
    UserCompletionRatesResponse, # 유저용 교육 이수 현황 백분율 응답모델
    AdminCategoryCompletionResponse, # 관리자용 교육 이수 현황 그래프 통계 응답모델
    AdminEducationDashboardResponse,
)
from app.schemas.ai_video import VideoGenerateResponse, VideoPublishResponse, VideoStatusResponse

education_router = APIRouter()
admin_education_router = APIRouter()


# ==========================================
# 1. 일반 유저용 API (/api/education)
# ==========================================

@education_router.get(
    "/list",
    response_model=List[EducationResponse],
    summary="[유저] 내 교육 영상 조회",
)
def read_my_education_list(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """자신의 조건에 해당하는 교육 영상 목록을 조회"""
    return get_my_education_list(db, user=current_user, category=category)


@education_router.get(
    "/summary",
    response_model=UserEducationSummaryResponse,
    summary="[유저] 상단 요약 건수 조회 (이번주 마감, 진행중, 이수 완료)",
)
def read_my_education_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """일반 유저 교육 페이지 상단 요약 카드 (이번주 마감 N건, 진행 중 N건, 이수 완료 N건)"""
    return get_user_education_summary_counts(db, user=current_user)


@education_router.get(
    "/status",
    response_model=List[EducationStatusResponse],
    summary="[유저] 내 교육 리스트 조회",
)
def read_my_education_status(
    completion_filter: Optional[EducationCompletionFilter] = Query(
        None,
        alias="status",
    ),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """일반 유저 내 교육 리스트 (교육명, 구분, 마감일, 상태 등)"""
    return get_user_education_statuses(
        db,
        user=current_user,
        category=category,
        completion_status=(
            completion_filter.value if completion_filter else None
        ),
    )


@education_router.get(
    "/completion-rates",
    response_model=UserCompletionRatesResponse,
    summary="[유저] 교육 이수 현황 백분율 조회 (필수, 정기, 전체)",
)
def read_my_completion_rates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """일반 유저 하단 교육 이수 현황 (필수 교육 %, 정기 교육 %, 전체 %)"""
    return get_user_completion_rates(db, user=current_user)


@education_router.post(
    "/{education_id}/complete",
    response_model=EducationCompletionResponse,
    summary="[유저] 비디오 수강 이수 완료 처리",
)
def post_my_education_complete(
    education_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """영상의 80% 이상 시청 후 '이수 완료' 버튼 클릭 시 호출"""
    education = get_education_by_id(db, education_id=education_id, company_id=current_user.company_id)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="교육을 찾을 수 없습니다",
        )
    return complete_education(db, user=current_user, education=education)


@education_router.post(
    "/{education_id}/progress",
    response_model=EducationCompletionResponse,
    summary="[유저] 교육 영상 시청 진척도 및 위치 업데이트",
)
def post_my_education_progress(
    payload: EducationProgressUpdate,
    education_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """시청 중 주기적으로 위치(초) 및 진척도(%) 업데이트 (80% 이상 시 자동으로 이수 처리)"""
    education = get_education_by_id(db, education_id=education_id, company_id=current_user.company_id)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="교육을 찾을 수 없습니다",
        )
    return update_education_progress(
        db,
        user=current_user,
        education=education,
        last_position_seconds=payload.last_position_seconds,
        progress_percent=payload.progress_percent,
    )


# ==========================================
# 2. 관리자용 API (/api/admin/education)
# ==========================================


@admin_education_router.get(
    "/category-stats",
    response_model=AdminCategoryCompletionResponse,
    summary="[관리자] 카테고리별 이수 현황 그래프 통계 조회",
)
def read_category_completion_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """각 사용자의 카테고리별 이수 현황 통계치 조회"""
    return get_category_completion_stats(db, company_id=current_admin.company_id)


@admin_education_router.get("/dashboard", response_model=AdminEducationDashboardResponse)
def read_admin_education_dashboard_compat(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return get_admin_education_dashboard(db, company_id=current_admin.company_id)


@admin_education_router.get(
    "/status",
    response_model=List[EducationStatusSummaryResponse],
    summary="[관리자] 대상자별 교육 리스트 및 이수 요약 조회",
)
def read_education_status_summary(
    education_id: Optional[int] = Query(None, ge=1),
    completion_filter: Optional[EducationCompletionFilter] = Query(
        None,
        alias="status",
    ),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """관리자 페이지 우측 '대상자별 교육 리스트'"""
    if (
        education_id is not None
        and get_education_by_id(
            db,
            education_id=education_id,
            company_id=current_admin.company_id,
        )
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="교육을 찾을 수 없습니다",
        )

    return get_education_status_summaries(
        db,
        company_id=current_admin.company_id,
        education_id=education_id,
        completion_status=(
            completion_filter.value if completion_filter else None
        ),
    )


@admin_education_router.get("/{education_id}/attendees", response_model=EducationAttendeeListResponse)
def read_education_attendees(
    education_id: int = Path(..., ge=1),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    education = get_education_by_id(db, education_id=education_id, company_id=current_admin.company_id)
    if education is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")
    return get_education_attendees(db, company_id=current_admin.company_id, education_id=education_id)


@admin_education_router.get(
    "/{uid}",
    response_model=UserEducationResponse,
    summary="[관리자] 특정 사용자 교육 상태 상세 조회",
)
def read_user_education(
    uid: int = Path(..., ge=1),
    category: Optional[str] = Query(None),
    completion_filter: Optional[EducationCompletionFilter] = Query(
        None,
        alias="status",
    ),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_user_by_uid(db, uid=uid, company_id=current_admin.company_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    return get_user_education_for_admin(
        db,
        user=user,
        category=category,
        completion_status=(
            completion_filter.value if completion_filter else None
        ),
    )


# ==========================================
# 3. Google Veo AI 동영상 전용 API (Track 2)
# ==========================================
# 영상 생성은 별도 서비스(aivle-team03/AI 의 videoagent)가 담당한다.
# 백엔드는 인증과 company_id 판별, 결과의 DB 영속화만 맡는다.

VIDEO_AGENT_URL = os.getenv("VIDEO_AGENT_URL", "http://127.0.0.1:8100").rstrip("/")


@education_router.post("/veo-generate", response_model=VideoGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_generate_veo_video(
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form("공통"),
    type: Optional[str] = Form("필수"),
    due_date: Optional[date] = Form(None),
    request: Optional[str] = Form(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    [Track 2] Google Veo AI 동영상 생성 비동기 요청 API
    - 업로드된 문서(PDF/PPTX/TXT) 또는 텍스트를 영상 생성 서비스로 전달하고 task_id를 반환한다.
    - company_id는 클라이언트 입력이 아니라 인증된 관리자 계정에서 가져온다.
    """
    if not file and not text_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="문서 파일(file) 또는 텍스트 내용(text_content) 중 하나는 필수입니다."
        )

    form = {"company_id": str(current_admin.company_id)}
    for key, value in (
        ("title", title),
        ("category", category),
        ("type", type),
        ("request", request),
        ("text_content", text_content),
    ):
        if value is not None:
            form[key] = value

    files = None
    if file:
        # 파이프라인이 다른 서비스에 있으므로 백엔드는 파일을 디스크에 남기지 않고 그대로 넘긴다.
        files = {"file": (file.filename, await file.read(), file.content_type)}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{VIDEO_AGENT_URL}/video/generate", data=form, files=files)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"영상 생성 서비스에 연결할 수 없습니다: {e}"
        )

    if resp.status_code != status.HTTP_202_ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"영상 생성 서비스가 요청을 거부했습니다 (status={resp.status_code})."
        )

    result = resp.json()
    task_id = result.get("task_id")
    if not task_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="영상 생성 서비스가 task_id를 반환하지 않았습니다.")

    job = VideoGenerationJob(
        task_id=task_id,
        company_id=current_admin.company_id,
        requested_by_uid=current_admin.uid,
        title=title,
        category=category,
        education_type=type,
        due_date=due_date,
        agent_status=result.get("status") or "PENDING",
        publication_status="QUEUED",
    )
    db.add(job)
    db.commit()
    finalize_video_generation.delay(task_id)
    return result


def _video_job_status(job: VideoGenerationJob):
    quality_report = json.loads(job.quality_report_json) if job.quality_report_json else None
    return {
        "task_id": job.task_id,
        "status": job.agent_status,
        "progress_percent": job.progress_percent,
        "video_url": job.video_url,
        "error_message": job.error_message,
        "quality_report": quality_report,
        "education_id": job.education_id,
        "publication_status": job.publication_status,
        "title": job.title,
        "category": job.category,
        "type": job.education_type,
        "due_date": job.due_date,
    }


@education_router.get("/veo-generate/pending", response_model=List[VideoStatusResponse])
async def read_pending_veo_video_jobs(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return this company's unfinished and human-review video jobs for page re-entry."""
    jobs = (
        db.query(VideoGenerationJob)
        .filter(
            VideoGenerationJob.company_id == current_admin.company_id,
            VideoGenerationJob.publication_status.in_(("QUEUED", "REVIEW_REQUIRED")),
        )
        .order_by(VideoGenerationJob.updated_at.desc())
        .all()
    )
    return [_video_job_status(job) for job in jobs]


@education_router.get("/veo-generate/{task_id}/status", response_model=VideoStatusResponse)
async def read_veo_video_status(
    task_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Google Veo 동영상 제작 작업 처리 상태 조회 API
    - Celery 워커가 DB에 기록한 작업 상태를 조회한다.
    """
    job = db.get(VideoGenerationJob, task_id)
    if not job or job.company_id != current_admin.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 Veo 작업(task_id)을 찾을 수 없습니다.")

    if job.publication_status in {"PUBLISHED", "REVIEW_REQUIRED", "FAILED", "TIMED_OUT"}:
        return _video_job_status(job)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{VIDEO_AGENT_URL}/video/generate/{task_id}/status")
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"영상 생성 서비스에 연결할 수 없습니다: {e}"
        )

    if resp.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 Veo 작업(task_id)을 찾을 수 없습니다."
        )
    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"영상 생성 서비스 조회에 실패했습니다 (status={resp.status_code})."
        )

    status_info = resp.json()

    # 다른 회사의 task_id로 조회하는 것을 막는다. 존재 여부까지 숨기기 위해 403이 아니라 404를 쓴다.
    owner_company_id = status_info.get("company_id")
    if owner_company_id is not None and int(owner_company_id) != current_admin.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 Veo 작업(task_id)을 찾을 수 없습니다."
        )

    status_info["publication_status"] = job.publication_status
    return status_info


@education_router.post(
    "/veo-generate/{task_id}/publish",
    response_model=VideoPublishResponse,
    status_code=status.HTTP_201_CREATED,
)
async def publish_generated_veo_video(
    task_id: str,
    due_date: date = Form(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """검토가 완료된 VideoAgent 결과만 교육 목록에 최종 등록한다."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{VIDEO_AGENT_URL}/video/generate/{task_id}/status")
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"영상 생성 서비스에 연결할 수 없습니다: {e}",
        )

    if resp.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 Veo 작업을 찾을 수 없습니다.")
    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="영상 생성 결과를 조회하지 못했습니다.")

    status_info = resp.json()
    owner_company_id = status_info.get("company_id")
    if owner_company_id is not None and int(owner_company_id) != current_admin.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 Veo 작업을 찾을 수 없습니다.")
    if status_info.get("status") != "COMPLETED" or not status_info.get("video_url"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="완료된 영상만 교육 목록에 등록할 수 있습니다.")

    education = save_generated_education(
        db,
        company_id=current_admin.company_id,
        video_url=status_info["video_url"],
        title=title or status_info.get("title"),
        category=category or status_info.get("category"),
        type=type or status_info.get("type"),
        due_date=due_date,
    )
    job = db.get(VideoGenerationJob, task_id)
    if job and job.company_id == current_admin.company_id:
        job.education_id = education.education_id
        job.publication_status = "PUBLISHED"
        db.commit()
    return {"education_id": education.education_id, "message": "교육 영상이 목록에 등록되었습니다."}
