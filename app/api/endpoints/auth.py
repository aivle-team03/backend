from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.models import User
from app.crud.user import create_users as crud_create_user, checkid as crud_check_id
from app.crud.auth import create_access_token, get_current_user
from app.core.crypt import verify_password
from app.schemas.user import UserCreate, UserLogin
from app.schemas.token import Token

router = APIRouter()

@router.post("/signup")
def signup(user_create: UserCreate, db: Session = Depends(get_db)):
    # 이미 존재하는 아이디인지 중복 검사
    if crud_check_id(db, user_create.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다."
        )
    db_user = crud_create_user(db, user_create)
    return {"message": "success", "user_id": db_user.user_id}

@router.get("/checkid")
def checkid(user_id: str, db: Session = Depends(get_db)):
    exists = crud_check_id(db, user_id)
    if exists:
        return {"message": "success"}  # 아이디가 이미 존재하는 경우
    else:
        return {"message": "fail"}     # 아이디 사용 가능한 경우

@router.post("/login", response_model=Token)
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    # 유저 조회
    user = db.query(User).filter(User.user_id == user_login.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 잘못되었습니다."
        )
    
    # 비밀번호 검증
    if not verify_password(user_login.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 잘못되었습니다."
        )
    
    # JWT Access Token 생성 (sub에 PK인 uid의 문자열 저장)
    access_token = create_access_token(data={"sub": str(user.uid)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """로그아웃 API - JWT 토큰 무효화(요구사항 USR-02-02-3)"""
    return {"message": "success"}