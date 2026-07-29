from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.models import User
from app.crud.auth import get_current_user
from app.crud import inspection as inspection_crud
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    InspectionDetailResponse,
    InspectionHistoryCreate,
    InspectionHistoryUpdate,
    InspectionHistoryResponse,
)

router = APIRouter()

# ==========================================
# 1. Inspection (점검 항목 Master) API
# ==========================================


@router.get("/", response_model=List[InspectionResponse])
def read_inspections(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """현재 로그인 유저 소속 회사의 점검 항목 목록 조회"""
    return inspection_crud.get_inspections_by_company(
        db=db, company_id=current_user.company_id, skip=skip, limit=limit
    )


@router.get("/{inspection_id}", response_model=InspectionDetailResponse)
def read_inspection_detail(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 점검 항목 상세 조회 (진행된 점검 이력 목록 포함)"""
    inspection = inspection_crud.get_inspection_by_id(
        db=db, inspection_id=inspection_id, company_id=current_user.company_id
    )
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 점검 항목을 찾을 수 없거나 접근 권한이 없습니다.",
        )
    return inspection


@router.post("/", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: InspectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """새로운 점검 항목 생성 (company_id는 토큰에서 자동 적용)"""
    return inspection_crud.create_inspection(
        db=db, inspection_in=payload, company_id=current_user.company_id
    )


@router.patch("/{inspection_id}", response_model=InspectionResponse)
def update_inspection(
    inspection_id: int,
    payload: InspectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """점검 항목 정보 수정"""
    updated_inspection = inspection_crud.update_inspection(
        db=db,
        inspection_id=inspection_id,
        company_id=current_user.company_id,
        inspection_in=payload,
    )
    if not updated_inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 점검 항목을 찾을 수 없거나 수정 권한이 없습니다.",
        )
    return updated_inspection


@router.delete("/{inspection_id}", status_code=status.HTTP_200_OK)
def delete_inspection(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """점검 항목 삭제"""
    success = inspection_crud.delete_inspection(
        db=db, inspection_id=inspection_id, company_id=current_user.company_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 점검 항목을 찾을 수 없거나 삭제 권한이 없습니다.",
        )
    return {"message": "점검 항목이 성공적으로 삭제되었습니다."}


# ==========================================
# 2. InspectionHistory (점검 이력) API
# ==========================================


@router.get("/{inspection_id}/histories", response_model=List[InspectionHistoryResponse])
def read_inspection_histories(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 점검 항목의 전체 이력 목록 조회"""
    return inspection_crud.get_histories_by_inspection(
        db=db, inspection_id=inspection_id, company_id=current_user.company_id
    )
    

@router.get("/histories/all", response_model=List[InspectionHistoryResponse])
def read_all_inspection_histories(
    status_filter: Optional[str] = None,
    is_action_required: Optional[bool] = None,
    date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    회사 전체 점검 이력 목록 조회
    - `status_filter`: "점검 대기", "점검 완료" 등
    - `is_action_required`: 조치 필요 여부 (true / false)
    - `date`: 특정 날짜 조회 (예: YYYY-MM-DD)
    """
    return inspection_crud.get_all_histories_by_company(
        db=db,
        company_id=current_user.company_id,
        status=status_filter,
        is_action_required=is_action_required,
        date=date,
        skip=skip,
        limit=limit,
    )
    
    
@router.get("/histories/me", response_model=List[InspectionHistoryResponse])
def read_my_inspection_histories(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    내게 배정된 점검 이력 목록 조회
    - `status_filter`: "점검 대기", "점검 완료" 등 (선택)
    """
    return inspection_crud.get_histories_by_user(
        db=db,
        company_id=current_user.company_id,
        uid=current_user.uid,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    

    
@router.get("/histories/{inspection_history_id}", response_model=InspectionHistoryResponse)
def read_inspection_history_detail(
    inspection_history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """점검 이력 단건 상세 조회"""
    history = inspection_crud.get_history_by_id(
        db=db,
        inspection_history_id=inspection_history_id,
        company_id=current_user.company_id,
    )
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 점검 이력을 찾을 수 없거나 접근 권한이 없습니다.",
        )
    return history


@router.post("/histories/create", response_model=InspectionHistoryResponse, status_code=status.HTTP_201_CREATED)
def create_inspection_history(
    payload: InspectionHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return inspection_crud.create_inspection_history(
            db=db, history_in=payload, company_id=current_user.company_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/histories/{history_id}", response_model=InspectionHistoryResponse)
def update_inspection_history(
    inspection_history_id: int,
    payload: InspectionHistoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """점검 수행 이력 상태/내용 수정 (점검 완료 처리 등)"""
    updated_history = inspection_crud.update_inspection_history(
        db=db,
        inspection_history_id=inspection_history_id,
        company_id=current_user.company_id,
        history_in=payload,
    )
    if not updated_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 점검 이력을 찾을 수 없거나 수정 권한이 없습니다.",
        )
    return updated_history

@router.delete("/histories/{inspection_history_id}", status_code=status.HTTP_200_OK)
def delete_inspection_history(
    inspection_history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """점검 이력 삭제"""
    success = inspection_crud.delete_inspection_history(
        db=db,
        inspection_history_id=inspection_history_id,
        company_id=current_user.company_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 점검 이력을 찾을 수 없거나 삭제 권한이 없습니다.",
        )
    return {"message": "점검 이력이 성공적으로 삭제되었습니다."}