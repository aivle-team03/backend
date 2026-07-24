from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Union

from app.db.db import get_db
from app.core.crypt import verify_password, hash_password
from app.schemas.user import (
    UserResponse,
    PasswordChange,
    PasswordChangeRequest,
    NotificationToggleRequest,
    PasswordFindResponse,
    UserRoleUpdateRequest
)
from app.crud.auth import get_current_user
from app.crud.user import (
    get_users,
    change_user_password,
    find_user_password,
    update_user_role
)
from app.models import User

router = APIRouter()
admin_user_router = APIRouter()


@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """내 정보 조회 (마이페이지) API - JWT 인증 필요"""
    return current_user

@router.patch("/me/password")
def change_password(
    password_data: Union[PasswordChangeRequest, PasswordChange],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """비밀번호 변경 API - JWT 인증 필요 (PUT / PATCH 모두 지원)"""
    old_pw = getattr(password_data, "old_password", None) or getattr(password_data, "current_password", None)
    new_pw = password_data.new_password

    if not old_pw:
        raise HTTPException(status_code=400, detail="현재 비밀번호를 입력해주세요.")

    if not verify_password(old_pw, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다."
        )

    if old_pw == new_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 기존 비밀번호와 다르게 설정해야 합니다."
        )

    current_user.password = hash_password(new_pw)
    db.commit()

    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


@router.patch("/me/notifications")
def patch_user_me_notifications(
    req: NotificationToggleRequest,
    current_user: User = Depends(get_current_user)
):
    """항목별 알림 수신 여부 설정 API - 명세서 URL /api/users/me/notifications"""
    return {
        "message": f"항목 '{req.item}'의 알림 수신 여부가 '{req.is_alert_enabled}'(으)로 변경되었습니다."
    }


@router.get("/find/password", response_model=PasswordFindResponse)
def get_find_user_password(
    user_id: str = Query(...),
    name: str = Query(...),
    db: Session = Depends(get_db)
):
    """비밀번호 찾기 API - 명세서 URL /api/users/find/password"""
    u = find_user_password(db, user_id=user_id, name=name)
    if not u:
        raise HTTPException(status_code=404, detail="일치하는 사용자 정보를 찾을 수 없습니다.")
    return {
        "user_id": u.user_id,
        "name": u.name,
        "message": "임시 비밀번호 재발급 안내 메일이 발송되었습니다. (가상 발송)"
    }


@router.get("", response_model=List[UserResponse])
def read_users(db: Session = Depends(get_db)):
    """전체 사용자 목록 조회 API - 명세서 URL /api/users"""
    return get_users(db)


# 관리자 전용 사용자 권한 관리 API
@admin_user_router.patch("/{uid}/role", response_model=UserResponse)
def patch_admin_user_role(
    uid: int = Path(...),
    req: UserRoleUpdateRequest = ...,
    db: Session = Depends(get_db)
):
    """사용자 권한(현장/통합) 관리 API - 명세서 URL /api/admin/users/{uid}/role"""
    u = update_user_role(db, uid=uid, role=req.role)
    if not u:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
    return u