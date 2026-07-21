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
)


education_router = APIRouter()
admin_education_router = APIRouter()


@education_router.get(
    "/list",
    response_model=List[EducationResponse],
    summary="내 교육 영상 조회",
)
def read_my_education_list(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_my_education_list(db, user=current_user, category=category)


@education_router.get(
    "/status",
    response_model=List[EducationStatusResponse],
    summary="내 교육 이수 현황 조회",
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
    return get_user_education_statuses(
        db,
        user=current_user,
        category=category,
        completion_status=(
            completion_filter.value if completion_filter else None
        ),
    )


@admin_education_router.get(
    "/status",
    response_model=List[EducationStatusSummaryResponse],
    summary="교육 이수 현황 조회",
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
    summary="대상자별 교육 리스트 조회",
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


@admin_education_router.patch(
    "/{uid}/{education_id}/completion",
    response_model=EducationCompletionResponse,
    summary="교육 이수 완료 처리",
)
def patch_education_completion(
    uid: int = Path(..., ge=1),
    education_id: int = Path(..., ge=1),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_user_by_uid(db, uid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    education = get_education_by_id(db, education_id)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="교육을 찾을 수 없습니다",
        )
    if education.role != user.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자 역할에 해당하지 않는 교육입니다",
        )

    return complete_education(db, user=user, education=education)
