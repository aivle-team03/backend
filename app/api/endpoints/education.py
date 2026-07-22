from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.crud.auth import get_current_admin, get_current_user
from app.crud.education import (
    complete_education,
    get_education_by_id,
    get_education_status_summaries,
    get_my_education_list,
    get_user_by_uid,
    get_user_education_for_admin,
    get_user_education_statuses,
    get_user_education_summary_counts, # 유저용 교육 요약 건수
    get_user_completion_rates, # 유저용 교육 이수 현황 백분율 조회
    get_admin_role_completion_stats, # 관리자용 교육 이수 현황 그래프 통계 조회
    create_ai_generated_education, # 관리자용 AI 교육 자료 생성
)
from app.db.db import get_db
from app.models import User
from app.schemas.education import (
    EducationCompletionFilter,
    EducationCompletionResponse,
    EducationResponse,
    EducationStatusResponse,
    EducationStatusSummaryResponse,
    UserEducationResponse,
    UserEducationSummaryResponse, # 유저용 교육 요약 건수 응답모델
    UserCompletionRatesResponse, # 유저용 교육 이수 현황 백분율 응답모델
    AdminRoleCompletionResponse, # 관리자용 교육 이수 현황 그래프 통계 응답모델
    AIEducationGenerateRequest, # 관리자용 AI 교육 자료 생성 요청모델
    AIEducationGenerateResponse, # 관리자용 AI 교육 자료 생성 응답모델
)

education_router = APIRouter()
admin_education_router = APIRouter()


# ==========================================
# 1. 일반 유저용 API (/api/education)
# ==========================================

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
    education = get_education_by_id(db, education_id)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="교육을 찾을 수 없습니다",
        )
    return complete_education(db, user=current_user, education=education)


# ==========================================
# 2. 관리자용 API (/api/admin/education)
# ==========================================

@admin_education_router.get(
    "/role-stats",
    response_model=AdminRoleCompletionResponse,
    summary="[관리자] 직군별 이수 현황 그래프 통계 조회",
)
def read_admin_role_completion_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """관리자 페이지 좌측 상단 '교육 이수 현황' (신규 근로자, 일반 작업자, 특수 작업자, 안전 관리자, 전체 %)"""
    return get_admin_role_completion_stats(db)


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
    role: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """관리자 페이지 우측 '대상자별 교육 리스트'"""
    if education_id is not None and get_education_by_id(db, education_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="교육을 찾을 수 없습니다",
        )

    return get_education_status_summaries(
        db,
        education_id=education_id,
        completion_status=(
            completion_filter.value if completion_filter else None
        ),
        role=role,
    )


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
    user = get_user_by_uid(db, uid)
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


@admin_education_router.post(
    "/ai-generate",
    response_model=AIEducationGenerateResponse,
    summary="[관리자] AI 교육 자료 생성",
)
def post_ai_generate_education(
    req: AIEducationGenerateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """관리자 페이지 우측 하단 'AI 교육 자료 생성' (작업 유형, 사용 장비, 위험 요인 입력 후 생성)"""
    return create_ai_generated_education(
        db,
        work_type=req.work_type,
        equipment=req.equipment,
        risk_factor=req.risk_factor
    )
