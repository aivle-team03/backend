from fastapi import APIRouter, Depends
from app.schemas.user import UserResponse
from app.crud.auth import get_current_user
from app.models import User

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """내 정보 조회 (마이페이지) API - JWT 인증 필요"""
    return current_user