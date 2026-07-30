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
from app.schemas.signup_code import (
    SignupCodeCreate,
    SignupCodeResponse,
    CategoryListResponse
)
from app.crud.auth import get_current_user, get_current_admin
from app.crud.user import (
    get_users,
    change_user_password,
    find_user_password,
    update_user_role,
    update_user_category_and_role
)
from app.crud.signup_code import (
    create_signup_code,
    get_all_signup_codes,
    get_available_categories
)
from app.models import User

router = APIRouter()
admin_router = APIRouter()

# 구버전 호환용 라우터 (기존 API 명세 유지용)
admin_user_router = APIRouter()

# 허용 역할 목록 (단일 소스)
VALID_ROLES = ["안전관리자", "관제사", "현장관리자", "일반유저"]


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

# =========================================================
# 안전관리자(총책임자) 전용 API 라우터 (/api/admin)
# =========================================================

@admin_router.get("/categories", response_model=CategoryListResponse)
def get_categories(admin_user: User = Depends(get_current_admin)):
    """
    일반유저 지정용 장비 카테고리 목록 조회
    GET /api/admin/categories
    """
    return {"categories": get_available_categories()}


@admin_router.post("/invite-codes", response_model=SignupCodeResponse)
def post_create_invite_code(
    req: SignupCodeCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin)
):
    """
    안전관리자 전용: 고유 회원가입 코드 생성
    POST /api/admin/invite-codes
    - role: 안전관리자 | 관제사 | 현장관리자 | 일반유저
    - category: 일반유저 선택 시 필수 (지게차, 화물트럭, 토잉카 등)
    """
    if req.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 역할입니다. 선택 가능한 역할: {', '.join(VALID_ROLES)}"
        )
    if req.role == "일반유저":
        if not req.category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="일반유저 선택 시 카테고리는 필수 입력사항입니다."
            )
        valid_categories = get_available_categories()
        if req.category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 카테고리입니다. 선택 가능한 카테고리: {', '.join(valid_categories)}"
            )
    return create_signup_code(db, company_id=admin_user.company_id, role=req.role, category=req.category)


@admin_router.get("/invite-codes", response_model=List[SignupCodeResponse])
def get_invite_codes(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin)
):
    """
    안전관리자 전용: 발급된 전체 회원가입 코드 목록 조회
    GET /api/admin/invite-codes
    """
    return get_all_signup_codes(db, company_id=admin_user.company_id)


@admin_router.get("/users", response_model=List[UserResponse])
def get_admin_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin)
):
    """
    안전관리자 전용: 전체 유저 목록(역할, 카테고리 포함) 조회
    GET /api/admin/users
    """
    return get_users(db, company_id=admin_user.company_id)


@admin_router.patch("/users/{uid}", response_model=UserResponse)
def patch_admin_user(
    uid: int = Path(..., description="수정할 유저의 UID"),
    req: UserRoleUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin)
):
    """
    안전관리자 전용: 유저 역할 및 카테고리 변경
    PATCH /api/admin/users/{uid}
    - role: 변경할 역할 (안전관리자 | 관제사 | 현장관리자 | 일반유저), 생략 가능
    - category: 변경할 카테고리 (일반유저인 경우), 생략 가능
    """
    # 역할 유효성 검증
    if req.role is not None and req.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 역할입니다. 선택 가능한 역할: {', '.join(VALID_ROLES)}"
        )
    # 카테고리 유효성 검증 (일반유저가 아닌 역할에 카테고리를 지정하려는 경우 경고)
    if req.category is not None:
        valid_categories = get_available_categories()
        if req.category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 카테고리입니다. 선택 가능한 카테고리: {', '.join(valid_categories)}"
            )

    u = update_user_category_and_role(db, uid=uid, company_id=admin_user.company_id, category=req.category, role=req.role)
    if not u:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
    return u


# 기존 API 명세 호환용 (admin_user_router - /api/admin/users/{uid}/role)
@admin_user_router.patch("/{uid}/role", response_model=UserResponse)
def patch_admin_user_role_legacy(
    uid: int = Path(...),
    req: UserRoleUpdateRequest = ...,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin)
):
    """기존 API 명세 호환용 역할 변경 API - PATCH /api/admin/users/{uid}/role"""
    if req.role is not None and req.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 역할입니다. 선택 가능한 역할: {', '.join(VALID_ROLES)}"
        )
    u = update_user_category_and_role(db, uid=uid, company_id=admin_user.company_id, category=req.category, role=req.role)
    if not u:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
    return u

