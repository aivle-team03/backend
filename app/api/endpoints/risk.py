from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.db import get_db
from app.models.user import User
from app.crud.auth import get_current_user, get_current_admin
from app.schemas.event_category import (
    RiskFactorResponse,
    RiskManagementDashboardResponse,
    EventCategoryCreate,
    EventCategoryLevelUpdate
)
from app.crud import risk

router = APIRouter()

@router.get("/list", response_model=List[RiskFactorResponse])
def get_risk_list(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return risk.get_risk_category_list(db, company_id=current_user.company_id)


@router.patch("/category/{category_id}/level")
def update_category_level(
    category_id: int,
    payload: EventCategoryLevelUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # 1~10 스케일 예외 처리
    if not (1 <= payload.level <= 10):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="강도(level)는 1에서 10 사이의 숫자여야 합니다."
        )

    updated_cat = risk.update_event_category_level(db, category_id, payload.level, company_id=current_admin.company_id)
    if not updated_cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 카테고리를 찾을 수 없습니다."
        )

    return {
        "message": "강도가 정상적으로 변경되었습니다.",
        "category_id": category_id,
        "level": updated_cat.level
    }


@router.post("/category", status_code=status.HTTP_201_CREATED)
def create_category(payload: EventCategoryCreate, current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if not (1 <= payload.level <= 10):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="강도(level)는 1에서 10 사이의 값이어야 합니다."
        )

    new_cat = risk.create_event_category(db, payload, company_id=current_admin.company_id)
    return {
        "message": "새로운 위험 요인 항목이 추가되었습니다.",
        "category_id": new_cat.category_id
    }


@router.delete("/category/{category_id}")
def delete_category(category_id: int, current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    success = risk.delete_event_category(db, category_id, company_id=current_admin.company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 카테고리를 찾을 수 없습니다."
        )

    return {"message": "카테고리가 성공적으로 제거되었습니다."}