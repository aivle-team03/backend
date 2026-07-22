from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.core.crypt import verify_password, hash_password
from app.schemas.user import UserResponse
from app.crud.auth import get_current_user
from app.models import User
from app.schemas.user import PasswordChange

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """내 정보 조회 (마이페이지) API - JWT 인증 필요"""
    return current_user

@router.patch("/me/password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    비밀번호 변경 API (부분 업데이트) - JWT 인증 필요
    """
    
    if not verify_password(password_data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다."
        )
    
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 기존 비밀번호와 다르게 설정해야 합니다."
        )

    current_user.password = hash_password(password_data.new_password)
    db.commit()

    return {"message": "비밀번호가 성공적으로 변경되었습니다."}